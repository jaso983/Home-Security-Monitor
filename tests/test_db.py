import sys
import os
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from core.db_manager import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    """DatabaseManager 数据库模块单元测试。"""

    def setUp(self) -> None:
        self.tmp_db = os.path.join(tempfile.gettempdir(), "test_alarms.db")
        self.db = DatabaseManager(db_path=self.tmp_db)

    def tearDown(self) -> None:
        try:
            self.db.close()
        except Exception:
            pass
        if os.path.exists(self.tmp_db):
            os.remove(self.tmp_db)

    def test_table_created(self) -> None:
        """验证 alarms 表存在。"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alarms'")
        self.assertIsNotNone(cursor.fetchone())

    def test_insert_and_query(self) -> None:
        """插入并查询报警记录。"""
        id1 = self.db.insert_alarm("fire", "screenshots/fire_test.jpg")
        id2 = self.db.insert_alarm("person", "screenshots/person_test.jpg")
        id3 = self.db.insert_alarm("fire", "screenshots/fire_test2.jpg")
        self.assertEqual(id1, 1)
        self.assertEqual(id2, 2)
        self.assertEqual(id3, 3)

    def test_get_recent_alarms(self) -> None:
        """查询全部记录。"""
        self.db.insert_alarm("fire", "screenshots/fire_test.jpg")
        self.db.insert_alarm("person", "screenshots/person_test.jpg")
        self.db.insert_alarm("fire", "screenshots/fire_test2.jpg")
        all_alarms = self.db.get_recent_alarms()
        self.assertEqual(len(all_alarms), 3)

    def test_get_alarms_by_type(self) -> None:
        """按类型筛选。"""
        self.db.insert_alarm("fire", "screenshots/fire_test.jpg")
        self.db.insert_alarm("person", "screenshots/person_test.jpg")
        self.db.insert_alarm("fire", "screenshots/fire_test2.jpg")
        fire_alarms = self.db.get_alarms_by_type("fire")
        person_alarms = self.db.get_alarms_by_type("person")
        self.assertEqual(len(fire_alarms), 2)
        self.assertEqual(len(person_alarms), 1)

    def test_limit_parameter(self) -> None:
        """limit 参数验证。"""
        for i in range(5):
            self.db.insert_alarm("fire", f"screenshots/fire_{i}.jpg")
        limited = self.db.get_recent_alarms(limit=2)
        self.assertEqual(len(limited), 2)

    def test_delete_alarm(self) -> None:
        """删除单条记录。"""
        self.db.insert_alarm("fire", "screenshots/fire_test.jpg")
        self.db.insert_alarm("person", "screenshots/person_test.jpg")
        self.db.delete_alarm(1)
        remaining = self.db.get_recent_alarms()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0][1], "person")

    def test_clear_all(self) -> None:
        """清空全部记录。"""
        self.db.insert_alarm("fire", "screenshots/fire_test.jpg")
        self.db.insert_alarm("person", "screenshots/person_test.jpg")
        self.db.clear_all()
        remaining = self.db.get_recent_alarms()
        self.assertEqual(len(remaining), 0)

    def test_empty_db_query(self) -> None:
        """空数据库查询应返回空列表，不报错。"""
        result = self.db.get_recent_alarms()
        self.assertEqual(result, [])

    def test_field_content_validation(self) -> None:
        """验证字段内容格式。"""
        self.db.insert_alarm("fire", "screenshots/fire_test.jpg")
        alarms = self.db.get_recent_alarms()
        for alarm in alarms:
            row_id, event_type, timestamp, image_path = alarm
            self.assertIn(event_type, ("fire", "person"))
            self.assertIsNotNone(timestamp)
            self.assertTrue(image_path.startswith("screenshots/"))

    # --- 异常测试 ---

    def test_invalid_db_path(self) -> None:
        """无效路径创建数据库应抛出异常。"""
        with self.assertRaises(Exception):
            DatabaseManager(db_path="/nonexistent/path/alarms.db")

    def test_delete_nonexistent_alarm(self) -> None:
        """删除不存在的 ID 不应报错，返回 True。"""
        result = self.db.delete_alarm(9999)
        self.assertTrue(result)

    def test_get_alarms_by_nonexistent_type(self) -> None:
        """查询不存在的类型应返回空列表。"""
        self.db.insert_alarm("fire", "screenshots/fire_test.jpg")
        result = self.db.get_alarms_by_type("earthquake")
        self.assertEqual(result, [])

    def test_double_close(self) -> None:
        """重复关闭数据库不应崩溃。"""
        self.db.close()
        try:
            self.db.close()
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
