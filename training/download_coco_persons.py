"""
下载 COCO val2017 室内含人图像作为硬负样本（HuggingFace 镜像版）。

用途：
  解决 fire_model 把头发误判为 smoke 的问题。
  COCO val2017 含真实人物图像（头发、深色衣服、灯光反光），
  作为空标签负样本注入训练，让模型学习"这些纹理不是火/烟"。

筛选逻辑（符合家庭安防室内视角）:
  1. 用 instances_val2017.json 筛选含 person 的图像
  2. 用 captions_val2017.json 关键词筛选室内场景
     - 含 indoor/room/kitchen/bedroom/office/home 等关键词
     - 不含 outdoor/street/beach/mountain/field 等室外关键词

输出：
  training/coco_persons/  — 室内含人图像（无标签 = 负样本）

用法:
    python training/download_coco_persons.py
    python training/download_coco_persons.py --max-images 1000 --no-indoor-filter
"""

import argparse
import os
import sys
import json
import zipfile
import shutil

from huggingface_hub import hf_hub_download


VAL2017_REPO = "LibreYOLO/coco-val2017"
VAL2017_FILENAME = "coco-val2017.zip"

ANN_REPO = "pcuenq/coco-2017-mirror"
ANN_FILENAME = "annotations_trainval2017.zip"

DEFAULT_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "coco_persons")
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_coco_cache")


INDOOR_KEYWORDS = {
    "indoor", "inside", "room", "kitchen", "bedroom", "bathroom", "living",
    "dining", "office", "home", "house", "apartment", "restaurant", "cafe",
    "shop", "store", "mall", "school", "classroom", "gym", "studio",
    "lobby", "hallway", "corridor", "interior", "sitting room", "hotel",
}

OUTDOOR_KEYWORDS = {
    "outdoor", "outside", "street", "beach", "mountain", "field", "park",
    "sports", "yard", "garden", "road", "sidewalk", "sky", "ocean", "sea",
    "lake", "river", "forest", "desert", "stadium", "court", "pitch",
    "outdoor scene", "open field", "ski", "snow", "surf", "swim",
}


def extract(zip_path: str, dest_dir: str) -> None:
    print(f"Extracting: {zip_path}")
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest_dir)
    print(f"  -> {dest_dir}")


def find_dir(extract_root: str, name: str, must_contain_ext: str = "") -> str:
    for root, dirs, files in os.walk(extract_root):
        if os.path.basename(root) == name:
            if not must_contain_ext or any(f.endswith(must_contain_ext) for f in files):
                return root
    return ""


def find_file(extract_root: str, name: str) -> str:
    for root, _, files in os.walk(extract_root):
        if name in files:
            return os.path.join(root, name)
    return ""


def is_indoor_caption(captions: list) -> bool:
    """判断 captions 是否描述室内场景。"""
    text = " ".join(captions).lower()
    has_indoor = any(kw in text for kw in INDOOR_KEYWORDS)
    has_outdoor = any(kw in text for kw in OUTDOOR_KEYWORDS)
    return has_indoor and not has_outdoor


