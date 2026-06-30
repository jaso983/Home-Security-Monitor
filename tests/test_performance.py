import sys
import os
import time
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from core.alarm_manager import AlarmManager
from core.db_manager import DatabaseManager
import tempfile


class TestPerformance(unittest.TestCase):
    """性能基准测试。"""

    def test_alarm_manager_latency(self) -> None:
        """AlarmManager 判定延迟应低于 1ms。"""
        mgr = AlarmManager(cooldown_seconds=10)
        start = time.perf_counter()
        for _ in range(1000):
            mgr.should_trigger_alarm("fire")
        elapsed = time.perf_counter() - start
        avg_ms = elapsed / 1000 * 1000
        self.assertLess(avg_ms, 1.0, f"Average latency {avg_ms:.3f}ms exceeds 1ms")
        print(f"[PERF] AlarmManager average latency: {avg_ms:.4f}ms")

    def test_db_insert_throughput(self) -> None:
        """数据库插入吞吐量应大于 100 条/秒。"""
        tmp_db = os.path.join(tempfile.gettempdir(), "test_perf_alarms.db")
        db = DatabaseManager(db_path=tmp_db)
        count = 500
        start = time.perf_counter()
        for i in range(count):
            db.insert_alarm("fire", f"screenshots/fire_{i}.jpg")
        elapsed = time.perf_counter() - start
        db.close()
        os.remove(tmp_db)
        tps = count / elapsed
        self.assertGreater(tps, 100, f"Insert throughput {tps:.0f} TPS below 100 TPS")
        print(f"[PERF] DB insert throughput: {tps:.0f} TPS")

    def test_db_query_latency(self) -> None:
        """数据库查询 100 条记录应低于 10ms。"""
        tmp_db = os.path.join(tempfile.gettempdir(), "test_perf_query.db")
        db = DatabaseManager(db_path=tmp_db)
        for i in range(100):
            db.insert_alarm("fire", f"screenshots/fire_{i}.jpg")
        start = time.perf_counter()
        alarms = db.get_recent_alarms(limit=100)
        elapsed = (time.perf_counter() - start) * 1000
        db.close()
        os.remove(tmp_db)
        self.assertEqual(len(alarms), 100)
        self.assertLess(elapsed, 10.0, f"Query latency {elapsed:.2f}ms exceeds 10ms")
        print(f"[PERF] DB query 100 records latency: {elapsed:.2f}ms")

    def test_frame_resize_performance(self) -> None:
        """帧缩放（640x480）应低于 5ms。"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        import cv2
        start = time.perf_counter()
        for _ in range(100):
            cv2.resize(frame, (640, 480))
        elapsed = (time.perf_counter() - start) / 100 * 1000
        self.assertLess(elapsed, 5.0, f"Frame resize latency {elapsed:.2f}ms exceeds 5ms")
        print(f"[PERF] Frame resize average latency: {elapsed:.2f}ms")


if __name__ == "__main__":
    unittest.main()
