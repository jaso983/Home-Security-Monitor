from ultralytics import YOLO
import cv2
import os

class YoloDetector:
    def __init__(self):
        model_dir = os.path.dirname(os.path.abspath(__file__))

        print("正在加载 YOLOv8 人员检测模型...")
        #第一次运行会自动下载，约6MB
        self.person_model = YOLO(os.path.join(model_dir, "yolov8n.pt"))
        print(f"人员模型类别: {self.person_model.names}")

        print("正在加载 火焰/烟雾 检测模型...")
        # 网上下的火焰检测模型，约20MB，已经放在 src/models 目录下了
        self.fire_model = YOLO(os.path.join(model_dir, "fire_model.pt"))
        print(f"火焰模型类别: {self.fire_model.names}") 

    def detect_person(self, frame):
        """检测人员"""
        results = self.person_model(frame, classes=[0], verbose=False)
        has_person = False
        annotated_frame = frame.copy()
        for result in results:
            if len(result.boxes) > 0:
                has_person = True
            annotated_frame = result.plot()
        return has_person, annotated_frame

    def detect_fire(self, frame):
        """检测火焰和烟雾 - 在原始frame上检测，不在人员检测后的frame上"""
        results = self.fire_model(frame, conf=0.4, verbose=False)
        has_fire = False
        annotated_frame = frame.copy()
        for result in results:
            if len(result.boxes) > 0:
                has_fire = True
                annotated_frame = result.plot()
        return has_fire, annotated_frame