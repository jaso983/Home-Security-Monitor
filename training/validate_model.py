"""
验证火焰/烟雾检测模型性能。

核心指标:
  1. home_fire test 集 mAP@50、precision、recall
  2. 硬负样本集（coco_persons + negatives）FP 率 — 衡量头发误判改善程度

用法:
    python training/validate_model.py --model src/models/fire_model.pt
    python training/validate_model.py --model src/models/fire_model.pt --data training/data/home_fire/data.yaml
    python training/validate_model.py --model src/models/fire_model.pt --negatives training/coco_persons training/negatives
"""

import argparse
import os
import sys

from ultralytics import YOLO


def validate_map(model_path: str, data: str) -> dict:
    """在测试集上计算 mAP。"""
    if not os.path.exists(data):
        print(f"[skip] data config not found: {data}")
        return {}

    print(f"\n=== mAP validation on {data} ===")
    model = YOLO(model_path)
    metrics = model.val(data=data, split="test", verbose=True)

    results = {
        "mAP50": float(metrics.box.map50),
        "mAP50-95": float(metrics.box.map),
        "precision": float(metrics.box.mp),
        "recall": float(metrics.box.mr),
    }

    print(f"\nmAP@50:     {results['mAP50']:.4f}")
    print(f"mAP@50-95:  {results['mAP50-95']:.4f}")
    print(f"Precision:  {results['precision']:.4f}")
    print(f"Recall:     {results['recall']:.4f}")

    if hasattr(metrics.box, "ap_class_index") and hasattr(metrics.box, "ap50"):
        names = metrics.names
        for idx, ap50 in zip(metrics.box.ap_class_index, metrics.box.ap50):
            cls_name = names[int(idx)] if names else str(idx)
            print(f"  {cls_name}: AP@50 = {float(ap50):.4f}")

    return results


def validate_fp_rate(model_path: str, negatives_dirs: list, conf_thresh: float = 0.3) -> dict:
    """在硬负样本集上计算 FP 率（检测到 fire/smoke 的图像比例）。"""
    print(f"\n=== Hard negative FP rate (conf > {conf_thresh}) ===")

    model = YOLO(model_path)

    total = 0
    fp_count = 0
    per_dir = {}

    for neg_dir in negatives_dirs:
        if not os.path.isdir(neg_dir):
            print(f"  [skip] not found: {neg_dir}")
            continue

        files = [f for f in os.listdir(neg_dir)
                 if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))]
        dir_total = 0
        dir_fp = 0

        for fname in files:
            dir_total += 1
            src = os.path.join(neg_dir, fname)
            try:
                results = model(src, conf=conf_thresh, verbose=False)
            except Exception as e:
                print(f"    [warn] inference failed on {fname}: {e}")
                continue

            has_detection = False
            for r in results:
                if len(r.boxes) > 0:
                    has_detection = True
                    break

            if has_detection:
                dir_fp += 1

        total += dir_total
        fp_count += dir_fp
        rate = dir_fp / dir_total if dir_total > 0 else 0
        per_dir[neg_dir] = {"total": dir_total, "fp": dir_fp, "rate": rate}
        print(f"  {neg_dir}: {dir_fp}/{dir_total} = {rate:.2%}")

    overall_rate = fp_count / total if total > 0 else 0
    print(f"\n  Overall: {fp_count}/{total} = {overall_rate:.2%}")

    return {
        "total": total,
        "fp": fp_count,
        "rate": overall_rate,
        "per_dir": per_dir,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate fire/smoke model")
    parser.add_argument("--model", default="src/models/fire_model.pt")
    parser.add_argument("--data", default="training/data/home_fire/data.yaml")
    parser.add_argument("--negatives", nargs="*", default=["training/coco_persons", "training/negatives"])
    parser.add_argument("--conf", type=float, default=0.3, help="Confidence threshold for FP")
    args = parser.parse_args()

    if not os.path.exists(args.model):
        print(f"Error: model not found: {args.model}")
        sys.exit(1)

    map_results = validate_map(args.model, args.data)
    fp_results = validate_fp_rate(args.model, args.negatives, args.conf)

    print("\n=== Summary ===")
    if map_results:
        print(f"mAP@50:    {map_results['mAP50']:.4f}  (target >= 0.92)")
        print(f"Precision: {map_results['precision']:.4f}  (target >= 0.95)")
    print(f"FP rate:   {fp_results['rate']:.2%}  (target < 2%)")

    if fp_results["rate"] < 0.02 and (not map_results or map_results["mAP50"] >= 0.92):
        print("\n[OK] Model passes validation. Safe to deploy.")
    else:
        print("\n[WARN] Model does not meet targets. Review metrics above.")


if __name__ == "__main__":
    main()
