from ultralytics import YOLO
import cv2
import os
import logging
from typing import Tuple, Optional, Dict, Any, List

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

        self._person_conf = det_cfg.get("person_conf", 0.5)
        self._person_classes = det_cfg.get("person_classes", [0])
        self._fire_conf = det_cfg.get("fire_conf", 0.7)
        self._fire_classes = det_cfg.get("fire_classes", [0, 1])

    def detect_person(self, frame: np.ndarray) -> Tuple[list, np.ndarray]:
        """
        检测画面中的人员，返回检测详情。

        Args:
            frame: OpenCV BGR 视频帧。

        Returns:
            (person_boxes, annotated_frame) 元组：
            person_boxes 为检测到的人员列表，每项为
            {"bbox": [x1, y1, x2, y2], "confidence": float}；
            annotated_frame 为带标注框的画面。
        """
        results = self.person_model(frame, conf=self._person_conf, classes=self._person_classes, verbose=False, half=True)
        person_boxes: list = []
        annotated_frame = frame.copy()
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                person_boxes.append({"bbox": [x1, y1, x2, y2], "confidence": conf})
            if len(result.boxes) > 0:
                annotated_frame = result.plot()
        return person_boxes, annotated_frame

    def detect_fire(self, frame: np.ndarray) -> Tuple[List[Dict], np.ndarray]:
        """
        检测画面中的火焰和烟雾（仅关注 fire 和 fire-smoke 类别）。

        Args:
            frame: OpenCV BGR 视频帧。

        Returns:
            (fire_detections, annotated_frame) 元组：
            fire_detections 为检测到的火焰/烟雾列表，每项含
            {"class_id", "class_name", "confidence", "bbox"}；
            annotated_frame 为带标注框的画面。
        """
        results = self.fire_model(frame, conf=self._fire_conf, classes=self._fire_classes, verbose=False, half=True)
        fire_detections: List[Dict] = []
        annotated_frame = frame.copy()
        for result in results:
            for box in result.boxes:
                fire_detections.append({
                    "class_id": int(box.cls[0]),
                    "class_name": self.fire_model.names[int(box.cls[0])],
                    "confidence": float(box.conf[0]),
                    "bbox": box.xyxy[0].tolist(),
                })
            if len(result.boxes) > 0:
                annotated_frame = result.plot()
        return fire_detections, annotated_frame
