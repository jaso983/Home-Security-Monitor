import tkinter as tk

from .utils import frame_to_photoimage, create_placeholder
from .theme import BG, CARD, BORDER, RED

import numpy as np


class VideoFeedPanel(tk.Frame):
    """实时视频画面面板，深色主题。"""

    def __init__(self, parent: tk.Widget, video_width: int = 640, video_height: int = 480) -> None:
        super().__init__(parent, bg=BG, highlightbackground=BORDER, highlightthickness=1)
        self.video_width = video_width
        self.video_height = video_height

        header = tk.Label(
            self, text="  LIVE", bg=CARD, fg=RED,
            font=("", 9, "bold"), anchor=tk.W, padx=8, pady=3,
        )
        header.pack(fill=tk.X)

        self._placeholder = create_placeholder(video_width, video_height)
        self._current_photo = self._placeholder

        self._video_label = tk.Label(self, bg="#0D0D1A", anchor=tk.CENTER)
        self._video_label.pack(fill=tk.BOTH, expand=True, padx=2, pady=(0, 2))
        self._video_label.config(image=self._current_photo)

    def update_frame(self, frame: np.ndarray) -> None:
        self._current_photo = frame_to_photoimage(frame, self.video_width, self.video_height)
        self._video_label.config(image=self._current_photo)

    def show_placeholder(self) -> None:
        self._current_photo = self._placeholder
        self._video_label.config(image=self._placeholder)
