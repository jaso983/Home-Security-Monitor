"""报警管理器：人员追踪 + 时段感知 + 智能去重。

核心逻辑：
- 基于 IoU 的人员追踪：同一人在画面中只触发一次报警
- 所有检测到的人员框都参与 track 匹配，身份识别结果独立更新
- 身份防抖：member 一旦确认永不降级，stranger 连续 N 帧才确认
- no_face 夜间短暂延迟报警（给人转身面对摄像头的时间）
- fire 类型保留原有冷却机制
"""

import time
from typing import Dict, List


def _iou(box_a: List[float], box_b: List[float]) -> float:
    """计算两个 [x1,y1,x2,y2] 框的 IoU。"""
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])

    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter == 0:
        return 0.0

    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    return inter / (area_a + area_b - inter)


class PersonTrack:
    """单个人员追踪记录。"""

    STABLE_FRAMES = 3
    IDENTITY_REFRESH_SECONDS = 5.0

    def __init__(self, track_id: int, bbox: List[float], identity: str, stable_frames: int = 3) -> None:
        self.track_id = track_id
        self._stable_frames = stable_frames
        self.bbox = bbox
        self.stable_identity: str = "pending"
        self._consecutive: int = 0
        self._last_raw_identity: str = ""
        self.first_seen: float = time.time()
        self.last_seen: float = self.first_seen
        self.last_identity_refresh: float = 0.0
        self.alarm_triggered: bool = False
        self.alarm_reason: str = ""
        self.miss_count: int = 0
        if identity and identity != "pending":
            self.update_identity(identity)

    def update_identity(self, new_identity: str) -> None:
        """更新身份，带防抖逻辑。

        规则：
        - member 一旦确认永不降级（最高置信度）
        - stranger 可升级为 member（识别纠正），但不降级为 no_face
        - member 单帧即可确认（DeepFace 高置信度）
        - stranger / no_face 需连续 STABLE_FRAMES 帧才确认
        """
        # member 永不降级
        if self.stable_identity.startswith("member:"):
            if new_identity.startswith("member:"):
                self.last_identity_refresh = time.time()
            return

        # member 立即确认（含 stranger 升级为 member）
        if new_identity.startswith("member:"):
            self.stable_identity = new_identity
            self._consecutive = self._stable_frames
            self._last_raw_identity = new_identity
            self.last_identity_refresh = time.time()
            return

        # 记录连续相同身份帧数
        if new_identity == self._last_raw_identity:
            self._consecutive += 1
        else:
            self._consecutive = 1
            self._last_raw_identity = new_identity

        # stranger 连续 N 帧确认
        if new_identity == "stranger":
            if self._consecutive >= self._stable_frames:
                self.stable_identity = "stranger"
                self.last_identity_refresh = time.time()
        # no_face 连续 N 帧确认，只在 pending 时生效（不覆盖 stranger）
        elif new_identity == "no_face":
            if self._consecutive >= self._stable_frames and self.stable_identity == "pending":
                self.stable_identity = "no_face"
                self.last_identity_refresh = time.time()

    @property
    def identity(self) -> str:
        """返回当前用于显示和报警判断的身份。"""
        return self.stable_identity

    @property
    def needs_face_check(self) -> bool:
        """是否需要重新执行人脸识别。

        - member 不需要（已确认，永不降级）
        - stranger/待确认身份 每5秒刷新一次（可能升级为 member）
        """
        if self.stable_identity.startswith("member:"):
            return False
        return time.time() - self.last_identity_refresh >= self.IDENTITY_REFRESH_SECONDS


class FireSmokeTracker:
    """fire/smoke 连续帧确认追踪器，两类独立计数。"""

    def __init__(self, fire_stable_frames: int = 3, smoke_stable_frames: int = 5) -> None:
        self.fire_stable_frames = fire_stable_frames
        self.smoke_stable_frames = smoke_stable_frames
        self._fire_consecutive: int = 0
        self._smoke_consecutive: int = 0

    def update(self, detected_classes: set) -> "str | None":
        """更新计数。detected_classes 为本帧检测到的 class_id 集合。

        返回确认触发的类别名 ("fire"/"smoke") 或 None。
        规则：某类本帧未出现 → 计数归零；达到阈值 → 返回类别名。
        """
        triggered = None
        if 0 in detected_classes:
            self._fire_consecutive += 1
            if self._fire_consecutive >= self.fire_stable_frames:
                triggered = "fire" if triggered is None else triggered
        else:
            self._fire_consecutive = 0
        if 1 in detected_classes:
            self._smoke_consecutive += 1
            if self._smoke_consecutive >= self.smoke_stable_frames:
                triggered = "smoke" if triggered is None else triggered
        else:
            self._smoke_consecutive = 0
        return triggered

    def reset(self) -> None:
        self._fire_consecutive = 0
        self._smoke_consecutive = 0


