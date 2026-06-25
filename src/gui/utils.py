import cv2
from PIL import Image, ImageTk
import numpy as np

from .theme import BG, TEXT_DIM


def frame_to_photoimage(frame: np.ndarray, target_width: int, target_height: int) -> ImageTk.PhotoImage:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, (target_width, target_height))
    image = Image.fromarray(rgb)
    return ImageTk.PhotoImage(image)


def create_placeholder(width: int, height: int, text: str = "No Signal") -> ImageTk.PhotoImage:
    img = np.full((height, width, 3), (30, 30, 46), dtype=np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0
    thickness = 2
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
    tx = (width - tw) // 2
    ty = (height + th) // 2
    cv2.putText(img, text, (tx, ty), font, font_scale, (158, 158, 158), thickness)
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return ImageTk.PhotoImage(Image.fromarray(rgb))
