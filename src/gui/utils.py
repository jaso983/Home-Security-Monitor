import cv2
from PIL import Image, ImageTk
import numpy as np


def frame_to_photoimage(frame, target_width, target_height):
    """Convert OpenCV BGR frame to ImageTk.PhotoImage for tkinter display."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, (target_width, target_height))
    image = Image.fromarray(rgb)
    return ImageTk.PhotoImage(image)


def create_placeholder(width, height, text="No Signal"):
    """Generate a gray placeholder image with centered text."""
    img = np.full((height, width, 3), (60, 60, 60), dtype=np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0
    thickness = 2
    (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
    tx = (width - tw) // 2
    ty = (height + th) // 2
    cv2.putText(img, text, (tx, ty), font, font_scale, (180, 180, 180), thickness)
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return ImageTk.PhotoImage(Image.fromarray(rgb))
