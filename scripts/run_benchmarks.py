"""
Run real performance benchmarks for documentation.
Measures: AlarmManager latency, DB throughput, DB query, YOLO FPS, frame resize.
"""
import os
import sys
import time
import tempfile

import cv2
import numpy as np

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT)

from src.core.alarm_manager import AlarmManager
from src.core.db_manager import DatabaseManager


def bench_alarm_manager():
    """Measure AlarmManager.update() latency."""
    mgr = AlarmManager(cooldown_seconds=10, iou_threshold=0.2, track_max_age=90)
    person_boxes = [{"bbox": [100, 100, 200, 300], "confidence": 0.85}]
    identity_results = [{"bbox": [100, 100, 200, 300], "identity": "stranger"}]

    # Warm up
    for _ in range(100):
        mgr.update(person_boxes, identity_results, is_night=True)
    mgr.reset_tracks()

    # Benchmark
    N = 1000
    t0 = time.perf_counter()
    for _ in range(N):
        mgr.update(person_boxes, identity_results, is_night=True)
    elapsed = time.perf_counter() - t0
    per_call_ms = (elapsed / N) * 1000

    print(f"AlarmManager.update() latency: {per_call_ms:.3f} ms/call ({N} iterations)")
    return per_call_ms


def bench_db_insert():
    """Measure DB insert throughput."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        db = DatabaseManager(db_path=db_path)
        N = 1000
        t0 = time.perf_counter()
        for i in range(N):
            db.insert_alarm(event_type="fire", image_path=f"screenshots/test_{i}.jpg")
        elapsed = time.perf_counter() - t0
        tps = N / elapsed
        print(f"DB insert throughput: {tps:.1f} TPS ({N} inserts in {elapsed:.3f}s)")
        db.close()
        return tps
    finally:
        os.unlink(db_path)


def bench_db_query():
    """Measure DB query latency."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        db = DatabaseManager(db_path=db_path)
        # Insert 100 records
        for i in range(100):
            db.insert_alarm(event_type="fire" if i % 2 == 0 else "person",
                            image_path=f"screenshots/test_{i}.jpg")

        # Benchmark recent query
        N = 100
        t0 = time.perf_counter()
        for _ in range(N):
            db.get_recent_alarms(limit=50)
        elapsed = time.perf_counter() - t0
        per_query_ms = (elapsed / N) * 1000
        print(f"DB query latency (100 records): {per_query_ms:.3f} ms/query")

        # Benchmark by type
        t0 = time.perf_counter()
        for _ in range(N):
            db.get_alarms_by_type(event_type="fire", limit=50)
        elapsed2 = time.perf_counter() - t0
        per_type_ms = (elapsed2 / N) * 1000
        print(f"DB query-by-type latency: {per_type_ms:.3f} ms/query")
        db.close()
        return per_query_ms
    finally:
        os.unlink(db_path)


def bench_yolo_inference():
    """Measure YOLO inference speed."""
    try:
        from src.models.yolo_detector import YoloDetector
        detector = YoloDetector()

        # Create synthetic frame
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Warm up
        for _ in range(3):
            detector.detect_person(frame)

        # Benchmark person detection
        N = 30
        t0 = time.perf_counter()
        for _ in range(N):
            detector.detect_person(frame)
        elapsed = time.perf_counter() - t0
        fps = N / elapsed
        ms_per_frame = (elapsed / N) * 1000
        print(f"Person detection: {fps:.1f} FPS ({ms_per_frame:.1f} ms/frame)")

        # Benchmark fire detection
        t0 = time.perf_counter()
        for _ in range(N):
            detector.detect_fire(frame)
        elapsed = time.perf_counter() - t0
        fps_fire = N / elapsed
        ms_fire = (elapsed / N) * 1000
        print(f"Fire detection: {fps_fire:.1f} FPS ({ms_fire:.1f} ms/frame)")

        # Combined
        total_ms = ms_per_frame + ms_fire
        combined_fps = 1000 / total_ms
        print(f"Combined (person+fire): {combined_fps:.1f} FPS ({total_ms:.1f} ms/frame)")
        return combined_fps
    except Exception as e:
        print(f"YOLO benchmark failed: {e}")
        return None


def bench_frame_resize():
    """Measure frame resize performance."""
    frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
    target = (640, 480)

    N = 100
    t0 = time.perf_counter()
    for _ in range(N):
        _ = cv2.resize(frame, target)
    elapsed = time.perf_counter() - t0
    per_ms = (elapsed / N) * 1000
    print(f"Frame resize (1920x1080 -> 640x480): {per_ms:.3f} ms/frame")
    return per_ms


if __name__ == "__main__":
    print("=" * 60)
    print("Home Security Monitor - Performance Benchmarks")
    print("=" * 60)
    print()

    print("[1/5] AlarmManager latency")
    alarm_ms = bench_alarm_manager()
    print()

    print("[2/5] DB insert throughput")
    db_tps = bench_db_insert()
    print()

    print("[3/5] DB query latency")
    db_q_ms = bench_db_query()
    print()

    print("[4/5] YOLO inference speed")
    yolo_fps = bench_yolo_inference()
    print()

    print("[5/5] Frame resize")
    resize_ms = bench_frame_resize()
    print()

    print("=" * 60)
    print("SUMMARY (for documentation)")
    print("=" * 60)
    print(f"AlarmManager.update(): {alarm_ms:.3f} ms")
    print(f"DB insert: {db_tps:.0f} TPS")
    print(f"DB query (100 records): {db_q_ms:.3f} ms")
    if yolo_fps:
        print(f"YOLO combined: {yolo_fps:.1f} FPS")
    print(f"Frame resize: {resize_ms:.3f} ms")
