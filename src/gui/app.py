import os
import cv2
import time
import logging
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

from models.yolo_detector import YoloDetector
from core.alarm_manager import AlarmManager
from core.db_manager import DatabaseManager
from core.face_recognizer import FaceRecognizer
from core.config import ConfigReader
from core.logger import setup_logging
from .video_panel import VideoFeedPanel
from .status_panel import StatusPanel
from .history_panel import HistoryPanel

import numpy as np

logger = logging.getLogger(__name__)


class SecurityApp:
    """家庭安防监控 GUI 应用主控制器，管理检测循环和界面交互。"""

    VIDEO_WIDTH: int = 640
    VIDEO_HEIGHT: int = 480
    LOOP_DELAY_MS: int = 30
    FPS_INTERVAL: float = 1.0
    PERSON_START: str = "00:00"
    PERSON_END: str = "23:59"

    def __init__(self, root: tk.Tk) -> None:
        """
        初始化安防应用。

        Args:
            root: tkinter 根窗口。
        """
        # Load config and setup logging
        self._cfg = ConfigReader()
        setup_logging(
            level=self._cfg.get("logging", "level", "INFO"),
            log_file=self._cfg.get("logging", "file"),
        )
        self.root = root
        self.root.title("Home Security Monitor")
        self.root.minsize(
            self._cfg.get("gui", "min_width", 1024),
            self._cfg.get("gui", "min_height", 700),
        )
        self.root.configure(bg="#F0F0F0")

        self._configure_style()
        self._running: bool = True
        self._frame_count: int = 0
        self._fps_timer: float = time.time()
        self._fps_current: float = 0.0
        self._current_raw_frame: np.ndarray | None = None

        # Screenshot directory
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.screenshot_dir: str = os.path.join(project_dir, "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)

        # Init backend components
        try:
            self.detector = YoloDetector(config=self._cfg.config)
            self.alarm_mgr = AlarmManager(
                cooldown_seconds=self._cfg.get("alarm", "cooldown_seconds", 10),
            )
            self.db = DatabaseManager()
            self.face_recognizer = FaceRecognizer(
                faces_dir=self._cfg.get("recognition", "faces_dir", ""),
                tolerance=self._cfg.get("recognition", "tolerance", 80.0),
            )
        except Exception as e:
            logger.error("Failed to initialize backend components: %s", e)
            messagebox.showerror("Init Error", f"Failed to initialize:\n{e}")
            self.root.destroy()
            return

        # Open camera
        self.cap = cv2.VideoCapture(self._cfg.get("camera", "device_id", 0))
        self.camera_ok: bool = self.cap.isOpened()

        # Build UI
        self._build_ui()

        if not self.camera_ok:
            self.video_panel.show_placeholder()
            self.status_panel.update_camera_status(False)
            messagebox.showwarning("Camera", "Cannot open camera 0. Will retry automatically.")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Escape>", lambda e: self.on_close())

        self.root.after(500, self._detection_loop)

    def _configure_style(self) -> None:
        """配置 ttk 主题和样式。"""
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

    def _build_ui(self) -> None:
        """构建 GUI 界面布局。"""
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        paned = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left column
        left = ttk.Frame(paned)
        paned.add(left, weight=3)

        self.video_panel = VideoFeedPanel(
            left,
            self._cfg.get("camera", "width", 640),
            self._cfg.get("camera", "height", 480),
        )
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

    def _detection_loop(self) -> None:
        """检测主循环：读取视频帧、执行检测、更新界面。"""
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
            logger.info("Camera reconnected")

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
        if elapsed >= self._cfg.get("gui", "fps_interval", 1.0):
            self._fps_current = self._frame_count / elapsed
            self._frame_count = 0
            self._fps_timer = time.time()
            self.status_panel.update_fps(self._fps_current)

        self.root.after(self._cfg.get("gui", "loop_delay_ms", 30), self._detection_loop)

    def _process_frame(self, frame: np.ndarray) -> None:
        """
        对单帧画面执行人员检测和火焰检测，更新界面状态。

        Args:
            frame: OpenCV BGR 视频帧。
        """
        is_night = self._check_time_in_range(
            self._cfg.get("monitor", "person_start", "00:00"),
            self._cfg.get("monitor", "person_end", "23:59"),
        )

        has_person = False
        is_stranger = False
        base_frame = frame
        if is_night:
            has_person, person_frame = self.detector.detect_person(frame)
            base_frame = person_frame

        if has_person:
            is_stranger = self.face_recognizer.is_stranger(frame)
            if is_stranger and self.alarm_mgr.should_trigger_alarm("person"):
                self._save_alarm("person")

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
        self.status_panel.update_person_status(is_night, has_person, is_stranger)
        self.status_panel.update_fire_status(has_fire)
        self.status_panel.update_camera_status(True)

    def _save_alarm(self, event_type: str) -> None:
        """
        保存报警截图并写入数据库。

        Args:
            event_type: 报警类型（"fire" 或 "person"）。
        """
        timestamp = datetime.now()
        filename = f"{event_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(self.screenshot_dir, filename)
        cv2.imwrite(filepath, self._current_raw_frame)
        self.db.insert_alarm(event_type, filepath)
        logger.warning("ALARM [%s] at %s, screenshot: %s", event_type, timestamp.strftime("%H:%M:%S"), filepath)
        self.status_panel.update_last_alarm((event_type, timestamp, filepath))
        self.history_panel.refresh()

    def _check_time_in_range(self, start_str: str, end_str: str) -> bool:
        """
        检查当前时间是否在指定时段内（支持跨午夜时段）。

        Args:
            start_str: 开始时间，格式 "HH:MM"。
            end_str: 结束时间，格式 "HH:MM"。

        Returns:
            当前时间是否在时段内。
        """
        now = datetime.now().time()
        start = datetime.strptime(start_str, "%H:%M").time()
        end = datetime.strptime(end_str, "%H:%M").time()
        if start <= end:
            return start <= now <= end
        else:
            return now >= start or now <= end

    def _on_delete_alarm(self) -> None:
        """删除选中的报警记录。"""
        if not self.history_panel.delete_selected():
            messagebox.showinfo("No Selection", "Please select an alarm row first.")

    def _on_clear_all(self) -> None:
        """清空所有报警记录（需用户确认）。"""
        if messagebox.askyesno("Clear All", "Delete all alarm records? This cannot be undone."):
            self.history_panel.clear_all()

    def _on_view_screenshot(self) -> None:
        """查看选中报警记录的截图。"""
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

    def on_close(self) -> None:
        """关闭应用：释放摄像头、关闭数据库、销毁窗口。"""
        self._running = False
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
        try:
            self.db.close()
        except Exception:
            pass
        logger.info("Application closed")
        self.root.destroy()
