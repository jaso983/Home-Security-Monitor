"""
火焰/烟雾检测模型训练脚本。

基于 YOLOv8n 进行迁移学习，在火焰/烟雾数据集上微调。
数据集需提前放置于 training/data/fire_smoke/ 目录下。

用法:
    python training/train_fire.py
    python training/train_fire.py --epochs 100 --batch 8
    python training/train_fire.py --data training/data/fire_smoke/data.yaml
"""

import argparse
import os
import sys

from ultralytics import YOLO


def train(
    data: str = "training/data/fire_smoke/data.yaml",
    epochs: int = 50,
    batch: int = 16,
    device: str = "0",
    patience: int = 20,
    imgsz: int = 640,
) -> str:
    """训练火焰/烟雾检测模型。"""
    if not os.path.exists(data):
        print(f"Error: Dataset config not found: {data}")
        print("Please download a fire/smoke dataset and place data.yaml at the path above.")
        print("Recommended: Roboflow Universe fire/smoke dataset in YOLOv8 format.")
        sys.exit(1)

    model = YOLO("yolov8n.pt")
    print(f"Training on device={device}, epochs={epochs}, batch={batch}")

    results = model.train(
        data=data,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        patience=patience,
        project="training/runs",
        name="fire_smoke",
        exist_ok=True,
        workers=0,
    )

    best_path = os.path.join("runs", "detect", "training", "runs", "fire_smoke", "weights", "best.pt")
    if os.path.exists(best_path):
        print(f"\nTraining complete! Best model: {best_path}")
        print(f"Run 'python training/export_model.py' to deploy to src/models/fire_model.pt")
    else:
        print("\nWarning: best.pt not found. Check training output.")

    return best_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train fire/smoke detection model")
    parser.add_argument("--data", default="training/data/fire_smoke/data.yaml")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="0")
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()

    train(data=args.data, epochs=args.epochs, batch=args.batch,
          device=args.device, patience=args.patience, imgsz=args.imgsz)
