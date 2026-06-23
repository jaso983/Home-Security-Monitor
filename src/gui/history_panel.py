import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Tuple

from core.db_manager import DatabaseManager


class HistoryPanel(ttk.LabelFrame):
    """报警历史面板，以 Treeview 列表展示和管理报警记录。"""

    def __init__(self, parent: tk.Widget, db_manager: DatabaseManager) -> None:
        """
        初始化历史面板。

        Args:
            parent: 父级 tkinter 容器。
            db_manager: 数据库管理器实例。
        """
        super().__init__(parent, text="Alarm History", padding=5)
        self._db = db_manager

        self._tree = ttk.Treeview(
            self,
            columns=("id", "type", "timestamp", "path"),
            show="headings",
            selectmode="browse",
            height=18,
        )
        self._tree.heading("id", text="ID")
        self._tree.heading("type", text="Type")
        self._tree.heading("timestamp", text="Time")
        self._tree.heading("path", text="Screenshot")

        self._tree.column("id", width=40, anchor=tk.CENTER)
        self._tree.column("type", width=60, anchor=tk.CENTER)
        self._tree.column("timestamp", width=140)
        self._tree.column("path", width=120)

        self._tree.tag_configure("fire", background="#FFCDD2")
        self._tree.tag_configure("person", background="#FFE0B2")

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._tree.bind("<Double-1>", self._on_double_click)

        self.refresh()

    def refresh(self) -> None:
        """从数据库重新加载报警记录到列表。"""
        for item in self._tree.get_children():
            self._tree.delete(item)
        try:
            alarms = self._db.get_recent_alarms(limit=100)
        except Exception:
            return
        for alarm in alarms:
            row_id, event_type, timestamp, image_path = alarm
            tag = event_type if event_type in ("fire", "person") else ""
            self._tree.insert("", tk.END, values=(row_id, event_type, timestamp, image_path), tags=(tag,))

    def _on_double_click(self, event: tk.Event) -> None:
        """双击行时打开对应截图文件。"""
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
        """
        获取当前选中的报警记录。

        Returns:
            (id, event_type, timestamp, image_path) 元组，无选中时返回 None。
        """
        selection = self._tree.selection()
        if not selection:
            return None
        return self._tree.item(selection[0], "values")

    def delete_selected(self) -> bool:
        """
        删除当前选中的报警记录。

        Returns:
            是否成功删除。
        """
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
        """清空所有报警记录。"""
        self._db.clear_all()
        self.refresh()
