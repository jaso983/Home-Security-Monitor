import cv2
import os
from datetime import datetime

from models.yolo_detector import YoloDetector
from core.alarm_manager import AlarmManager
from core.db_manager import DatabaseManager


def check_time_in_range(start_time_str, end_time_str):
    now = datetime.now().time()
    start_time = datetime.strptime(start_time_str, "%H:%M").time()
    end_time = datetime.strptime(end_time_str, "%H:%M").time()
    if start_time <= end_time:
        return start_time <= now <= end_time
    else:
        return now >= start_time or now <= end_time


def main():
    print("初始化系统组件...")

    # 初始化截图保存目录
    screenshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
    os.makedirs(screenshot_dir, exist_ok=True)

    detector = YoloDetector()
    alarm_mgr = AlarmManager(cooldown=10)
    db = DatabaseManager()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("错误：无法打开摄像头")
        return

    print("监控系统已启动！")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            is_monitor_time = check_time_in_range("23:00", "06:00")

            display_frame = frame.copy()
            has_person = False
            if is_monitor_time:
                has_person, person_frame = detector.detect_person(frame)
                display_frame = person_frame
                cv2.putText(display_frame, "Night Security: ON", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                if has_person and alarm_mgr.should_trigger_alarm("person"):
                    timestamp = datetime.now()
                    filename = f"person_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
                    filepath = os.path.join(screenshot_dir, filename)
                    cv2.imwrite(filepath, frame)
                    db.insert_alarm("person", filepath)
                    print(f"\n[!!! 警报 !!!] {timestamp.strftime('%H:%M:%S')} 检测到陌生人闯入！截图已保存: {filepath}")
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
                    print(f"\n[!!! 紧急警报 !!!] {timestamp.strftime('%H:%M:%S')} 检测到火焰/烟雾！截图已保存: {filepath}")

            cv2.imshow("Home Security Camera", display_frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        db.close()
        print("系统已安全退出。")


if __name__ == "__main__":
    main()
