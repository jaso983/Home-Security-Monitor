import sys
import os
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from core.alarm_manager import AlarmManager, _iou


def mgr_id_map(mgr: AlarmManager) -> dict:
    """把 AlarmManager 的 display identities 转成 {x1: identity} 映射，方便断言。"""
    return {i["bbox"][0]: i["identity"] for i in mgr.get_display_identities()}


class TestAlarmManager(unittest.TestCase):
    """AlarmManager 报警防抖模块单元测试。"""

    def setUp(self) -> None:
        self.alarm_mgr = AlarmManager(cooldown_seconds=1)

    # --- Fire/smoke alarm (consecutive-frame confirmation + cooldown) ---

    def test_fire_needs_consecutive_frames(self) -> None:
        """fire 连续 3 帧才触发，前 2 帧不触发。"""
        self.assertFalse(self.alarm_mgr.should_trigger_fire_alarm({0}))
        self.assertFalse(self.alarm_mgr.should_trigger_fire_alarm({0}))
        self.assertTrue(self.alarm_mgr.should_trigger_fire_alarm({0}))

    def test_fire_single_frame_no_alarm(self) -> None:
        """单帧 fire 不触发（核心痛点：抑制头发误检）。"""
        self.assertFalse(self.alarm_mgr.should_trigger_fire_alarm({0}))

    def test_fire_intermittent_no_alarm(self) -> None:
        """fire 间歇出现（检测/丢失/检测/丢失/检测）不触发。"""
        self.alarm_mgr.should_trigger_fire_alarm({0})
        self.alarm_mgr.should_trigger_fire_alarm(set())
        self.alarm_mgr.should_trigger_fire_alarm({0})
        self.alarm_mgr.should_trigger_fire_alarm(set())
        self.assertFalse(self.alarm_mgr.should_trigger_fire_alarm({0}))

    def test_smoke_needs_more_frames(self) -> None:
        """smoke 需 5 帧，4 帧不触发（比 fire 更严格）。"""
        mgr = AlarmManager(cooldown_seconds=10, fire_stable_frames=3, smoke_stable_frames=5)
        for _ in range(4):
            self.assertFalse(mgr.should_trigger_fire_alarm({1}))
        self.assertTrue(mgr.should_trigger_fire_alarm({1}))

    def test_fire_cooldown_after_confirm(self) -> None:
        """确认触发后冷却内不触发，冷却过期后下一帧即触发（计数器未重置）。"""
        mgr = AlarmManager(cooldown_seconds=1)
        mgr.should_trigger_fire_alarm({0})
        mgr.should_trigger_fire_alarm({0})
        self.assertTrue(mgr.should_trigger_fire_alarm({0}))
        # 冷却内：计数器继续累计，triggered 非 None 但冷却抑制
        self.assertFalse(mgr.should_trigger_fire_alarm({0}))
        self.assertFalse(mgr.should_trigger_fire_alarm({0}))
        time.sleep(1.1)
        # 冷却过期后，计数器已 >=3，下一帧立即触发
        self.assertTrue(mgr.should_trigger_fire_alarm({0}))

    def test_fire_smoke_independent(self) -> None:
        """fire 和 smoke 计数互不干扰。"""
        mgr = AlarmManager(cooldown_seconds=10, fire_stable_frames=3, smoke_stable_frames=3)
        mgr.should_trigger_fire_alarm({0})  # fire=1, smoke=0
        mgr.should_trigger_fire_alarm({0})  # fire=2, smoke=0
        self.assertEqual(mgr._fire_tracker._smoke_consecutive, 0)
        self.assertTrue(mgr.should_trigger_fire_alarm({0}))  # fire=3 触发

    def test_fire_class_disappear_reset(self) -> None:
        """fire 消失一帧后计数归零，需重新连续 3 帧才触发。"""
        mgr = AlarmManager(cooldown_seconds=10, fire_stable_frames=3)
        mgr.should_trigger_fire_alarm({0})  # fire=1
        mgr.should_trigger_fire_alarm({0})  # fire=2
        mgr.should_trigger_fire_alarm(set())  # fire=0 (归零)
        self.assertFalse(mgr.should_trigger_fire_alarm({0}))  # fire=1
        self.assertFalse(mgr.should_trigger_fire_alarm({0}))  # fire=2
        self.assertTrue(mgr.should_trigger_fire_alarm({0}))  # fire=3 触发

    def test_fire_backward_compat_should_trigger_alarm(self) -> None:
        """should_trigger_alarm('fire') 向后兼容：内部传 {0}，连续 3 次触发。"""
        mgr = AlarmManager(cooldown_seconds=10)
        self.assertFalse(mgr.should_trigger_alarm("fire"))
        self.assertFalse(mgr.should_trigger_alarm("fire"))
        self.assertTrue(mgr.should_trigger_alarm("fire"))

    # --- Person tracking ---

    def test_stranger_needs_consecutive_frames(self) -> None:
        """stranger 连续3帧确认后才触发报警。"""
        det = [{"bbox": [10, 10, 100, 200], "identity": "stranger"}]
        r1 = self.alarm_mgr.update(det, det, is_night=True)
        self.assertEqual(len(r1), 0)
        r2 = self.alarm_mgr.update(det, det, is_night=True)
        self.assertEqual(len(r2), 0)
        r3 = self.alarm_mgr.update(det, det, is_night=True)
        self.assertEqual(len(r3), 1)
        self.assertEqual(r3[0]["reason"], "stranger")

    def test_stranger_single_frame_no_alarm(self) -> None:
        """单帧 stranger 不应报警（避免误判）。"""
        det = [{"bbox": [10, 10, 100, 200], "identity": "stranger"}]
        results = self.alarm_mgr.update(det, det, is_night=True)
        self.assertEqual(len(results), 0)

    def test_stranger_intermittent_no_alarm(self) -> None:
        """stranger 与 no_face 交替出现时不应确认 stranger。"""
        stranger_det = [{"bbox": [10, 10, 100, 200], "identity": "stranger"}]
        noface_det = [{"bbox": [10, 10, 100, 200], "identity": "no_face"}]
        self.alarm_mgr.update(stranger_det, stranger_det, is_night=True)
        self.alarm_mgr.update(noface_det, noface_det, is_night=True)
        results = self.alarm_mgr.update(stranger_det, stranger_det, is_night=True)
        self.assertEqual(len(results), 0)

    def test_member_no_alarm(self) -> None:
        """member 单帧即可确认，不触发报警。"""
        det = [{"bbox": [10, 10, 100, 200], "identity": "member:alice"}]
        results = self.alarm_mgr.update(det, det, is_night=True)
        self.assertEqual(len(results), 0)

    def test_no_face_night_alarm_after_delay(self) -> None:
        """夜间 no_face 连续3帧确认 + 延迟后报警。"""
        mgr = AlarmManager(no_face_night_delay_seconds=0.2)
        det = [{"bbox": [10, 10, 100, 200], "identity": "no_face"}]
        mgr.update(det, det, is_night=True)
        mgr.update(det, det, is_night=True)
        mgr.update(det, det, is_night=True)
        time.sleep(0.3)
        results = mgr.update(det, det, is_night=True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["reason"], "no_face_night")

    def test_no_face_night_no_alarm_before_delay(self) -> None:
        """夜间 no_face 确认后但未达延迟时间不应报警。"""
        mgr = AlarmManager(no_face_night_delay_seconds=10)
        det = [{"bbox": [10, 10, 100, 200], "identity": "no_face"}]
        mgr.update(det, det, is_night=True)
        mgr.update(det, det, is_night=True)
        mgr.update(det, det, is_night=True)
        results = mgr.update(det, det, is_night=True)
        self.assertEqual(len(results), 0)

    def test_no_face_day_no_immediate_alarm(self) -> None:
        """白天 no_face 不应立即报警。"""
        det = [{"bbox": [10, 10, 100, 200], "identity": "no_face"}]
        self.alarm_mgr.update(det, det, is_night=False)
        self.alarm_mgr.update(det, det, is_night=False)
        results = self.alarm_mgr.update(det, det, is_night=False)
        self.assertEqual(len(results), 0)

    def test_no_face_day_delayed_alarm(self) -> None:
        """白天 no_face 稳定确认后，超过延迟时间应报警。"""
        mgr = AlarmManager(no_face_delay_seconds=0.2)
        det = [{"bbox": [10, 10, 100, 200], "identity": "no_face"}]
        mgr.update(det, det, is_night=False)
        mgr.update(det, det, is_night=False)
        mgr.update(det, det, is_night=False)
        time.sleep(0.3)
        results = mgr.update(det, det, is_night=False)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["reason"], "no_face_delayed")

    def test_no_face_debounced_flashes(self) -> None:
        """no_face 和 member 交替闪烁时，身份应保持 member（防抖）。"""
        mgr = AlarmManager()
        member_det = [{"bbox": [10, 10, 100, 200], "identity": "member:alice"}]
        noface_det = [{"bbox": [10, 10, 100, 200], "identity": "no_face"}]
        mgr.update(member_det, member_det, is_night=True)
        mgr.update(noface_det, noface_det, is_night=True)
        mgr.update(noface_det, noface_det, is_night=True)
        mgr.update(noface_det, noface_det, is_night=True)
        identities = mgr.get_display_identities()
        self.assertEqual(identities[0]["identity"], "member:alice")

    def test_same_track_no_repeat_alarm(self) -> None:
        """同一 track 已触发报警后不重复报警。"""
        det = [{"bbox": [10, 10, 100, 200], "identity": "stranger"}]
        self.alarm_mgr.update(det, det, is_night=True)
        self.alarm_mgr.update(det, det, is_night=True)
        self.alarm_mgr.update(det, det, is_night=True)
        results = self.alarm_mgr.update(
            [{"bbox": [12, 12, 102, 202], "identity": "stranger"}],
            [{"bbox": [12, 12, 102, 202], "identity": "stranger"}],
            is_night=True,
        )
        self.assertEqual(len(results), 0)

    def test_track_expires_after_leaving(self) -> None:
        """track 离开画面老化后，重新出现需再次连续3帧确认才报警。"""
        mgr = AlarmManager(track_max_age=2, person_alarm_gap=0.1)
        det = [{"bbox": [10, 10, 100, 200], "identity": "stranger"}]
        mgr.update(det, det, is_night=True)
        mgr.update(det, det, is_night=True)
        mgr.update(det, det, is_night=True)
        mgr.update([], [], is_night=True)
        mgr.update([], [], is_night=True)
        mgr.update([], [], is_night=True)
        mgr.update([], [], is_night=True)
        time.sleep(0.15)
        r1 = mgr.update(det, det, is_night=True)
        self.assertEqual(len(r1), 0)
        r2 = mgr.update(det, det, is_night=True)
        self.assertEqual(len(r2), 0)
        r3 = mgr.update(det, det, is_night=True)
        self.assertEqual(len(r3), 1)

    def test_all_person_boxes_tracked(self) -> None:
        """所有人员框都应参与 track 匹配，未识别的保持 pending 身份。"""
        person_boxes = [
            {"bbox": [10, 10, 100, 200]},
            {"bbox": [300, 10, 400, 200]},
        ]
        identity_results = [
            {"bbox": [10, 10, 100, 200], "identity": "member:alice"},
        ]
        self.alarm_mgr.update(person_boxes, identity_results, is_night=True)
        self.assertEqual(self.alarm_mgr.active_tracks, 2)
        id_map = mgr_id_map(self.alarm_mgr)
        self.assertEqual(id_map[10], "member:alice")
        self.assertEqual(id_map[300], "pending")

    def test_stranger_upgrades_to_member(self) -> None:
        """stranger 确认后，连续 member 帧应升级为 member。"""
        stranger_det = [{"bbox": [10, 10, 100, 200], "identity": "stranger"}]
        member_det = [{"bbox": [10, 10, 100, 200], "identity": "member:alice"}]
        self.alarm_mgr.update(stranger_det, stranger_det, is_night=True)
        self.alarm_mgr.update(stranger_det, stranger_det, is_night=True)
        self.alarm_mgr.update(stranger_det, stranger_det, is_night=True)
        results = self.alarm_mgr.update(member_det, member_det, is_night=True)
        self.assertEqual(len(results), 0)
        id_map = mgr_id_map(self.alarm_mgr)
        self.assertEqual(id_map[10], "member:alice")

    # --- IoU ---

    def test_iou_overlap(self) -> None:
        val = _iou([0, 0, 100, 100], [50, 50, 150, 150])
        self.assertGreater(val, 0)
        self.assertLess(val, 1)

    def test_iou_no_overlap(self) -> None:
        val = _iou([0, 0, 50, 50], [100, 100, 150, 150])
        self.assertEqual(val, 0.0)

    def test_iou_identical(self) -> None:
        val = _iou([0, 0, 100, 100], [0, 0, 100, 100])
        self.assertAlmostEqual(val, 1.0)


if __name__ == "__main__":
    unittest.main()
