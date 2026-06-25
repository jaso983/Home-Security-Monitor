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

    screenshot_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)

    detector = YoloDetector(config=cfg.config)
    alarm_mgr = AlarmManager(
        cooldown_seconds=cfg.get("alarm", "cooldown_seconds", 10),
        iou_threshold=cfg.get("alarm", "iou_threshold", 0.2),
        track_max_age=cfg.get("alarm", "track_max_age", 90),
        no_face_delay_seconds=cfg.get("alarm", "no_face_delay_seconds", 10),
        no_face_night_delay_seconds=cfg.get("alarm", "no_face_night_delay_seconds", 3),
        person_alarm_gap=cfg.get("alarm", "person_alarm_gap", 5.0),
        fire_stable_frames=cfg.get("alarm", "fire_stable_frames", 3),
        smoke_stable_frames=cfg.get("alarm", "smoke_stable_frames", 5),
        person_stable_frames=cfg.get("alarm", "person_stable_frames", 3),
    )
    db = DatabaseManager()
    face_recognizer = FaceRecognizer(
        faces_dir=cfg.get("recognition", "faces_dir", ""),
        tolerance=cfg.get("recognition", "tolerance", 0.68),
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
                cfg.get("monitor", "person_start", "00:00"),
                cfg.get("monitor", "person_end", "23:59"),
            )

            display_frame = frame.copy()
            pending_person_alarms: list = []
            pending_fire_alarm = False

            if is_monitor_time:
                person_boxes, person_frame = detector.detect_person(frame)
                display_frame = person_frame

                if person_boxes:
                    # 只对需要人脸识别的人员框执行 DeepFace
                    boxes_to_identify = alarm_mgr.get_boxes_needing_face_check(person_boxes)

                    identity_results: list = []
                    if boxes_to_identify:
                        identity_results = face_recognizer.identify_faces(frame, boxes_to_identify)
                    # 所有人员框都参与 track 匹配，未识别的保持原身份
                    pending_person_alarms = alarm_mgr.update(person_boxes, identity_results, is_monitor_time)

                    # 在 display_frame 上绘制身份标签（保存截图前标注）
                    for ti in alarm_mgr.get_display_identities():
                        x1, y1, x2, y2 = [int(v) for v in ti["bbox"]]
                        identity = ti["identity"]
                        if identity.startswith("member:"):
                            label = f"[OK] {identity.split(':')[1]}"
                            color = (0, 200, 0)
                        elif identity == "stranger":
                            label = "[ALERT] STRANGER"
                            color = (0, 0, 255)
                        elif identity == "no_face":
                            label = "[ALERT] NO FACE"
                            color = (0, 200, 255)
                        else:
                            label = "..."
                            color = (180, 180, 180)
                        cv2.putText(display_frame, label, (x1, y1 - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                if is_monitor_time:
                    cv2.putText(display_frame, "Night Security: ON", (10, 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            else:
                cv2.putText(display_frame, "Night Security: OFF", (10, 55),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.putText(display_frame, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # 火焰检测
            fire_dets, fire_frame = detector.detect_fire(display_frame)
            has_fire = len(fire_dets) > 0
            if has_fire:
                display_frame = fire_frame
                if alarm_mgr.should_trigger_fire_alarm({d["class_id"] for d in fire_dets}):
                    pending_fire_alarm = True

            # 报警保存（标注完成后）
            for alarm in pending_person_alarms:
                timestamp = datetime.now()
                filename = f"person_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
                filepath = os.path.join(screenshot_dir, filename)
                cv2.imwrite(filepath, display_frame)
                db.insert_alarm("person", filepath)
                logger.warning("ALARM [person/%s] at %s, screenshot: %s",
                               alarm.get("reason", "unknown"),
                               timestamp.strftime("%H:%M:%S"), filepath)

            if pending_fire_alarm:
                timestamp = datetime.now()
                filename = f"fire_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
                filepath = os.path.join(screenshot_dir, filename)
                cv2.imwrite(filepath, display_frame)
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
