# Fire/Smoke Model Training

## Overview

Train a custom YOLOv8n fire/smoke detection model using transfer learning from COCO pretrained weights.

## Dataset

Download a fire/smoke dataset from Roboflow Universe in YOLOv8 format and place it under `training/data/fire_smoke/`:

```
training/data/fire_smoke/
  data.yaml          # nc=2, names: ['fire', 'smoke']
  train/
    images/
    labels/
  valid/
    images/
    labels/
  test/
    images/
    labels/
```

### data.yaml Example

```yaml
path: training/data/fire_smoke
train: train/images
val: valid/images
test: test/images

nc: 2
names:
  0: fire
  1: smoke
```

## Training

```bash
python training/train_fire.py
python training/train_fire.py --epochs 100 --batch 8 --device 0
python training/train_fire.py --device cpu --batch 4
```

Training results are saved to `training/runs/fire_smoke/`.

## Export

```bash
python training/export_model.py
```

Copies `training/runs/fire_smoke/weights/best.pt` to `src/models/fire_model.pt`.

## Class Index Mapping

| Index | Class |
|-------|-------|
| 0     | fire  |
| 1     | smoke |

Config `fire_classes: [0, 1]` matches these indices.

## Hardware

- Recommended: NVIDIA GPU with 8GB+ VRAM (RTX 4060 tested)
- CPU training works but is significantly slower
- Training time: ~20-40 minutes on RTX 4060 (50 epochs)
