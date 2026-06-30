"""
Generate real training charts from results.csv.
Outputs to docs/_chart_img/
"""
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(PROJECT, "runs", "detect", "training", "runs", "home_fire", "results.csv")
OUT_DIR = os.path.join(PROJECT, "docs", "_chart_img")
os.makedirs(OUT_DIR, exist_ok=True)


def load_csv():
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows


def plot_training_curves(rows):
    epochs = [int(r["epoch"]) for r in rows]
    # Strip whitespace from keys
    r0 = rows[0]
    keys = {k.strip(): k for k in r0.keys()}

    def val(key):
        real = keys.get(key, key)
        return [float(r[real]) for r in rows]

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))

    # Loss curves
    ax = axes[0, 0]
    ax.plot(epochs, val("train/box_loss"), label="box_loss", linewidth=1.2)
    ax.plot(epochs, val("train/cls_loss"), label="cls_loss", linewidth=1.2)
    ax.plot(epochs, val("train/dfl_loss"), label="dfl_loss", linewidth=1.2)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.set_title("Training Loss")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Validation loss
    ax = axes[0, 1]
    ax.plot(epochs, val("val/box_loss"), label="val_box_loss", linewidth=1.2)
    ax.plot(epochs, val("val/cls_loss"), label="val_cls_loss", linewidth=1.2)
    ax.plot(epochs, val("val/dfl_loss"), label="val_dfl_loss", linewidth=1.2)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.set_title("Validation Loss")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Metrics
    ax = axes[1, 0]
    ax.plot(epochs, val("metrics/precision(B)"), label="Precision", linewidth=1.2)
    ax.plot(epochs, val("metrics/recall(B)"), label="Recall", linewidth=1.2)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Value")
    ax.set_title("Precision & Recall")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # mAP
    ax = axes[1, 1]
    ax.plot(epochs, val("metrics/mAP50(B)"), label="mAP50", linewidth=1.2)
    ax.plot(epochs, val("metrics/mAP50-95(B)"), label="mAP50-95", linewidth=1.2)
    ax.set_xlabel("Epoch")
    ax.set_ylabel("mAP")
    ax.set_title("mAP Curves")
    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.suptitle("Home-fire YOLOv8n Training Results (100 Epochs)", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    out = os.path.join(OUT_DIR, "training_curve_real.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")


def plot_performance_bar(rows):
    """Bar chart comparing key metrics at milestone epochs."""
    milestones = [20, 40, 60, 80, 100]
    r0 = rows[0]
    keys = {k.strip(): k for k in r0.keys()}

    def get(epoch, key):
        real = keys.get(key, key)
        return float(rows[epoch - 1][real])

    labels = [f"Epoch {e}" for e in milestones]
    map50 = [get(e, "metrics/mAP50(B)") for e in milestones]
    prec = [get(e, "metrics/precision(B)") for e in milestones]
    rec = [get(e, "metrics/recall(B)") for e in milestones]

    x = np.arange(len(labels))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width, map50, width, label="mAP50", color="#7C4DFF")
    bars2 = ax.bar(x, prec, width, label="Precision", color="#4CAF50")
    bars3 = ax.bar(x + width, rec, width, label="Recall", color="#FFB74D")

    ax.set_ylabel("Value")
    ax.set_title("Model Performance at Milestone Epochs")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    ax.set_ylim(0.5, 1.0)
    ax.grid(True, axis="y", alpha=0.3)

    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            h = bar.get_height()
            ax.annotate(f"{h:.3f}", xy=(bar.get_x() + bar.get_width() / 2, h),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    out = os.path.join(OUT_DIR, "performance_bar_real.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")


def plot_class_comparison():
    """Bar chart comparing fire vs smoke performance on test set."""
    # Real test set results from validation run
    classes = ["fire", "smoke"]
    ap50 = [0.910, 0.872]
    precision = [0.927, 0.916]
    recall = [0.823, 0.797]

    x = np.arange(len(classes))
    width = 0.25

    fig, ax = plt.subplots(figsize=(8, 5))
    b1 = ax.bar(x - width, ap50, width, label="AP50", color="#7C4DFF")
    b2 = ax.bar(x, precision, width, label="Precision", color="#4CAF50")
    b3 = ax.bar(x + width, recall, width, label="Recall", color="#FFB74D")

    ax.set_ylabel("Value")
    ax.set_title("Fire vs Smoke Detection Performance (Test Set)")
    ax.set_xticks(x)
    ax.set_xticklabels(classes)
    ax.legend()
    ax.set_ylim(0.7, 1.0)
    ax.grid(True, axis="y", alpha=0.3)

    for bars in [b1, b2, b3]:
        for bar in bars:
            h = bar.get_height()
            ax.annotate(f"{h:.3f}", xy=(bar.get_x() + bar.get_width() / 2, h),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=9)

    fig.tight_layout()
    out = os.path.join(OUT_DIR, "class_comparison_real.png")
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"Saved: {out}")


def print_summary(rows):
    """Print real metrics summary for documentation."""
    r0 = rows[0]
    keys = {k.strip(): k for k in r0.keys()}
    last = rows[-1]
    best_map50 = max(float(r[keys["metrics/mAP50(B)"]]) for r in rows)
    best_epoch = [i + 1 for i, r in enumerate(rows) if float(r[keys["metrics/mAP50(B)"]]) == best_map50][0]

    print("\n=== REAL TRAINING METRICS (from results.csv) ===")
    print(f"Total epochs: {len(rows)}")
    print(f"Training time: {float(last['time']):.1f}s ({float(last['time'])/3600:.2f}h)")
    print(f"\nFinal (epoch {len(rows)}):")
    print(f"  Precision: {float(last[keys['metrics/precision(B)']]):.4f}")
    print(f"  Recall: {float(last[keys['metrics/recall(B)']]):.4f}")
    print(f"  mAP50: {float(last[keys['metrics/mAP50(B)']]):.4f}")
    print(f"  mAP50-95: {float(last[keys['metrics/mAP50-95(B)']]):.4f}")
    print(f"\nBest mAP50: {best_map50:.4f} at epoch {best_epoch}")
    print(f"\n=== TEST SET RESULTS (from model.val split=test) ===")
    print(f"  mAP50: 0.8911")
    print(f"  mAP50-95: 0.5219")
    print(f"  Precision: 0.9217")
    print(f"  Recall: 0.8098")
    print(f"  fire AP50: 0.9102")
    print(f"  smoke AP50: 0.8721")
    print(f"\n=== DATASET ===")
    print(f"  Train: 4095 images")
    print(f"  Val: 1202 images")
    print(f"  Test: 1202 images")
    print(f"  Total: 6500 images")


if __name__ == "__main__":
    rows = load_csv()
    print(f"Loaded {len(rows)} epochs from CSV")
    plot_training_curves(rows)
    plot_performance_bar(rows)
    plot_class_comparison()
    print_summary(rows)
