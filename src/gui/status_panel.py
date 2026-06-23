import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import Optional, Tuple


class StatusPanel(ttk.Frame):
    """状态指示面板，显示安防模式、火警状态、FPS、最近报警和摄像头状态。"""

    def __init__(self, parent: tk.Widget) -> None:
        """
        初始化状态面板。

        Args:
            parent: 父级 tkinter 容器。
        """
        super().__init__(parent, padding=(0, 5, 0, 0))

        # Row 0: person mode + fire status + FPS
        row0 = ttk.Frame(self)
        row0.pack(fill=tk.X)

        self._mode_icon = tk.Label(row0, text="  ", width=2, font=("", 10, "bold"), relief=tk.RIDGE)
        self._mode_icon.pack(side=tk.LEFT, padx=(0, 5))
        self._mode_text = ttk.Label(row0, text="Night Security: OFF", font=("", 10))
        self._mode_text.pack(side=tk.LEFT, padx=(0, 20))

        self._fire_icon = tk.Label(row0, text="  ", width=2, font=("", 10, "bold"), relief=tk.RIDGE)
        self._fire_icon.pack(side=tk.LEFT, padx=(0, 5))
        self._fire_text = ttk.Label(row0, text="Fire: Clear", font=("", 10))
        self._fire_text.pack(side=tk.LEFT, padx=(0, 20))

        self._face_icon = tk.Label(row0, text="  ", width=2, font=("", 10, "bold"), relief=tk.RIDGE)
        self._face_icon.pack(side=tk.LEFT, padx=(0, 5))
        self._face_text = ttk.Label(row0, text="Person: --", font=("", 10))
        self._face_text.pack(side=tk.LEFT)

        self._fps_label = ttk.Label(row0, text="FPS: --", font=("", 9))
        self._fps_label.pack(side=tk.RIGHT)

        # Row 1: last alarm
        row1 = ttk.Frame(self)
        row1.pack(fill=tk.X, pady=(3, 0))
        self._last_alarm = ttk.Label(row1, text="Last Alarm: None", font=("", 9), foreground="#757575")
        self._last_alarm.pack(side=tk.LEFT)

        # Row 2: camera status
        row2 = ttk.Frame(self)
        row2.pack(fill=tk.X)
        self._camera_label = ttk.Label(row2, text="Camera: Connecting...", font=("", 9), foreground="#757575")
        self._camera_label.pack(side=tk.LEFT)

    def update_person_status(self, is_night_time: bool, person_detected: bool, is_stranger: bool = False) -> None:
        """更新人员安防状态显示。"""
        if person_detected and is_stranger:
            self._mode_icon.config(bg="#D32F2F")
            self._mode_text.config(text="Night Security: INTRUSION!", foreground="#D32F2F")
            self._face_icon.config(bg="#D32F2F")
            self._face_text.config(text="STRANGER!", foreground="#D32F2F")
        elif person_detected and not is_stranger:
            self._mode_icon.config(bg="#388E3C")
            self._mode_text.config(text="Night Security: Family", foreground="#388E3C")
            self._face_icon.config(bg="#388E3C")
            self._face_text.config(text="Family", foreground="#388E3C")
        elif is_night_time:
            self._mode_icon.config(bg="#388E3C")
            self._mode_text.config(text="Night Security: ACTIVE", foreground="#388E3C")
            self._face_icon.config(bg="#BDBDBD")
            self._face_text.config(text="Person: --", foreground="#757575")
        else:
            self._mode_icon.config(bg="#BDBDBD")
            self._mode_text.config(text="Night Security: OFF (daytime)", foreground="#757575")
            self._face_icon.config(bg="#BDBDBD")
            self._face_text.config(text="Person: --", foreground="#757575")

    def update_fire_status(self, fire_detected: bool) -> None:
        """
        更新火焰检测状态显示。

        Args:
            fire_detected: 是否检测到火焰/烟雾。
        """
        if fire_detected:
            self._fire_icon.config(bg="#D32F2F")
            self._fire_text.config(text="FIRE ALERT!", foreground="#D32F2F")
        else:
            self._fire_icon.config(bg="#388E3C")
            self._fire_text.config(text="Fire: Clear", foreground="#388E3C")

    def update_fps(self, fps: float) -> None:
        """
        更新 FPS 显示。

        Args:
            fps: 当前帧率。
        """
        self._fps_label.config(text=f"FPS: {fps:.1f}")

    def update_last_alarm(self, alarm_info: Optional[Tuple]) -> None:
        """
        更新最近报警信息显示。

        Args:
            alarm_info: (event_type, timestamp, image_path) 元组，或 None。
        """
        if alarm_info is None:
            self._last_alarm.config(text="Last Alarm: None")
        else:
            event_type, timestamp, _ = alarm_info
            self._last_alarm.config(
                text=f"Last Alarm: [{event_type}] at {timestamp.strftime('%H:%M:%S')}",
                foreground="#D32F2F",
            )

    def update_camera_status(self, connected: bool) -> None:
        """
        更新摄像头连接状态显示。

        Args:
            connected: 摄像头是否已连接。
        """
        if connected:
            self._camera_label.config(text="Camera: Connected", foreground="#388E3C")
        else:
            self._camera_label.config(text="Camera: Disconnected", foreground="#D32F2F")
