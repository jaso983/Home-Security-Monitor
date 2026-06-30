"""在测试集图片上运行双模型推理，保存标注结果作为系统运行截图。"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import cv2
from ultralytics import YOLO

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TEST_IMAGES_DIR = os.path.join(PROJECT_ROOT, "training", "data", "data", "test", "images")
SCREENSHOTS_DIR = os.path.join(PROJECT_ROOT, "docs", "_screenshots")
PERSON_MODEL_PATH = os.path.join(PROJECT_ROOT, "src", "yolov8n.pt")
FIRE_MODEL_PATH = os.path.join(PROJECT_ROOT, "src", "models", "fire_model.pt")

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def main():
    person_model = YOLO(PERSON_MODEL_PATH)
    fire_model = YOLO(FIRE_MODEL_PATH)

    images = sorted(os.listdir(TEST_IMAGES_DIR))[:6]

    for i, img_name in enumerate(images):
        img_path = os.path.join(TEST_IMAGES_DIR, img_name)
        frame = cv2.imread(img_path)
        if frame is None:
            print(f"  Skip: {img_name}")
            continue

        frame_resized = cv2.resize(frame, (640, 480))

        # Person detection
        person_results = person_model(frame_resized, classes=[0], conf=0.5, verbose=False)
        annotated = person_results[0].plot()

        # Fire detection
        fire_results = fire_model(annotated, classes=[0, 1], conf=0.70, verbose=False)
        annotated = fire_results[0].plot()

        out_path = os.path.join(SCREENSHOTS_DIR, f"system_detection_{i + 1}.jpg")
        cv2.imwrite(out_path, annotated)
        print(f"  Saved: {out_path}")

    print(f"\nGenerated {len(images)} system detection screenshots.")


if __name__ == "__main__":
    main()
