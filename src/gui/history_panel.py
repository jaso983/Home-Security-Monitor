import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox


class HistoryPanel(ttk.LabelFrame):
    def __init__(self, parent, db_manager):
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

    def refresh(self):
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

    def _on_double_click(self, event):
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

    def get_selected_alarm(self):
        selection = self._tree.selection()
        if not selection:
            return None
        return self._tree.item(selection[0], "values")

    def delete_selected(self):
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

    def clear_all(self):
        self._db.clear_all()
        self.refresh()
