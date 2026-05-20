import tkinter as tk
from tkinter import ttk


class StatusPanel(ttk.Frame):
    def __init__(self, parent):
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
        self._fire_text.pack(side=tk.LEFT)

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

    def update_person_status(self, is_night_time, person_detected):
        if person_detected:
            self._mode_icon.config(bg="#D32F2F")
            self._mode_text.config(text="Night Security: INTRUSION!", foreground="#D32F2F")
        elif is_night_time:
            self._mode_icon.config(bg="#388E3C")
            self._mode_text.config(text="Night Security: ACTIVE", foreground="#388E3C")
        else:
            self._mode_icon.config(bg="#BDBDBD")
            self._mode_text.config(text="Night Security: OFF (daytime)", foreground="#757575")

    def update_fire_status(self, fire_detected):
        if fire_detected:
            self._fire_icon.config(bg="#D32F2F")
            self._fire_text.config(text="FIRE ALERT!", foreground="#D32F2F")
        else:
            self._fire_icon.config(bg="#388E3C")
            self._fire_text.config(text="Fire: Clear", foreground="#388E3C")

    def update_fps(self, fps):
        self._fps_label.config(text=f"FPS: {fps:.1f}")

    def update_last_alarm(self, alarm_info):
        if alarm_info is None:
            self._last_alarm.config(text="Last Alarm: None")
        else:
            event_type, timestamp, _ = alarm_info
            self._last_alarm.config(
                text=f"Last Alarm: [{event_type}] at {timestamp.strftime('%H:%M:%S')}",
                foreground="#D32F2F"
            )

    def update_camera_status(self, connected):
        if connected:
            self._camera_label.config(text="Camera: Connected", foreground="#388E3C")
        else:
            self._camera_label.config(text="Camera: Disconnected", foreground="#D32F2F")
