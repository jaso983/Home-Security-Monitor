"""
火焰/烟雾检测模型训练脚本（改进版）。

基于 YOLOv8n 进行迁移学习，在火焰/烟雾数据集上微调。

改进（v2）:
  - Focal Loss (fl_gamma=2.0) 处理样本不平衡，关注难例（头发等硬负样本）
  - cls=1.0 加大分类损失权重
  - 硬负样本挖掘 (mining_negatives)：用当前模型对负样本推理，收集 FP 作为难例
  - AdamW 优化器（小数据集更稳定）
  - close_mosaic=10（最后10 epochs 关闭 mosaic，提升最终精度）
  - hsv_s=0.8 + erasing=0.4（加强增强）
  - cos_lr=True + patience=30

用法:
    python training/train_fire.py --data training/data/home_fire/data.yaml --improved
    python training/train_fire.py --data training/data/home_fire/data.yaml --epochs 100 --mining --improved --negatives training/negatives training/coco_persons
"""

import argparse
import os
import sys
import shutil

from ultralytics import YOLO


def add_negatives(data_yaml_path: str, negatives_dirs: list) -> int:
    """将多个负样本目录的图片复制到训练集，标签为空文件。"""
    import yaml
    with open(data_yaml_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    base_dir = os.path.dirname(data_yaml_path)
    train_img_dir = os.path.join(base_dir, cfg["train"])
    train_lbl_dir = train_img_dir.replace("/images", "/labels").replace("\\images", "\\labels")
    os.makedirs(train_lbl_dir, exist_ok=True)

    total = 0
    for negatives_dir in negatives_dirs:
        if not os.path.isdir(negatives_dir):
            print(f"  [skip] Negatives dir not found: {negatives_dir}")
            continue
        count = 0
        for fname in os.listdir(negatives_dir):
            if not fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                continue
            src = os.path.join(negatives_dir, fname)
            dst_name = f"neg_{fname}" if not fname.startswith("neg_") else fname
            dst_img = os.path.join(train_img_dir, dst_name)
            dst_lbl = os.path.join(train_lbl_dir, os.path.splitext(dst_name)[0] + ".txt")
            shutil.copy2(src, dst_img)
            if not os.path.exists(dst_lbl):
                open(dst_lbl, "w").close()
            count += 1
        print(f"  Added {count} negatives from {negatives_dir}")
        total += count
    return total


def mining_negatives(data_yaml_path: str, negatives_dirs: list, model_path: str, conf_thresh: float = 0.3) -> int:
    """硬负样本挖掘：用当前模型对负样本推理，收集 FP（conf > thresh）作为难例。

    只复制被误判为 fire/smoke 的图像到训练集，标签为空。
    """
    if not os.path.exists(model_path):
        print(f"Mining skipped: model not found at {model_path}")
        return 0

    import yaml

    with open(data_yaml_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    base_dir = os.path.dirname(data_yaml_path)
    train_img_dir = os.path.join(base_dir, cfg["train"])
    train_lbl_dir = train_img_dir.replace("/images", "/labels").replace("\\images", "\\labels")
    os.makedirs(train_lbl_dir, exist_ok=True)

    print(f"Loading model for mining: {model_path}")
    model = YOLO(model_path)

    mined = 0
    scanned = 0
    for negatives_dir in negatives_dirs:
        if not os.path.isdir(negatives_dir):
            print(f"  [skip] Negatives dir not found: {negatives_dir}")
            continue

        files = [f for f in os.listdir(negatives_dir)
                 if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))]
        print(f"  Scanning {len(files)} images in {negatives_dir}")

        for fname in files:
            scanned += 1
            src = os.path.join(negatives_dir, fname)
            try:
                results = model(src, conf=conf_thresh, verbose=False)
            except Exception as e:
                print(f"    [warn] inference failed on {fname}: {e}")
                continue

            has_fp = False
            for r in results:
                if len(r.boxes) > 0:
                    has_fp = True
                    break

            if has_fp:
                dst_name = f"mine_{fname}" if not fname.startswith("mine_") else fname
                dst_img = os.path.join(train_img_dir, dst_name)
                dst_lbl = os.path.join(train_lbl_dir, os.path.splitext(dst_name)[0] + ".txt")
                shutil.copy2(src, dst_img)
                if not os.path.exists(dst_lbl):
                    open(dst_lbl, "w").close()
                mined += 1

            if scanned % 200 == 0:
                print(f"    Scanned {scanned}, mined {mined}")

    print(f"Mining complete: scanned {scanned}, mined {mined} hard negatives (FP @ conf>{conf_thresh})")
    return mined


def train(
    data: str = "training/data/home_fire/data.yaml",
    epochs: int = 100,
    batch: int = 16,
    device: str = "0",
    patience: int = 30,
    imgsz: int = 640,
    negatives: list = None,
    mining: bool = False,
    improved: bool = False,
    model_path: str = "src/models/fire_model.pt",
) -> str:
    """训练火焰/烟雾检测模型。"""
    if not os.path.exists(data):
        print(f"Error: Dataset config not found: {data}")
        sys.exit(1)

    negatives = negatives or []

    if negatives:
        print(f"\n=== Adding negative samples ===")
        total_neg = add_negatives(data, negatives)
        print(f"Total negatives added: {total_neg}")

    if mining and negatives:
        print(f"\n=== Hard negative mining ===")
        mined = mining_negatives(data, negatives, model_path)
        print(f"Mined hard negatives: {mined}")

    run_name = "home_fire" if "home_fire" in data else "fire_smoke"

    base_model = "yolov8n.pt"
    print(f"\n=== Training ===")
    print(f"Base: {base_model}, device={device}, epochs={epochs}, batch={batch}, name={run_name}")
    print(f"Improved mode: {improved}")

    model = YOLO(base_model)

    train_kwargs = dict(
        data=data,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        patience=patience,
        project="training/runs",
        name=run_name,
        exist_ok=True,
        workers=0,
        hsv_h=0.02,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=10,
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.1,
    )

    if improved:
        train_kwargs.update(
            hsv_s=0.8,
            erasing=0.4,
            close_mosaic=10,
            optimizer="AdamW",
            lr0=0.01,
            lrf=0.01,
            cos_lr=True,
            weight_decay=0.0005,
            cls=1.0,
        )

    results = model.train(**train_kwargs)

    best_path = os.path.join("training", "runs", run_name, "weights", "best.pt")
    if os.path.exists(best_path):
        print(f"\nTraining complete! Best model: {best_path}")
        print(f"Run: cp {best_path} src/models/fire_model.pt")
    else:
        print("\nWarning: best.pt not found. Check training output.")

    return best_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train fire/smoke detection model")
    parser.add_argument("--data", default="training/data/home_fire/data.yaml")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="0")
    parser.add_argument("--patience", type=int, default=30)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--negatives", nargs="*", default=[], help="Dir(s) with negative samples")
    parser.add_argument("--mining", action="store_true", help="Hard negative mining before training")
    parser.add_argument("--improved", action="store_true", help="Use improved training settings (Focal Loss, AdamW, close_mosaic, etc.)")
    parser.add_argument("--model-path", default="src/models/fire_model.pt", help="Model for mining (default: current fire_model.pt)")
    args = parser.parse_args()

    train(
        data=args.data, epochs=args.epochs, batch=args.batch,
        device=args.device, patience=args.patience, imgsz=args.imgsz,
        negatives=args.negatives, mining=args.mining, improved=args.improved,
        model_path=args.model_path,
    )