def filter_indoor_person_images(
    instances_json: str,
    captions_json: str,
    val2017_dir: str,
    out_dir: str,
    max_images: int,
    indoor_filter: bool,
) -> int:
    """筛选室内含人图像。"""
    print(f"Loading annotations: {instances_json}")
    with open(instances_json, "r", encoding="utf-8") as f:
        ann = json.load(f)

    person_cat_ids = {c["id"] for c in ann["categories"] if c["name"] == "person"}
    if not person_cat_ids:
        print("Error: 'person' category not found")
        return 0

    person_image_ids = {a["image_id"] for a in ann["annotations"] if a["category_id"] in person_cat_ids}
    print(f"Images containing person: {len(person_image_ids)}")

    id_to_file = {img["id"]: img["file_name"] for img in ann["images"]}

    indoor_ids = None
    if indoor_filter:
        print(f"Loading captions: {captions_json}")
        with open(captions_json, "r", encoding="utf-8") as f:
            caps = json.load(f)
        id_to_caps = {}
        for c in caps["annotations"]:
            id_to_caps.setdefault(c["image_id"], []).append(c["caption"])
        indoor_ids = {img_id for img_id, cs in id_to_caps.items() if is_indoor_caption(cs)}
        print(f"Indoor images (by caption keyword): {len(indoor_ids)}")

    target_ids = person_image_ids
    if indoor_ids is not None:
        target_ids = person_image_ids & indoor_ids
        print(f"Indoor + person intersection: {len(target_ids)}")

    os.makedirs(out_dir, exist_ok=True)
    copied = 0
    for img_id in target_ids:
        if max_images > 0 and copied >= max_images:
            break
        fname = id_to_file[img_id]
        src = os.path.join(val2017_dir, fname)
        if not os.path.exists(src):
            continue
        dst = os.path.join(out_dir, f"coco_{fname}")
        shutil.copy2(src, dst)
        copied += 1
        if copied % 100 == 0:
            print(f"  Copied {copied} images")

    print(f"Total copied: {copied} -> {out_dir}")
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(description="Download COCO val2017 indoor person images as hard negatives")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output directory")
    parser.add_argument("--max-images", type=int, default=0, help="Max images (0 = all)")
    parser.add_argument("--no-indoor-filter", action="store_true", help="Disable indoor caption filter")
    parser.add_argument("--keep-cache", action="store_true", help="Keep downloaded zip cache")
    args = parser.parse_args()

    os.makedirs(CACHE_DIR, exist_ok=True)

    print(f"Downloading val2017.zip from {VAL2017_REPO}...")
    val_zip = hf_hub_download(
        repo_id=VAL2017_REPO, filename=VAL2017_FILENAME,
        repo_type="dataset", cache_dir=CACHE_DIR,
    )
    print(f"  -> {val_zip} ({os.path.getsize(val_zip) / 1e6:.1f} MB)")

    val_extract = os.path.join(CACHE_DIR, "val_extract")
    if not os.path.isdir(val_extract) or not any(os.scandir(val_extract)):
        extract(val_zip, val_extract)
    val2017_dir = find_dir(val_extract, "val2017", ".jpg")
    if not val2017_dir:
        print("Error: val2017 directory not found after extraction")
        sys.exit(1)
    print(f"val2017 dir: {val2017_dir}")

    print(f"\nDownloading annotations from {ANN_REPO}...")
    ann_zip = hf_hub_download(
        repo_id=ANN_REPO, filename=ANN_FILENAME,
        repo_type="dataset", cache_dir=CACHE_DIR,
    )
    print(f"  -> {ann_zip} ({os.path.getsize(ann_zip) / 1e6:.1f} MB)")

    ann_extract = os.path.join(CACHE_DIR, "ann_extract")
    if not os.path.isdir(ann_extract) or not any(os.scandir(ann_extract)):
        extract(ann_zip, ann_extract)
    instances_json = find_file(ann_extract, "instances_val2017.json")
    captions_json = find_file(ann_extract, "captions_val2017.json")
    if not instances_json:
        print("Error: instances_val2017.json not found")
        sys.exit(1)
    if not captions_json:
        print("Error: captions_val2017.json not found (needed for indoor filter)")
        sys.exit(1)
    print(f"instances json: {instances_json}")
    print(f"captions json: {captions_json}")

    indoor_filter = not args.no_indoor_filter
    print(f"\nIndoor filter: {indoor_filter}")

    count = filter_indoor_person_images(
        instances_json, captions_json, val2017_dir, args.out, args.max_images, indoor_filter,
    )

    if not args.keep_cache:
        print("Cleaning cache...")
        shutil.rmtree(CACHE_DIR, ignore_errors=True)

    print(f"\nDone! {count} indoor person images saved to: {args.out}")
    print("Next: python training/train_fire.py --data training/data/home_fire/data.yaml --epochs 100 --mining --improved --negatives training/negatives training/coco_persons")


if __name__ == "__main__":
    main()
