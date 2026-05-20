import tkinter as tk
from tkinter import ttk

from .utils import frame_to_photoimage, create_placeholder


class VideoFeedPanel(ttk.LabelFrame):
    def __init__(self, parent, video_width=640, video_height=480):
        super().__init__(parent, text="Live Camera Feed", padding=5)
        self.video_width = video_width
        self.video_height = video_height

        self._placeholder = create_placeholder(video_width, video_height)
        self._current_photo = self._placeholder

        self._video_label = ttk.Label(self, anchor=tk.CENTER, relief=tk.SUNKEN)
        self._video_label.pack(fill=tk.BOTH, expand=True)
        self._video_label.config(image=self._current_photo)

    def update_frame(self, frame):
        self._current_photo = frame_to_photoimage(frame, self.video_width, self.video_height)
        self._video_label.config(image=self._current_photo)

    def show_placeholder(self):
        self._current_photo = self._placeholder
        self._video_label.config(image=self._placeholder)
