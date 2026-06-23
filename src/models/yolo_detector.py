from ultralytics import YOLO
import cv2
import os
import logging
from typing import Tuple, Optional, Dict, Any

import numpy as np

logger = logging.getLogger(__name__)


class YoloDetector:
    """YOLO 检测器，封装人员检测和火焰/烟雾检测模型。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """加载 YOLOv8 人员检测模型和火焰/烟雾检测模型。

        Args:
            config: 配置字典，支持 detection 节参数。
        """
        cfg = config or {}
        det_cfg = cfg.get("detection", {})
        model_dir = os.path.dirname(os.path.abspath(__file__))

        logger.info("Loading YOLOv8 person detection model...")
        self.person_model = YOLO("yolov8n.pt")
        logger.info("Person model classes: %s", self.person_model.names)

        logger.info("Loading fire/smoke detection model...")
        fire_model_path = det_cfg.get("fire_model_path", "") or os.path.join(model_dir, "fire_model.pt")
        self.fire_model = YOLO(fire_model_path)
        logger.info("Fire model classes: %s", self.fire_model.names)

        self._person_conf = det_cfg.get("person_conf", 0.8)
        self._person_classes = det_cfg.get("person_classes", [0])
        self._fire_conf = det_cfg.get("fire_conf", 0.8)
        self._fire_classes = det_cfg.get("fire_classes", [0, 1])

    def detect_person(self, frame: np.ndarray) -> Tuple[bool, np.ndarray]:
        """
        检测画面中的人员。

        Args:
            frame: OpenCV BGR 视频帧。

        Returns:
            (has_person, annotated_frame) 元组，has_person 为是否检测到人员，
            annotated_frame 为带标注框的画面。
        """
        results = self.person_model(frame, conf=self._person_conf, classes=self._person_classes, verbose=False)
        has_person = False
        annotated_frame = frame.copy()
        for result in results:
            if len(result.boxes) > 0:
                has_person = True
            annotated_frame = result.plot()
        return has_person, annotated_frame

    def detect_fire(self, frame: np.ndarray) -> Tuple[bool, np.ndarray]:
        """
        检测画面中的火焰和烟雾（仅关注 fire 和 fire-smoke 类别）。

        Args:
            frame: OpenCV BGR 视频帧。

        Returns:
            (has_fire, annotated_frame) 元组，has_fire 为是否检测到火焰/烟雾，
            annotated_frame 为带标注框的画面。
        """
        results = self.fire_model(frame, conf=self._fire_conf, classes=self._fire_classes, verbose=False)
        has_fire = False
        annotated_frame = frame.copy()
        for result in results:
            if len(result.boxes) > 0:
                has_fire = True
                annotated_frame = result.plot()
        return has_fire, annotated_frame
