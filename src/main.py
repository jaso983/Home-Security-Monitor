import cv2
import os
import logging
from datetime import datetime

from models.yolo_detector import YoloDetector
from core.alarm_manager import AlarmManager
from core.db_manager import DatabaseManager
from core.face_recognizer import FaceRecognizer
from core.config import ConfigReader
from core.logger import setup_logging

logger = logging.getLogger(__name__)


def check_time_in_range(start_time_str: str, end_time_str: str) -> bool:
    """
    检查当前时间是否在指定时段内（支持跨午夜时段）。

    Args:
        start_time_str: 开始时间，格式 "HH:MM"。
        end_time_str: 结束时间，格式 "HH:MM"。

    Returns:
        当前时间是否在时段内。
    """
    now = datetime.now().time()
    start_time = datetime.strptime(start_time_str, "%H:%M").time()
    end_time = datetime.strptime(end_time_str, "%H:%M").time()
    if start_time <= end_time:
        return start_time <= now <= end_time
    else:
        return now >= start_time or now <= end_time


def main() -> None:
    """CLI 模式主函数：启动 OpenCV 窗口进行安防监控。"""
    cfg = ConfigReader()
    setup_logging(
        level=cfg.get("logging", "level", "INFO"),
        log_file=cfg.get("logging", "file"),
    )

    logger.info("Initializing system components...")

    # 初始化截图保存目录
    screenshot_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)

    detector = YoloDetector(config=cfg.config)
    alarm_mgr = AlarmManager(cooldown=cfg.get("alarm", "cooldown_seconds", 10))
    db = DatabaseManager()
    face_recognizer = FaceRecognizer(
        faces_dir=cfg.get("recognition", "faces_dir", ""),
        tolerance=cfg.get("recognition", "tolerance", 80.0),
    )

    cap = cv2.VideoCapture(cfg.get("camera", "device_id", 0))
    if not cap.isOpened():
        logger.error("Cannot open camera")
        return

    logger.info("Security monitoring system started")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            is_monitor_time = check_time_in_range(
                cfg.get("monitor", "person_start", "23:00"),
                cfg.get("monitor", "person_end", "06:00"),
            )

            display_frame = frame.copy()
            has_person = False
            if is_monitor_time:
                has_person, person_frame = detector.detect_person(frame)
                display_frame = person_frame
                cv2.putText(display_frame, "Night Security: ON", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                if has_person:
                    is_stranger = face_recognizer.is_stranger(frame)
                    if is_stranger and alarm_mgr.should_trigger_alarm("person"):
                        timestamp = datetime.now()
                        filename = f"person_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
                        filepath = os.path.join(screenshot_dir, filename)
                        cv2.imwrite(filepath, frame)
                        db.insert_alarm("person", filepath)
                        logger.warning("ALARM [person/stranger] at %s, screenshot: %s",
                                       timestamp.strftime("%H:%M:%S"), filepath)
            else:
                cv2.putText(display_frame, "Night Security: OFF", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # 时间戳
            cv2.putText(display_frame, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            # 全天候火焰/烟雾检测
            has_fire, fire_frame = detector.detect_fire(frame)
            if has_fire:
                display_frame = fire_frame
                if alarm_mgr.should_trigger_alarm("fire"):
                    timestamp = datetime.now()
                    filename = f"fire_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
                    filepath = os.path.join(screenshot_dir, filename)
                    cv2.imwrite(filepath, frame)
                    db.insert_alarm("fire", filepath)
                    logger.warning("ALARM [fire] at %s, screenshot: %s",
                                   timestamp.strftime("%H:%M:%S"), filepath)

            cv2.imshow("Home Security Camera", display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        db.close()
        logger.info("System exited safely")


if __name__ == "__main__":
    main()
