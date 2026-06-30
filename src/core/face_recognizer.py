"""
陌生人识别模块。

使用 DeepFace ArcFace 深度学习模型实现家庭成员与陌生人区分。
单张照片即可准确识别，512维特征向量余弦距离对比。

性能优化：
- 预加载 ArcFace 模型，避免重复初始化
- Haar Cascade 定位人脸 + detector_backend="skip" 跳过 DeepFace 重复检测
- 已裁剪人脸直接推理，大幅降低延迟
"""

import os
import logging
from typing import List, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_DISTANCE_THRESHOLD = 0.68


class FaceRecognizer:
    """基于 DeepFace ArcFace 的人脸识别器，优化实时性能。"""

    def __init__(
        self,
        faces_dir: str = "",
        tolerance: float = _DEFAULT_DISTANCE_THRESHOLD,
    ) -> None:
        self._tolerance = tolerance
        self._faces_dir = faces_dir
        self._face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self._member_encodings: List[np.ndarray] = []
        self._member_names: List[str] = []
        self._trained: bool = False

        if faces_dir and os.path.isdir(faces_dir):
            self._load_faces(faces_dir)
        else:
            logger.warning("Family faces directory not found: %s", faces_dir)

    def _load_faces(self, faces_dir: str) -> None:
        """从目录加载家庭成员照片，提取 ArcFace 特征向量。"""
        from deepface import DeepFace

        self._member_encodings = []
        self._member_names = []

        for fname in sorted(os.listdir(faces_dir)):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                continue
            name = os.path.splitext(fname)[0]
            img_path = os.path.join(faces_dir, fname)

            try:
                reps = DeepFace.represent(
                    img_path=img_path,
                    model_name="ArcFace",
                    enforce_detection=True,
                    align=True,
                )
                if reps:
                    best = max(reps, key=lambda r: r.get("facial_area", {}).get("w", 0) * r.get("facial_area", {}).get("h", 0))
                    self._member_encodings.append(np.array(best["embedding"]))
                    self._member_names.append(name)
                    logger.info("Loaded member: %s from %s", name, fname)
            except ValueError as e:
                logger.warning("No face in %s: %s", fname, e)
            except Exception as e:
                logger.warning("Error loading %s: %s", fname, e)

        self._trained = len(self._member_encodings) > 0
        if self._trained:
            logger.info(
                "Face recognizer ready: %d members loaded (ArcFace)",
                len(self._member_names),
            )
        else:
            logger.warning("No valid face samples found in %s", faces_dir)

    def identify_faces(
        self, frame: np.ndarray, person_boxes: list
    ) -> list:
        """对每个人员检测框区域进行人脸识别。"""
        from deepface import DeepFace

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        all_faces = self._face_cascade.detectMultiScale(
            gray, scaleFactor=1.08, minNeighbors=4, minSize=(24, 24)
        )

        results: list = []

        for pbox in person_boxes:
            px1, py1, px2, py2 = [int(v) for v in pbox["bbox"]]
            pbox_cx = (px1 + px2) / 2
            pbox_cy = (py1 + py2) / 2

            matched_face = None
            best_dist = float("inf")

            for fx, fy, fw, fh in all_faces:
                face_cx = fx + fw / 2
                face_cy = fy + fh / 2
                if px1 <= face_cx <= px2 and py1 <= face_cy <= py2:
                    dist = abs(face_cx - pbox_cx) + abs(face_cy - pbox_cy)
                    if dist < best_dist:
                        best_dist = dist
                        matched_face = (fx, fy, fw, fh)

            if matched_face is None:
                results.append({"bbox": pbox["bbox"], "identity": "no_face"})
                continue

            if not self._trained:
                results.append({"bbox": pbox["bbox"], "identity": "stranger"})
                continue

            # 裁剪人脸区域（带边距）
            fx, fy, fw, fh = matched_face
            margin_x = int(fw * 0.3)
            margin_y = int(fh * 0.3)
            h, w = frame.shape[:2]
            y1 = max(0, fy - margin_y)
            y2 = min(h, fy + fh + margin_y)
            x1 = max(0, fx - margin_x)
            x2 = min(w, fx + fw + margin_x)
            face_crop = frame[y1:y2, x1:x2]

            # 用 detector_backend="skip" 跳过重复人脸检测，直接推理
            identity = self._identify_crop(DeepFace, face_crop)
            results.append({"bbox": pbox["bbox"], "identity": identity})

        return results

    def _identify_crop(self, DeepFace, face_crop: np.ndarray) -> str:
        """用 DeepFace + skip detector 识别人脸裁剪区域。"""
        try:
            reps = DeepFace.represent(
                img_path=face_crop,
                model_name="ArcFace",
                detector_backend="skip",
                enforce_detection=False,
                align=True,
            )
        except Exception:
            return "stranger"

        if not reps:
            return "stranger"

        query_embedding = np.array(reps[0]["embedding"])

        best_idx = -1
        best_distance = float("inf")

        for idx, member_emb in enumerate(self._member_encodings):
            dist = self._cosine_distance(query_embedding, member_emb)
            if dist < best_distance:
                best_distance = dist
                best_idx = idx

        if best_distance < self._tolerance and best_idx >= 0:
            name = self._member_names[best_idx]
            return f"member:{name}"
        return "stranger"

    @staticmethod
    def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
        dot = np.dot(a, b)
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        if norm == 0:
            return 1.0
        return 1.0 - dot / norm

    def is_stranger(self, frame: np.ndarray) -> bool:
        faces = self.detect_faces(frame)
        if len(faces) == 0:
            return False
        if not self._trained:
            return True
        from deepface import DeepFace
        for x, y, w, h in faces:
            margin_x = int(w * 0.3)
            margin_y = int(h * 0.3)
            fh, fw = frame.shape[:2]
            y1 = max(0, y - margin_y)
            y2 = min(fh, y + h + margin_y)
            x1 = max(0, x - margin_x)
            x2 = min(fw, x + w + margin_x)
            face_crop = frame[y1:y2, x1:x2]
            identity = self._identify_crop(DeepFace, face_crop)
            if identity.startswith("member:"):
                return False
        return True

    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return self._face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
        )

    @property
    def trained(self) -> bool:
        return self._trained

    @property
    def member_count(self) -> int:
        return len(self._member_names)
