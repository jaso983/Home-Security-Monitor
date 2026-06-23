import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple

from .utils import frame_to_photoimage, create_placeholder

import numpy as np


class VideoFeedPanel(ttk.LabelFrame):
    """实时视频画面面板，显示摄像头画面或占位图。"""

    def __init__(self, parent: tk.Widget, video_width: int = 640, video_height: int = 480) -> None:
        """
        初始化视频面板。

        Args:
            parent: 父级 tkinter 容器。
            video_width: 视频显示宽度（像素）。
            video_height: 视频显示高度（像素）。
        """
        super().__init__(parent, text="Live Camera Feed", padding=5)
        self.video_width = video_width
        self.video_height = video_height

        self._placeholder = create_placeholder(video_width, video_height)
        self._current_photo = self._placeholder

        self._video_label = ttk.Label(self, anchor=tk.CENTER, relief=tk.SUNKEN)
        self._video_label.pack(fill=tk.BOTH, expand=True)
        self._video_label.config(image=self._current_photo)

    def update_frame(self, frame: np.ndarray) -> None:
        """
        更新视频画面。

        Args:
            frame: OpenCV BGR 视频帧。
        """
        self._current_photo = frame_to_photoimage(frame, self.video_width, self.video_height)
        self._video_label.config(image=self._current_photo)

    def show_placeholder(self) -> None:
        """显示无信号占位图。"""
        self._current_photo = self._placeholder
        self._video_label.config(image=self._placeholder)
