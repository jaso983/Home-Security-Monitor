import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Tuple

from core.db_manager import DatabaseManager
from .theme import BG, CARD, BORDER, TEXT, TEXT_DIM, RED, ORANGE, ACCENT


class HistoryPanel(tk.Frame):
    """报警历史面板，深色主题 Treeview。"""

    ROW_ALT = "#252538"

    def __init__(self, parent: tk.Widget, db_manager: DatabaseManager) -> None:
        super().__init__(parent, bg=BG, highlightbackground=BORDER, highlightthickness=1)
        self._db = db_manager

        header = tk.Label(
            self, text="  ALARM HISTORY", bg=CARD, fg=ACCENT,
            font=("", 9, "bold"), anchor=tk.W, padx=8, pady=3,
        )
        header.pack(fill=tk.X)

        style = ttk.Style()
        style.configure(
            "Dark.Treeview",
            background=CARD, foreground=TEXT, fieldbackground=CARD,
            rowheight=24, font=("", 9),
        )
        style.configure(
            "Dark.Treeview.Heading",
            background="#252538", foreground=TEXT, font=("", 8, "bold"),
            relief=tk.FLAT,
        )
        style.map(
            "Dark.Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", "#FFFFFF")],
        )

        tree_frame = tk.Frame(self, bg=BG)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self._tree = ttk.Treeview(
            tree_frame,
            columns=("id", "type", "timestamp", "path"),
            show="headings",
            selectmode="browse",
            height=16,
            style="Dark.Treeview",
        )
        self._tree.heading("id", text="ID")
        self._tree.heading("type", text="Type")
        self._tree.heading("timestamp", text="Time")
        self._tree.heading("path", text="Screenshot")

        self._tree.column("id", width=36, anchor=tk.CENTER)
        self._tree.column("type", width=60, anchor=tk.CENTER)
        self._tree.column("timestamp", width=130)
        self._tree.column("path", width=100)

        self._tree.tag_configure("fire", foreground=RED)
        self._tree.tag_configure("person", foreground=ORANGE)
        self._tree.tag_configure("alt", background=self.ROW_ALT)

        scrollbar = tk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._tree.yview,
                                 bg=CARD, troughcolor=BG)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._tree.bind("<Double-1>", self._on_double_click)

        self.refresh()

    def refresh(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        try:
            alarms = self._db.get_recent_alarms(limit=100)
        except Exception:
            return
        for idx, alarm in enumerate(alarms):
            row_id, event_type, timestamp, image_path = alarm
            tag = event_type if event_type in ("fire", "person") else ""
            alt = "alt" if idx % 2 == 1 else ""
            tags = tuple(filter(None, (tag, alt)))
            self._tree.insert("", tk.END, values=(row_id, event_type, timestamp, image_path), tags=tags)

    def _on_double_click(self, event: tk.Event) -> None:
        selection = self._tree.selection()
        if not selection:
            return
        values = self._tree.item(selection[0], "values")
        if not values:
            return
        image_path = values[3]
        if os.path.exists(image_path):
            try:
                os.startfile(image_path)
            except AttributeError:
                subprocess.run(["xdg-open", image_path])
        else:
            messagebox.showwarning("File Not Found", f"Screenshot not found:\n{image_path}")

    def get_selected_alarm(self) -> Optional[Tuple]:
        selection = self._tree.selection()
        if not selection:
            return None
        return self._tree.item(selection[0], "values")

    def delete_selected(self) -> bool:
        selection = self._tree.selection()
        if not selection:
            return False
        values = self._tree.item(selection[0], "values")
        if not values:
            return False
        alarm_id = int(values[0])
        self._db.delete_alarm(alarm_id)
        self.refresh()
        return True

    def clear_all(self) -> None:
        self._db.clear_all()
        self.refresh()
