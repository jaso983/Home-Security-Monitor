import cv2
from PIL import Image, ImageTk
import numpy as np


def frame_to_photoimage(frame: np.ndarray, target_width: int, target_height: int) -> ImageTk.PhotoImage:
    """
    将 OpenCV BGR 帧转换为 tkinter 可显示的 PhotoImage。

    Args:
        frame: OpenCV BGR 视频帧。
        target_width: 目标显示宽度。
        target_height: 目标显示高度。

    Returns:
        缩放后的 ImageTk.PhotoImage 对象。
    """
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, (target_width, target_height))
    image = Image.fromarray(rgb)
    return ImageTk.PhotoImage(image)


def create_placeholder(width: int, height: int, text: str = "No Signal") -> ImageTk.PhotoImage:
    """
    生成灰色占位图，中央显示文字。

    Args:
        width: 图像宽度。
        height: 图像高度。
        text: 中央显示的文字内容。

    Returns:
        ImageTk.PhotoImage 占位图对象。
    """
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
