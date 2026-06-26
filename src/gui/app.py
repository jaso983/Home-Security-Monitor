import os
import shutil
import cv2
import time
import logging
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

from models.yolo_detector import YoloDetector
from core.alarm_manager import AlarmManager
from core.db_manager import DatabaseManager
from core.face_recognizer import FaceRecognizer
from core.config import ConfigReader
from core.logger import setup_logging
from .video_panel import VideoFeedPanel
from .status_panel import StatusPanel
from .history_panel import HistoryPanel
from .theme import BG, CARD, BORDER, TEXT, TEXT_DIM, ACCENT, RED, GREEN, ORANGE

import numpy as np

logger = logging.getLogger(__name__)


class SecurityApp:
    """家庭安防监控 GUI 应用主控制器，深色主题。"""

    def __init__(self, root: tk.Tk) -> None:
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
        self.root.configure(bg=BG)

        self._configure_style()
        self._running: bool = True
        self._frame_count: int = 0
        self._fps_timer: float = time.time()
        self._fps_current: float = 0.0
        self._current_raw_frame: np.ndarray | None = None

        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.screenshot_dir: str = os.path.join(project_dir, "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)

        try:
            self.detector = YoloDetector(config=self._cfg.config)
            self.alarm_mgr = AlarmManager(
                cooldown_seconds=self._cfg.get("alarm", "cooldown_seconds", 10),
                iou_threshold=self._cfg.get("alarm", "iou_threshold", 0.2),
                track_max_age=self._cfg.get("alarm", "track_max_age", 90),
                no_face_delay_seconds=self._cfg.get("alarm", "no_face_delay_seconds", 10),
                no_face_night_delay_seconds=self._cfg.get("alarm", "no_face_night_delay_seconds", 3),
                person_alarm_gap=self._cfg.get("alarm", "person_alarm_gap", 5.0),
                fire_stable_frames=self._cfg.get("alarm", "fire_stable_frames", 3),
                smoke_stable_frames=self._cfg.get("alarm", "smoke_stable_frames", 5),
                person_stable_frames=self._cfg.get("alarm", "person_stable_frames", 3),
            )
            self.db = DatabaseManager()
            self.face_recognizer = FaceRecognizer(
                faces_dir=self._cfg.get("recognition", "faces_dir", ""),
                tolerance=self._cfg.get("recognition", "tolerance", 0.68),
            )
        except Exception as e:
            logger.error("Failed to initialize backend components: %s", e)
            messagebox.showerror("Init Error", f"Failed to initialize:\n{e}")
            self.root.destroy()
            return

        self.cap = cv2.VideoCapture(self._cfg.get("camera", "device_id", 0))
        self.camera_ok: bool = self.cap.isOpened()

        self._build_ui()

        if not self.camera_ok:
            self.video_panel.show_placeholder()
            self.status_panel.update_camera_status(False)
            messagebox.showwarning("Camera", "Cannot open camera 0. Will retry automatically.")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<Escape>", lambda e: self.on_close())

        self.root.after(500, self._detection_loop)

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=BG, foreground=TEXT, borderwidth=0)
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("TButton", padding=(10, 5), font=("", 9),
                         background=CARD, foreground=TEXT, borderwidth=0)
        style.map("TButton",
                   background=[("active", ACCENT), ("pressed", ACCENT)],
                   foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")])
        style.configure("Accent.TButton", background=ACCENT, foreground="#FFFFFF", font=("", 9, "bold"))
        style.map("Accent.TButton",
                   background=[("active", "#9C6DFF"), ("pressed", "#6A3DE8")])
        style.configure("Danger.TButton", background=RED, foreground="#FFFFFF")
        style.map("Danger.TButton",
                   background=[("active", "#FF7474"), ("pressed", "#D32F2F")])

    def _build_ui(self) -> None:
        main = tk.Frame(self.root, bg=BG, padx=10, pady=10)
        main.pack(fill=tk.BOTH, expand=True)

        # Title bar
        title_bar = tk.Frame(main, bg=BG)
        title_bar.pack(fill=tk.X, pady=(0, 8))
        tk.Label(title_bar, text="Home Security Monitor", bg=BG, fg=ACCENT,
                 font=("", 14, "bold")).pack(side=tk.LEFT)
        tk.Label(title_bar, text="v2.0", bg=BG, fg=TEXT_DIM,
                 font=("", 9)).pack(side=tk.LEFT, padx=(8, 0))

        # Content area
        content = tk.Frame(main, bg=BG)
        content.pack(fill=tk.BOTH, expand=True)

        # Left column - video + status
        left = tk.Frame(content, bg=BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        self.video_panel = VideoFeedPanel(
            left,
            self._cfg.get("camera", "width", 640),
            self._cfg.get("camera", "height", 480),
        )
        self.video_panel.pack(fill=tk.BOTH, expand=True)

        self.status_panel = StatusPanel(left)
        self.status_panel.pack(fill=tk.X, pady=(6, 0))

        # Right column - history + controls
        right = tk.Frame(content, bg=BG, width=320)
        right.pack(side=tk.RIGHT, fill=tk.BOTH)
        right.pack_propagate(False)

        self.history_panel = HistoryPanel(right, self.db)
        self.history_panel.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Control buttons
        self._build_controls(right)

    def _build_controls(self, parent: tk.Widget) -> None:
        ctrl = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        ctrl.pack(fill=tk.X)

        # Alarm actions
        alarm_frame = tk.Frame(ctrl, bg=CARD)
        alarm_frame.pack(fill=tk.X, padx=8, pady=(8, 4))
        tk.Label(alarm_frame, text="ALARMS", bg=CARD, fg=TEXT_DIM,
                 font=("", 7, "bold")).pack(anchor=tk.W, pady=(0, 4))

        btn_row1 = tk.Frame(alarm_frame, bg=CARD)
        btn_row1.pack(fill=tk.X)
        self._make_btn(btn_row1, "Refresh", self.history_panel.refresh).pack(side=tk.LEFT, padx=(0, 4))
        self._make_btn(btn_row1, "View", self._on_view_screenshot).pack(side=tk.LEFT, padx=(0, 4))
        self._make_btn(btn_row1, "Delete", self._on_delete_alarm).pack(side=tk.LEFT, padx=(0, 4))
        self._make_btn(btn_row1, "Clear All", self._on_clear_all, style="danger").pack(side=tk.LEFT)

        # Member actions
        member_frame = tk.Frame(ctrl, bg=CARD)
        member_frame.pack(fill=tk.X, padx=8, pady=(4, 4))
        tk.Label(member_frame, text="MEMBERS", bg=CARD, fg=TEXT_DIM,
                 font=("", 7, "bold")).pack(anchor=tk.W, pady=(0, 4))

        btn_row2 = tk.Frame(member_frame, bg=CARD)
        btn_row2.pack(fill=tk.X)
        self._make_btn(btn_row2, "Add Member", self._on_add_member, style="accent").pack(side=tk.LEFT, padx=(0, 4))
        self._make_btn(btn_row2, "Reload Faces", self._on_reload_faces).pack(side=tk.LEFT, padx=(0, 4))
        self._make_btn(btn_row2, "Manage Members", self._on_manage_members, style="danger").pack(side=tk.LEFT)

        # System
        sys_frame = tk.Frame(ctrl, bg=CARD)
        sys_frame.pack(fill=tk.X, padx=8, pady=(4, 8))
        self._make_btn(sys_frame, "Exit", self.on_close, style="danger").pack(side=tk.RIGHT)

    def _make_btn(self, parent, text, command, style="normal") -> tk.Button:
        if style == "accent":
            bg, fg, abg = ACCENT, "#FFFFFF", "#9C6DFF"
        elif style == "danger":
            bg, fg, abg = RED, "#FFFFFF", "#FF7474"
        else:
            bg, fg, abg = CARD, TEXT, ACCENT
        return tk.Button(
            parent, text=text, command=command,
            bg=bg, fg=fg, activebackground=abg, activeforeground="#FFFFFF",
            font=("", 8), relief=tk.FLAT, padx=8, pady=3,
            cursor="hand2", borderwidth=0,
        )

    def _detection_loop(self) -> None:
        if not self._running:
            return

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

        self._frame_count += 1
        elapsed = time.time() - self._fps_timer
        if elapsed >= self._cfg.get("gui", "fps_interval", 1.0):
            self._fps_current = self._frame_count / elapsed
            self._frame_count = 0
            self._fps_timer = time.time()
            self.status_panel.update_fps(self._fps_current)

        self.root.after(self._cfg.get("gui", "loop_delay_ms", 30), self._detection_loop)

    def _process_frame(self, frame: np.ndarray) -> None:
        is_night = self._check_time_in_range(
            self._cfg.get("monitor", "person_start", "00:00"),
            self._cfg.get("monitor", "person_end", "23:59"),
        )

        person_boxes: list = []
        identity_results: list = []
        has_person = False
        has_stranger = False
        has_no_face = False
        pending_person_alarms: list = []
        pending_fire_alarm = False
        base_frame = frame

        if is_night:
            person_boxes, person_frame = self.detector.detect_person(frame)
            base_frame = person_frame
            has_person = len(person_boxes) > 0

            if has_person:
                # 只对需要人脸识别的人员框执行 DeepFace（已确认 member 跳过，stranger 每5秒刷新）
                boxes_to_identify = self.alarm_mgr.get_boxes_needing_face_check(person_boxes)

                if boxes_to_identify:
                    identity_results = self.face_recognizer.identify_faces(frame, boxes_to_identify)
                # 所有人员框都参与 track 匹配，未识别的保持原身份
                pending_person_alarms = self.alarm_mgr.update(person_boxes, identity_results, is_night)

            for ti in self.alarm_mgr.get_display_identities():
                if ti["identity"] == "stranger":
                    has_stranger = True
                elif ti["identity"] == "no_face":
                    has_no_face = True

        fire_dets, fire_frame = self.detector.detect_fire(base_frame)
        has_fire = len(fire_dets) > 0
        display_frame = fire_frame if has_fire else base_frame

        if has_fire and self.alarm_mgr.should_trigger_fire_alarm({d["class_id"] for d in fire_dets}):
            pending_fire_alarm = True

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(display_frame, now_str, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        if is_night:
            cv2.putText(display_frame, "Night Security: ON", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        else:
            cv2.putText(display_frame, "Night Security: OFF", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        if is_night and has_person:
            for ti in self.alarm_mgr.get_display_identities():
                x1, y1, x2, y2 = [int(v) for v in ti["bbox"]]
                identity = ti["identity"]
                if identity.startswith("member:"):
                    label = f"[OK] {identity.split(':')[1]}"
                    color = (0, 200, 0)
                elif identity == "stranger":
                    label = "[ALERT] STRANGER"
                    color = (0, 0, 255)
                elif identity == "no_face":
                    label = "[ALERT] NO FACE"
                    color = (0, 200, 255)
                elif identity == "pending":
                    label = "..."
                    color = (180, 180, 180)
                else:
                    label = identity
                    color = (180, 180, 180)
                cv2.putText(display_frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        if has_fire:
            cv2.putText(display_frame, "[ALERT] FIRE DETECTED", (10, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        self._annotated_frame = display_frame

        for alarm in pending_person_alarms:
            self._save_alarm("person", alarm.get("reason", "stranger"))
        if pending_fire_alarm:
            self._save_alarm("fire")

        self.video_panel.update_frame(display_frame)
        self.status_panel.update_person_status(is_night, has_person, has_stranger, has_no_face)
        self.status_panel.update_fire_status(has_fire)
        self.status_panel.update_camera_status(True)

    def _save_alarm(self, event_type: str, reason: str = "") -> None:
        timestamp = datetime.now()
        filename = f"{event_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(self.screenshot_dir, filename)
        frame_to_save = getattr(self, '_annotated_frame', self._current_raw_frame)
        cv2.imwrite(filepath, frame_to_save)
        detail = f"{event_type}/{reason}" if reason else event_type
        self.db.insert_alarm(event_type, filepath)
        logger.warning("ALARM [%s] at %s, screenshot: %s", detail, timestamp.strftime("%H:%M:%S"), filepath)
        self.status_panel.update_last_alarm((event_type, timestamp, filepath))
        self.history_panel.refresh()

    def _check_time_in_range(self, start_str: str, end_str: str) -> bool:
        now = datetime.now().time()
        start = datetime.strptime(start_str, "%H:%M").time()
        end = datetime.strptime(end_str, "%H:%M").time()
        if start <= end:
            return start <= now <= end
        else:
            return now >= start or now <= end

    def _on_delete_alarm(self) -> None:
        if not self.history_panel.delete_selected():
            messagebox.showinfo("No Selection", "Please select an alarm row first.")

    def _on_clear_all(self) -> None:
        if messagebox.askyesno("Clear All", "Delete all alarm records and reset tracking?"):
            self.history_panel.clear_all()
            self.alarm_mgr.reset_tracks()

    def _on_view_screenshot(self) -> None:
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

    def _on_reload_faces(self) -> None:
        self.face_recognizer = FaceRecognizer(
            faces_dir=self._cfg.get("recognition", "faces_dir", ""),
            tolerance=self._cfg.get("recognition", "tolerance", 80.0),
        )
        if self.face_recognizer.trained:
            messagebox.showinfo("Reload Faces",
                                f"Loaded {self.face_recognizer.member_count} family member(s).")
        else:
            messagebox.showwarning("Reload Faces", "No valid face samples found.")

    def _get_faces_dir(self) -> str:
        faces_dir = self._cfg.get("recognition", "faces_dir", "")
        if not faces_dir:
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            faces_dir = os.path.join(project_dir, "models", "family_faces")
        return faces_dir

    def _on_manage_members(self) -> None:
        faces_dir = self._get_faces_dir()
        members = [f for f in os.listdir(faces_dir)
                   if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))]
        if not members:
            messagebox.showinfo("Manage Members", "No registered members.")
            return

        win = tk.Toplevel(self.root)
        win.title("Manage Members")
        win.configure(bg=CARD)
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text=f"Registered Members ({len(members)})", bg=CARD, fg=ACCENT,
                 font=("", 10, "bold")).pack(padx=12, pady=(10, 6), anchor=tk.W)

        list_frame = tk.Frame(win, bg=BG, highlightbackground=BORDER, highlightthickness=1)
        list_frame.pack(padx=12, pady=(0, 6), fill=tk.BOTH, expand=True)

        listbox = tk.Listbox(list_frame, bg=BG, fg=TEXT, selectbackground=ACCENT,
                             selectforeground="#FFFFFF", font=("", 9),
                             relief=tk.FLAT, highlightthickness=0, height=10)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        for m in members:
            listbox.insert(tk.END, os.path.splitext(m)[0])
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def delete_selected():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            name = members[idx]
            if messagebox.askyesno("Delete Member", f"Delete '{os.path.splitext(name)[0]}'?",
                                   parent=win):
                os.remove(os.path.join(faces_dir, name))
                listbox.delete(idx)
                members.pop(idx)

        def clear_all():
            if messagebox.askyesno("Clear All", "Delete ALL member photos?", parent=win):
                for m in members:
                    os.remove(os.path.join(faces_dir, m))
                members.clear()
                listbox.delete(0, tk.END)

        def on_close():
            self.face_recognizer = FaceRecognizer(
                faces_dir=faces_dir,
                tolerance=self._cfg.get("recognition", "tolerance", 80.0),
            )
            self.alarm_mgr.reset_tracks()
            win.destroy()

        btn_frame = tk.Frame(win, bg=CARD)
        btn_frame.pack(padx=12, pady=(0, 10), fill=tk.X)
        self._make_btn(btn_frame, "Delete", delete_selected, style="danger").pack(side=tk.LEFT, padx=(0, 4))
        self._make_btn(btn_frame, "Clear All", clear_all, style="danger").pack(side=tk.LEFT, padx=(0, 4))
        self._make_btn(btn_frame, "Close", on_close).pack(side=tk.RIGHT)

        win.protocol("WM_DELETE_WINDOW", on_close)

    def _on_add_member(self) -> None:
        """添加家庭成员：选择照片 → 输入名字 → 保存并重新训练。"""
        file_path = filedialog.askopenfilename(
            title="Select Member Photo",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")],
        )
        if not file_path:
            return

        name = simpledialog.askstring("Member Name", "Enter family member name:")
        if not name or not name.strip():
            return
        name = name.strip()

        faces_dir = self._get_faces_dir()
        os.makedirs(faces_dir, exist_ok=True)

        ext = os.path.splitext(file_path)[1] or ".jpg"
        dest = os.path.join(faces_dir, f"{name}{ext}")
        try:
            shutil.copy2(file_path, dest)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save photo:\n{e}")
            return

        self.face_recognizer = FaceRecognizer(
            faces_dir=faces_dir,
            tolerance=self._cfg.get("recognition", "tolerance", 80.0),
        )
        if self.face_recognizer.trained:
            messagebox.showinfo("Member Added",
                                f"Added '{name}' — {self.face_recognizer.member_count} member(s) loaded.")
        else:
            messagebox.showwarning("Training Failed",
                                   "Photo saved but face could not be detected. Try a clearer photo.")

    def on_close(self) -> None:
        self._running = False
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
        try:
            self.db.close()
        except Exception:
            pass
        logger.info("Application closed")
        self.root.destroy()
