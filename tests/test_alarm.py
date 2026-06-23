import sys
import os
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from core.alarm_manager import AlarmManager


class TestAlarmManager(unittest.TestCase):
    """AlarmManager 报警防抖模块单元测试。"""

    def setUp(self) -> None:
        self.alarm_mgr = AlarmManager(cooldown_seconds=1)

    def test_first_alarm_triggers(self) -> None:
        """首次报警应触发。"""
        self.assertTrue(self.alarm_mgr.should_trigger_alarm("fire"))
        self.assertTrue(self.alarm_mgr.should_trigger_alarm("person"))

    def test_cooldown_suppresses_repeat(self) -> None:
        """冷却期内重复报警应被抑制。"""
        self.alarm_mgr.should_trigger_alarm("fire")
        self.assertFalse(self.alarm_mgr.should_trigger_alarm("fire"))

    def test_cooldown_expires_allows_new(self) -> None:
        """冷却期后应允许新报警。"""
        self.alarm_mgr.should_trigger_alarm("fire")
        time.sleep(1.1)
        self.assertTrue(self.alarm_mgr.should_trigger_alarm("fire"))

    def test_different_types_independent(self) -> None:
        """不同报警类型的冷却计时器应独立。"""
        self.assertTrue(self.alarm_mgr.should_trigger_alarm("fire"))
        self.assertTrue(self.alarm_mgr.should_trigger_alarm("person"))

    def test_same_type_within_cooldown(self) -> None:
        """冷却期内同一类型多次触发，均返回 False。"""
        self.alarm_mgr.should_trigger_alarm("fire")
        self.assertFalse(self.alarm_mgr.should_trigger_alarm("fire"))
        self.assertFalse(self.alarm_mgr.should_trigger_alarm("fire"))

    def test_custom_cooldown(self) -> None:
        """自定义冷却时间应生效。"""
        mgr = AlarmManager(cooldown_seconds=0.2)
        mgr.should_trigger_alarm("person")
        time.sleep(0.3)
        self.assertTrue(mgr.should_trigger_alarm("person"))

    def test_invalid_event_type_raises(self) -> None:
        """无效事件类型应抛出 KeyError。"""
        with self.assertRaises(KeyError):
            self.alarm_mgr.should_trigger_alarm("unknown")

    def test_cooldown_not_reset_on_suppress(self) -> None:
        """冷却期内重复检测不应重置计时器，冷却期后应能再次触发。"""
        mgr = AlarmManager(cooldown_seconds=1)
        self.assertTrue(mgr.should_trigger_alarm("fire"))
        # 冷却期内多次检测，不应重置计时器
        time.sleep(0.4)
        self.assertFalse(mgr.should_trigger_alarm("fire"))
        time.sleep(0.4)
        self.assertFalse(mgr.should_trigger_alarm("fire"))
        # 总共0.8秒，还没过1秒冷却期
        self.assertFalse(mgr.should_trigger_alarm("fire"))
        # 再等0.3秒，总共1.1秒，超过冷却期
        time.sleep(0.3)
        self.assertTrue(mgr.should_trigger_alarm("fire"))


if __name__ == "__main__":
    unittest.main()
