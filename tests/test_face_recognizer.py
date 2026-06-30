import sys
import os
import unittest
from unittest.mock import patch
import tempfile
import shutil

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from core.face_recognizer import FaceRecognizer


class TestFaceRecognizer(unittest.TestCase):
    """FaceRecognizer 陌生人识别模块单元测试。"""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_no_faces_dir_returns_untrained(self) -> None:
        recognizer = FaceRecognizer(faces_dir="", tolerance=80.0)
        self.assertFalse(recognizer.trained)
        self.assertEqual(recognizer.member_count, 0)

    def test_empty_faces_dir_returns_untrained(self) -> None:
        recognizer = FaceRecognizer(faces_dir=self.tmp_dir, tolerance=80.0)
        self.assertFalse(recognizer.trained)
        self.assertEqual(recognizer.member_count, 0)

    def test_untrained_is_stranger(self) -> None:
        """未训练时，检测到人脸应视为陌生人。"""
        # 构造一个已初始化但未训练的识别器，mock人脸检测返回有人脸
        recognizer = FaceRecognizer(faces_dir="", tolerance=80.0)
        self.assertFalse(recognizer.trained)
        # 未训练时is_stranger在检测到人脸后走 self._trained=False 分支，返回True
        # 需要让detectMultiScale返回人脸坐标
        import cv2
        orig_fn = cv2.CascadeClassifier.detectMultiScale
        def mock_detect(self2, *args, **kwargs):
            return np.array([[10, 10, 80, 80]])
        cv2.CascadeClassifier.detectMultiScale = mock_detect
        try:
            result = recognizer.is_stranger(np.zeros((100, 100, 3), dtype=np.uint8))
            self.assertTrue(result)
        finally:
            cv2.CascadeClassifier.detectMultiScale = orig_fn

    def test_no_face_returns_false(self) -> None:
        """无人脸时，is_stranger应返回False（避免无人也报警）。"""
        recognizer = FaceRecognizer(faces_dir="", tolerance=80.0)
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        # detectMultiScale默认返回空
        self.assertFalse(recognizer.is_stranger(frame))

    def test_invalid_image_file_skipped(self) -> None:
        """无效图片文件应被跳过，不崩溃。"""
        bad_img = os.path.join(self.tmp_dir, "bad.jpg")
        with open(bad_img, "w") as f:
            f.write("not an image")
        recognizer = FaceRecognizer(faces_dir=self.tmp_dir, tolerance=80.0)
        self.assertFalse(recognizer.trained)

    def test_member_count_property(self) -> None:
        """member_count应反映加载的家庭成员数量。"""
        recognizer = FaceRecognizer(faces_dir="", tolerance=80.0)
        self.assertEqual(recognizer.member_count, 0)

    def test_tolerance_stored(self) -> None:
        """容差阈值应正确存储。"""
        recognizer = FaceRecognizer(faces_dir="", tolerance=60.0)
        self.assertEqual(recognizer._tolerance, 60.0)


if __name__ == "__main__":
    unittest.main()
