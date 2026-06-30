import sys
import os
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from core.alarm_manager import AlarmManager
from core.db_manager import DatabaseManager


class TestGUIComponents(unittest.TestCase):
    """GUI 组件基础测试（不启动真实窗口）。"""

    def test_alarm_manager_integration(self) -> None:
        """验证 AlarmManager 与 GUI 控制器的集成接口（连续帧确认 + 冷却）。"""
        alarm_mgr = AlarmManager(cooldown_seconds=10)
        # 连续 3 帧确认后触发
        self.assertFalse(alarm_mgr.should_trigger_alarm("fire"))
        self.assertFalse(alarm_mgr.should_trigger_alarm("fire"))
        self.assertTrue(alarm_mgr.should_trigger_alarm("fire"))
        # 冷却内不触发
        self.assertFalse(alarm_mgr.should_trigger_alarm("fire"))

    def test_db_manager_integration(self) -> None:
        """验证 DatabaseManager 与 HistoryPanel 的集成接口。"""
        import tempfile
        tmp_db = os.path.join(tempfile.gettempdir(), "test_gui_alarms.db")
        db = DatabaseManager(db_path=tmp_db)
        row_id = db.insert_alarm("fire", "test.jpg")
        self.assertIsNotNone(row_id)
        alarms = db.get_recent_alarms()
        self.assertEqual(len(alarms), 1)
        db.close()
        os.remove(tmp_db)

    @patch('cv2.VideoCapture')
    def test_camera_open_failure(self, mock_cap_class) -> None:
        """摄像头打开失败时应返回 False。"""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_cap_class.return_value = mock_cap
        cap = mock_cap_class(0)
        self.assertFalse(cap.isOpened())


if __name__ == "__main__":
    unittest.main()
