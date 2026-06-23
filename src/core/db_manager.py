import sqlite3
import os
import logging
from datetime import datetime
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class DatabaseManager:
    """SQLite 数据库管理器，负责报警记录的 CRUD 操作。"""

    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        初始化数据库连接并建表。

        Args:
            db_path: 数据库文件路径，默认为 src/core/alarms.db。

        Raises:
            sqlite3.OperationalError: 数据库连接或建表失败时抛出。
        """
        if db_path is None:
            db_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(db_dir, "alarms.db")
        try:
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self._init_db()
            logger.info("Database initialized: %s", db_path)
        except sqlite3.OperationalError as e:
            logger.error("Database initialization failed: %s", e)
            raise

    def _init_db(self) -> None:
        """创建 alarms 表（如不存在）。"""
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

    def insert_alarm(self, event_type: str, image_path: str) -> Optional[int]:
        """
        插入一条报警记录。

        Args:
            event_type: 报警类型（"fire" 或 "person"）。
            image_path: 截图文件路径。

        Returns:
            新插入记录的自增 ID，失败时返回 None。
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO alarms (event_type, timestamp, image_path) VALUES (?, ?, ?)",
                (event_type, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), image_path),
            )
            self.conn.commit()
            logger.info("Inserted alarm: type=%s, id=%s", event_type, cursor.lastrowid)
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error("Failed to insert alarm: %s", e)
            return None

    def get_recent_alarms(self, limit: int = 50) -> List[Tuple]:
        """
        查询最近的报警记录，按 ID 降序排列。

        Args:
            limit: 返回记录数量上限。

        Returns:
            报警记录元组列表，每项为 (id, event_type, timestamp, image_path)。查询失败返回空列表。
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, event_type, timestamp, image_path FROM alarms ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error("Failed to query recent alarms: %s", e)
            return []

    def get_alarms_by_type(self, event_type: str, limit: int = 50) -> List[Tuple]:
        """
        按报警类型筛选记录。

        Args:
            event_type: 报警类型（"fire" 或 "person"）。
            limit: 返回记录数量上限。

        Returns:
            报警记录元组列表。查询失败返回空列表。
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, event_type, timestamp, image_path FROM alarms WHERE event_type = ? ORDER BY id DESC LIMIT ?",
                (event_type, limit),
            )
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error("Failed to query alarms by type: %s", e)
            return []

    def delete_alarm(self, alarm_id: int) -> bool:
        """
        删除指定 ID 的报警记录。

        Args:
            alarm_id: 要删除的记录 ID。

        Returns:
            是否成功删除。
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM alarms WHERE id = ?", (alarm_id,))
            self.conn.commit()
            logger.info("Deleted alarm id=%s", alarm_id)
            return True
        except sqlite3.Error as e:
            logger.error("Failed to delete alarm id=%s: %s", alarm_id, e)
            return False

    def clear_all(self) -> None:
        """清空所有报警记录。"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM alarms")
            self.conn.commit()
            logger.info("Cleared all alarm records")
        except sqlite3.Error as e:
            logger.error("Failed to clear alarms: %s", e)

    def close(self) -> None:
        """关闭数据库连接。"""
        try:
            self.conn.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error("Error closing database: %s", e)
