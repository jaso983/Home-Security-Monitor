"""
将训练好的最佳模型权重导出到部署目录。

从 training/runs/fire_smoke/weights/best.pt 复制到 src/models/fire_model.pt。
"""

import os
import shutil


def export_model(
    source: str = os.path.join("training", "runs", "home_fire", "weights", "best.pt"),
    target: str = os.path.join("src", "models", "fire_model.pt"),
) -> None:
    """导出训练模型到部署目录。"""
    if not os.path.exists(source):
        print(f"Error: Source model not found: {source}")
        print("Please run training first: python training/train_fire.py")
        return

    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copy2(source, target)
    print(f"Model exported: {source} -> {target}")

    from ultralytics import YOLO
    model = YOLO(target)
    print(f"Model classes: {model.names}")


if __name__ == "__main__":
    export_model()
