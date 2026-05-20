import os
import cv2
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

from models.yolo_detector import YoloDetector
from core.alarm_manager import AlarmManager
from core.db_manager import DatabaseManager
from .video_panel import VideoFeedPanel
from .status_panel import StatusPanel
from .history_panel import HistoryPanel


class SecurityApp:
    VIDEO_WIDTH = 640
    VIDEO_HEIGHT = 480
    LOOP_DELAY_MS = 30
    FPS_INTERVAL = 1.0
    PERSON_START = "00:00"
    PERSON_END = "23:59"

    def __init__(self, root):
        self.root = root
        self.root.title("Home Security Monitor")
        self.root.minsize(1024, 700)
        self.root.configure(bg="#F0F0F0")

        self._configure_style()
        self._running = True
        self._frame_count = 0
        self._fps_timer = time.time()
        self._fps_current = 0.0
        self._current_raw_frame = None

        # Screenshot directory
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.screenshot_dir = os.path.join(project_dir, "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)

        # Init backend components
        try:
            self.detector = YoloDetector()
            self.alarm_mgr = AlarmManager(cooldown_seconds=10)
            self.db = DatabaseManager()
        except Exception as e:
            messagebox.showerror("Init Error", f"Failed to initialize:\n{e}")
            self.root.destroy()
            return

        # Open camera
        self.cap = cv2.VideoCapture(0)
        self.camera_ok = self.cap.isOpened()

        # Build UI
        self._build_ui()

        if not self.camera_ok:
            self.video_panel.show_placeholder()
            self.status_panel.update_camera_status(False)
            messagebox.showwarning("Camera", "Cannot open camera 0. Will retry automatically.")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Escape>", lambda e: self.on_close())

        self.root.after(500, self._detection_loop)

    def _configure_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background="#F0F0F0", foreground="#212121")
        style.configure("TFrame", background="#F0F0F0")
        style.configure("TLabel", background="#F0F0F0", foreground="#212121")
        style.configure("TLabelFrame", background="#FFFFFF", relief=tk.RIDGE, borderwidth=1)
        style.configure("TLabelFrame.Label", background="#FFFFFF", foreground="#212121", font=("", 10, "bold"))
        style.configure("TButton", padding=(10, 4), font=("", 9))
        style.configure("Treeview", rowheight=24, background="#FFFFFF", fieldbackground="#FFFFFF")
        style.configure("Treeview.Heading", font=("", 9, "bold"))

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        paned = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left column
        left = ttk.Frame(paned)
        paned.add(left, weight=3)

        self.video_panel = VideoFeedPanel(left, self.VIDEO_WIDTH, self.VIDEO_HEIGHT)
        self.video_panel.pack(fill=tk.BOTH, expand=True)

        self.status_panel = StatusPanel(left)
        self.status_panel.pack(fill=tk.X, pady=(5, 0))

        # Right column
        right = ttk.Frame(paned)
        paned.add(right, weight=2)

        self.history_panel = HistoryPanel(right, self.db)
        self.history_panel.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(right)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(btn_frame, text="Refresh", command=self.history_panel.refresh).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="View Image", command=self._on_view_screenshot).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Delete", command=self._on_delete_alarm).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Clear All", command=self._on_clear_all).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Exit", command=self.on_close).pack(side=tk.RIGHT)

    def _detection_loop(self):
        if not self._running:
            return

        # Camera retry
        if not self.camera_ok:
            self.cap = cv2.VideoCapture(0)
            self.camera_ok = self.cap.isOpened()
            if not self.camera_ok:
                self.status_panel.update_camera_status(False)
                self.root.after(1000, self._detection_loop)
                return
            self.status_panel.update_camera_status(True)

        ret, frame = self.cap.read()
        if not ret:
            self.camera_ok = False
            self.video_panel.show_placeholder()
            self.root.after(1000, self._detection_loop)
            return

        self._current_raw_frame = frame.copy()
        self._process_frame(frame)

        # FPS
        self._frame_count += 1
        elapsed = time.time() - self._fps_timer
        if elapsed >= self.FPS_INTERVAL:
            self._fps_current = self._frame_count / elapsed
            self._frame_count = 0
            self._fps_timer = time.time()
            self.status_panel.update_fps(self._fps_current)

        self.root.after(self.LOOP_DELAY_MS, self._detection_loop)

    def _process_frame(self, frame):
        is_night = self._check_time_in_range(self.PERSON_START, self.PERSON_END)

        has_person = False
        base_frame = frame
        if is_night:
            has_person, person_frame = self.detector.detect_person(frame)
            base_frame = person_frame

        if has_person and self.alarm_mgr.should_trigger_alarm("person"):
            self._save_alarm("person")

        # 在可能已标注人体的帧上叠加火焰检测，避免相互覆盖
        has_fire, fire_frame = self.detector.detect_fire(base_frame)
        display_frame = fire_frame if has_fire else base_frame

        if has_fire and self.alarm_mgr.should_trigger_alarm("fire"):
            self._save_alarm("fire")

        # Overlay text on frame
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(display_frame, now_str, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        if is_night:
            cv2.putText(display_frame, "Night Security: ON", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        else:
            cv2.putText(display_frame, "Night Security: OFF", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        self.video_panel.update_frame(display_frame)
        self.status_panel.update_person_status(is_night, has_person)
        self.status_panel.update_fire_status(has_fire)
        self.status_panel.update_camera_status(True)

    def _save_alarm(self, event_type):
        timestamp = datetime.now()
        filename = f"{event_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(self.screenshot_dir, filename)
        cv2.imwrite(filepath, self._current_raw_frame)
        self.db.insert_alarm(event_type, filepath)
        self.status_panel.update_last_alarm((event_type, timestamp, filepath))
        self.history_panel.refresh()

    def _check_time_in_range(self, start_str, end_str):
        now = datetime.now().time()
        start = datetime.strptime(start_str, "%H:%M").time()
        end = datetime.strptime(end_str, "%H:%M").time()
        if start <= end:
            return start <= now <= end
        else:
            return now >= start or now <= end

    def _on_delete_alarm(self):
        if not self.history_panel.delete_selected():
            messagebox.showinfo("No Selection", "Please select an alarm row first.")

    def _on_clear_all(self):
        if messagebox.askyesno("Clear All", "Delete all alarm records? This cannot be undone."):
            self.history_panel.clear_all()

    def _on_view_screenshot(self):
        alarm = self.history_panel.get_selected_alarm()
        if alarm is None:
            messagebox.showinfo("No Selection", "Please select an alarm row first.")
            return
        image_path = alarm[3]
        if os.path.exists(image_path):
            try:
                os.startfile(image_path)
            except AttributeError:
                import subprocess
                subprocess.run(["xdg-open", image_path])
        else:
            messagebox.showwarning("File Not Found", f"Screenshot not found:\n{image_path}")

    def on_close(self):
        self._running = False
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
        try:
            self.db.close()
        except Exception:
            pass
        self.root.destroy()