class AlarmManager:
    """报警防抖管理器，支持人员追踪和时段感知。"""

    def __init__(
        self,
        cooldown_seconds: float = 10,
        iou_threshold: float = 0.2,
        track_max_age: int = 90,
        no_face_delay_seconds: float = 10,
        no_face_night_delay_seconds: float = 3,
        person_alarm_gap: float = 5.0,
        fire_stable_frames: int = 3,
        smoke_stable_frames: int = 5,
        person_stable_frames: int = 3,
    ) -> None:
        self.cooldown: float = cooldown_seconds
        self.iou_threshold: float = iou_threshold
        self.track_max_age: int = track_max_age
        self.no_face_delay_seconds: float = no_face_delay_seconds
        self.no_face_night_delay_seconds: float = no_face_night_delay_seconds
        self.person_alarm_gap: float = person_alarm_gap
        self._person_stable_frames: int = person_stable_frames
        self._fire_tracker = FireSmokeTracker(fire_stable_frames, smoke_stable_frames)

        self.last_fire_alarm_time: float = 0.0
        self.last_person_alarm_time: float = 0.0
        self._tracks: Dict[int, PersonTrack] = {}
        self._next_id: int = 0

    def should_trigger_fire_alarm(self, detected_classes: set) -> bool:
        """判断是否应触发火焰报警（连续帧确认 + 冷却机制）。"""
        triggered = self._fire_tracker.update(detected_classes)
        if triggered is None:
            return False
        now = time.time()
        if now - self.last_fire_alarm_time > self.cooldown:
            self.last_fire_alarm_time = now
            self._fire_tracker.reset()
            return True
        return False

    def update(
        self,
        person_boxes: List[Dict],
        identity_results: List[Dict],
        is_night: bool,
    ) -> List[Dict]:
        """更新人员追踪状态，返回需要报警的人员列表。

        Args:
            person_boxes: YOLO 检测到的所有人员框
                {"bbox": [x1,y1,x2,y2], "confidence": float}
            identity_results: DeepFace 识别结果（仅包含需要识别的人员）
                {"bbox": [x1,y1,x2,y2], "identity": "member:xxx"|"stranger"|"no_face"}
            is_night: 是否处于夜间安防时段

        Returns:
            需要报警的人员列表 [{"track_id", "identity", "bbox", "reason"}]
        """
        # 将 identity_result 通过 IoU 匹配到 person_box 索引
        identity_map: Dict[int, str] = {}
        used_pi: set = set()
        for ir in identity_results:
            best_pi = -1
            best_iou = self.iou_threshold
            for pi, pbox in enumerate(person_boxes):
                if pi in used_pi:
                    continue
                iou_val = _iou(ir["bbox"], pbox["bbox"])
                if iou_val >= best_iou:
                    best_iou = iou_val
                    best_pi = pi
            if best_pi >= 0:
                identity_map[best_pi] = ir["identity"]
                used_pi.add(best_pi)

        # 1. 计算所有 (person_box, track) 的 IoU 对，按 IoU 降序贪心匹配
        pairs: List[tuple] = []
        for pi, pbox in enumerate(person_boxes):
            for tid, track in self._tracks.items():
                iou_val = _iou(pbox["bbox"], track.bbox)
                if iou_val >= self.iou_threshold:
                    pairs.append((iou_val, pi, tid))

        pairs.sort(key=lambda p: p[0], reverse=True)

        matched_pis: set = set()
        matched_tids: set = set()

        for _, pi, tid in pairs:
            if pi in matched_pis or tid in matched_tids:
                continue
            track = self._tracks[tid]
            pbox = person_boxes[pi]
            track.bbox = pbox["bbox"]
            if pi in identity_map:
                track.update_identity(identity_map[pi])
            track.last_seen = time.time()
            track.miss_count = 0
            matched_pis.add(pi)
            matched_tids.add(tid)

        # 2. 未匹配的 person_box 创建新 track
        new_tids: set = set()
        for pi, pbox in enumerate(person_boxes):
            if pi not in matched_pis:
                tid = self._next_id
                self._next_id += 1
                initial_identity = identity_map.get(pi, "pending")
                self._tracks[tid] = PersonTrack(tid, pbox["bbox"], initial_identity, stable_frames=self._person_stable_frames)
                new_tids.add(tid)

        # 3. 未匹配的 track 老化
        for tid, track in self._tracks.items():
            if tid not in matched_tids and tid not in new_tids:
                track.miss_count += 1

        expired = [tid for tid, t in self._tracks.items()
                   if t.miss_count > self.track_max_age]
        for tid in expired:
            del self._tracks[tid]

        # 4. 判断哪些 track 需要报警
        alarms: List[Dict] = []
        now = time.time()

        for track in self._tracks.values():
            if track.alarm_triggered:
                continue
            identity = track.identity
            if identity.startswith("member:"):
                continue
            if identity == "pending":
                continue

            # 全局人员报警间隔
            if now - self.last_person_alarm_time < self.person_alarm_gap:
                continue

            if identity == "stranger":
                alarms.append({
                    "track_id": track.track_id,
                    "identity": identity,
                    "bbox": track.bbox,
                    "reason": "stranger",
                })
                track.alarm_triggered = True
                track.alarm_reason = "stranger"
                self.last_person_alarm_time = now

            elif identity == "no_face":
                delay = self.no_face_night_delay_seconds if is_night else self.no_face_delay_seconds
                elapsed = now - track.first_seen
                if elapsed >= delay:
                    reason = "no_face_night" if is_night else "no_face_delayed"
                    alarms.append({
                        "track_id": track.track_id,
                        "identity": identity,
                        "bbox": track.bbox,
                        "reason": reason,
                    })
                    track.alarm_triggered = True
                    track.alarm_reason = reason
                    self.last_person_alarm_time = now

        return alarms

    def find_track_by_bbox(self, bbox: List[float]) -> "PersonTrack | None":
        """根据 IoU 查找匹配的现有 track。"""
        best_tid = -1
        best_iou = self.iou_threshold
        for tid, track in self._tracks.items():
            iou_val = _iou(bbox, track.bbox)
            if iou_val >= best_iou:
                best_iou = iou_val
                best_tid = tid
        if best_tid >= 0:
            return self._tracks[best_tid]
        return None

    def get_boxes_needing_face_check(self, person_boxes: list) -> list:
        """返回需要执行 DeepFace 识别的人员框列表。

        已确认 member 且无需刷新的 track 跳过，其余需要识别。
        """
        boxes_to_check = []
        for pbox in person_boxes:
            matched = self.find_track_by_bbox(pbox["bbox"])
            if matched and not matched.needs_face_check:
                continue
            boxes_to_check.append(pbox)
        return boxes_to_check

    def reset_tracks(self) -> None:
        """清除所有人员追踪状态，允许重新报警。"""
        self._tracks.clear()
        self.last_person_alarm_time = 0.0

    def get_display_identities(self) -> List[Dict]:
        """返回各 track 的稳定身份和 bbox，用于画面标注和 UI 状态。"""
        return [
            {"track_id": t.track_id, "identity": t.identity, "bbox": t.bbox}
            for t in self._tracks.values()
        ]

    @property
    def active_tracks(self) -> int:
        return len(self._tracks)

    def get_track_summary(self) -> str:
        if not self._tracks:
            return "No tracked persons"
        parts = []
        for track in self._tracks.values():
            short = track.identity.split(":")[1] if track.identity.startswith("member:") else track.identity
            parts.append(f"#{track.track_id}:{short}")
        return "Tracks: " + ", ".join(parts)

    def should_trigger_alarm(self, event_type: str) -> bool:
        if event_type == "fire":
            return self.should_trigger_fire_alarm({0})
        return False
