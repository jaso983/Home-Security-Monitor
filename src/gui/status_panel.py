import tkinter as tk
from typing import Optional, Tuple

from .theme import BG, CARD, BORDER, TEXT, TEXT_DIM, RED, GREEN, ORANGE, ACCENT


class StatusPanel(tk.Frame):
    """紧凑状态栏，单行显示所有状态，深色主题。"""

    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)

        row = tk.Frame(self, bg=CARD)
        row.pack(fill=tk.X, padx=8, pady=5)

        # Mode indicator
        self._mode_dot = tk.Label(row, text="  ", bg="#BDBDBD", width=1, relief=tk.FLAT)
        self._mode_dot.pack(side=tk.LEFT, padx=(0, 4))
        self._mode_text = tk.Label(row, text="Security: OFF", bg=CARD, fg=TEXT_DIM, font=("", 9))
        self._mode_text.pack(side=tk.LEFT, padx=(0, 12))

        # Fire indicator
        self._fire_dot = tk.Label(row, text="  ", bg=GREEN, width=1, relief=tk.FLAT)
        self._fire_dot.pack(side=tk.LEFT, padx=(0, 4))
        self._fire_text = tk.Label(row, text="Fire: Clear", bg=CARD, fg=GREEN, font=("", 9))
        self._fire_text.pack(side=tk.LEFT, padx=(0, 12))

        # Person indicator
        self._face_dot = tk.Label(row, text="  ", bg="#BDBDBD", width=1, relief=tk.FLAT)
        self._face_dot.pack(side=tk.LEFT, padx=(0, 4))
        self._face_text = tk.Label(row, text="Person: --", bg=CARD, fg=TEXT_DIM, font=("", 9))
        self._face_text.pack(side=tk.LEFT, padx=(0, 12))

        # Last alarm
        self._last_alarm = tk.Label(row, text="Last: --", bg=CARD, fg=TEXT_DIM, font=("", 8))
        self._last_alarm.pack(side=tk.LEFT, padx=(0, 8))

        # Camera + FPS on right
        self._camera_label = tk.Label(row, text="CAM: --", bg=CARD, fg=TEXT_DIM, font=("", 8))
        self._camera_label.pack(side=tk.RIGHT, padx=(8, 0))
        self._fps_label = tk.Label(row, text="FPS: --", bg=CARD, fg=TEXT_DIM, font=("", 8))
        self._fps_label.pack(side=tk.RIGHT)

    def update_person_status(
        self, is_night_time: bool, person_detected: bool,
        is_stranger: bool = False, has_no_face: bool = False,
    ) -> None:
        if person_detected and is_stranger:
            self._mode_dot.config(bg=RED)
            self._mode_text.config(text="INTRUSION!", fg=RED)
            self._face_dot.config(bg=RED)
            self._face_text.config(text="STRANGER", fg=RED)
        elif person_detected and has_no_face:
            if is_night_time:
                self._mode_dot.config(bg=RED)
                self._mode_text.config(text="INTRUSION!", fg=RED)
                self._face_dot.config(bg=ORANGE)
                self._face_text.config(text="NO FACE", fg=ORANGE)
            else:
                self._mode_dot.config(bg=ORANGE)
                self._mode_text.config(text="Verifying...", fg=ORANGE)
                self._face_dot.config(bg=ORANGE)
                self._face_text.config(text="NO FACE", fg=ORANGE)
        elif person_detected and not is_stranger and not has_no_face:
            self._mode_dot.config(bg=GREEN)
            self._mode_text.config(text="Security: Family", fg=GREEN)
            self._face_dot.config(bg=GREEN)
            self._face_text.config(text="Family", fg=GREEN)
        elif is_night_time:
            self._mode_dot.config(bg=ACCENT)
            self._mode_text.config(text="Night: ACTIVE", fg=ACCENT)
            self._face_dot.config(bg="#BDBDBD")
            self._face_text.config(text="Person: --", fg=TEXT_DIM)
        else:
            self._mode_dot.config(bg="#BDBDBD")
            self._mode_text.config(text="Security: OFF", fg=TEXT_DIM)
            self._face_dot.config(bg="#BDBDBD")
            self._face_text.config(text="Person: --", fg=TEXT_DIM)

    def update_fire_status(self, fire_detected: bool) -> None:
        if fire_detected:
            self._fire_dot.config(bg=RED)
            self._fire_text.config(text="FIRE!", fg=RED)
        else:
            self._fire_dot.config(bg=GREEN)
            self._fire_text.config(text="Fire: Clear", fg=GREEN)

    def update_fps(self, fps: float) -> None:
        self._fps_label.config(text=f"FPS: {fps:.1f}")

    def update_last_alarm(self, alarm_info: Optional[Tuple]) -> None:
        if alarm_info is None:
            self._last_alarm.config(text="Last: --", fg=TEXT_DIM)
        else:
            event_type, timestamp, _ = alarm_info
            self._last_alarm.config(
                text=f"Last: [{event_type}] {timestamp.strftime('%H:%M:%S')}",
                fg=RED,
            )

    def update_camera_status(self, connected: bool) -> None:
        if connected:
            self._camera_label.config(text="CAM: OK", fg=GREEN)
        else:
            self._camera_label.config(text="CAM: OFF", fg=RED)
