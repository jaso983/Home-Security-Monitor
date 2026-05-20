import sqlite3
import os
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_path=None):
        if db_path is None:
            db_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(db_dir, "alarms.db")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                image_path TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def insert_alarm(self, event_type, image_path):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO alarms (event_type, timestamp, image_path) VALUES (?, ?, ?)",
            (event_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), image_path),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_recent_alarms(self, limit=50):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, event_type, timestamp, image_path FROM alarms ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return cursor.fetchall()

    def get_alarms_by_type(self, event_type, limit=50):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, event_type, timestamp, image_path FROM alarms WHERE event_type = ? ORDER BY id DESC LIMIT ?",
            (event_type, limit),
        )
        return cursor.fetchall()

    def delete_alarm(self, alarm_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM alarms WHERE id = ?", (alarm_id,))
        self.conn.commit()

    def clear_all(self):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM alarms")
        self.conn.commit()

    def close(self):
        self.conn.close()
