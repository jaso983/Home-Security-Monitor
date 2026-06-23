"""
陌生人识别模块。

使用 OpenCV 人脸检测 + LBPH 人脸识别器实现家庭成员与陌生人的区分。
注册家庭成员照片后，系统可判断画面中的人是否为家庭成员。

依赖：opencv-python（项目已有依赖，无需额外安装）
"""

import os
import logging
from typing import List, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 80.0


class FaceRecognizer:
    """基于 OpenCV LBPH 的人脸识别器，区分家庭成员与陌生人。"""

    def __init__(
        self,
        faces_dir: str = "",
        tolerance: float = _DEFAULT_THRESHOLD,
    ) -> None:
        """初始化人脸识别器。"""
        self._tolerance = tolerance
        self._faces_dir = faces_dir
        self._face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self._recognizer = cv2.face.LBPHFaceRecognizer_create(
            threshold=tolerance
        )
        self._labels: List[str] = []
        self._trained: bool = False

        if faces_dir and os.path.isdir(faces_dir):
            self._load_faces(faces_dir)
        else:
            logger.warning("Family faces directory not found: %s", faces_dir)

    def _load_faces(self, faces_dir: str) -> None:
        """从目录加载家庭成员照片并训练识别器。"""
        name_to_samples: dict = {}

        for fname in os.listdir(faces_dir):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                continue
            name = os.path.splitext(fname)[0]
            img_path = os.path.join(faces_dir, fname)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                logger.warning("Cannot read image: %s", img_path)
                continue

            faces = self._face_cascade.detectMultiScale(
                img, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
            )
            if len(faces) == 0:
                logger.warning("No face detected in: %s", img_path)
                continue

            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            face_roi = cv2.resize(img[y:y+h, x:x+w], (100, 100))
            name_to_samples.setdefault(name, []).append(face_roi)

        if not name_to_samples:
            logger.warning("No valid face samples found in %s", faces_dir)
            return

        samples: List[np.ndarray] = []
        labels: List[int] = []
        self._labels = []
        for idx, (name, faces) in enumerate(name_to_samples.items()):
            self._labels.append(name)
            for face in faces:
                samples.append(face)
                labels.append(idx)

        self._recognizer.train(samples, np.array(labels))
        self._trained = True
        logger.info(
            "Face recognizer trained: %d members, %d samples",
            len(self._labels), len(samples),
        )

    def is_stranger(self, frame: np.ndarray) -> bool:
        """判断画面中的人是否为陌生人。

        Returns:
            True = 陌生人（应触发报警），False = 家庭成员或无人脸。
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
        )

        if len(faces) == 0:
            return False

        if not self._trained:
            return True

        for x, y, w, h in faces:
            face_roi = cv2.resize(gray[y:y+h, x:x+w], (100, 100))
            label, confidence = self._recognizer.predict(face_roi)
            if confidence < self._tolerance:
                logger.debug(
                    "Family member: %s (conf=%.1f)",
                    self._labels[label] if label < len(self._labels) else "?",
                    confidence,
                )
                return False

        return True

    def detect_faces(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """检测画面中的人脸位置。"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return self._face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
        )

    @property
    def trained(self) -> bool:
        """是否已训练。"""
        return self._trained

    @property
    def member_count(self) -> int:
        """已注册的家庭成员数量。"""
        return len(self._labels)
