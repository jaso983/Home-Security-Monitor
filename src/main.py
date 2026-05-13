import cv2
from datetime import datetime
import time

# 引入我们自己写的模块
from models.yolo_detector import YoloDetector
# 如果你之前没有写 alarm_manager.py，请先在当前目录下创建一个空的，或者把下面的逻辑先简单替换掉

class AlarmManager:
    def __init__(self, cooldown=10):
        self.cooldown = cooldown
        self.last_time = {"person": 0, "fire": 0}

    def should_trigger(self, event_type):
        current = time.time()
        if current - self.last_time[event_type] > self.cooldown:
            self.last_time[event_type] = current
            return True
        return False

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
    detector = YoloDetector()          # 初始化 AI 模型
    alarm_mgr = AlarmManager(cooldown=5) # 报警冷却时间设为5秒（测试用）
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("错误：无法打开摄像头")
        return

    print("监控系统已启动！")

    while True:
        ret, frame = cap.read()
        if not ret: break

        # 1. 拿到当前时间，判断是否在设防时间 (为了测试，你现在可以先改成 "00:00" 到 "23:59")
        is_monitor_time = check_time_in_range("00:00", "23:59")

        display_frame = frame.copy()
        has_person = False
        if is_monitor_time:
            # 2. 如果在设防时间，调用 AI 进行人员检测！
            has_person, person_frame = detector.detect_person(frame)
            display_frame = person_frame
            cv2.putText(display_frame, "Night Security: ON", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            # 3. 触发报警与防抖过滤逻辑
            if has_person:
                if alarm_mgr.should_trigger("person"):
                    print(f"\n[!!! 警报 !!!] {datetime.now().strftime('%H:%M:%S')} 检测到陌生人闯入！")
                    # 这里以后可以加上：保存截图、写入数据库的操作
        else:
            cv2.putText(display_frame, "Night Security: OFF", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # 在画面左上角打上时间戳
        cv2.putText(display_frame, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # 24小时全天候火焰检测 - 在原始frame上检测
        has_fire, fire_frame = detector.detect_fire(frame)
        if has_fire:
            # 将火焰框叠加到显示frame上
            display_frame = fire_frame
            if alarm_mgr.should_trigger("fire"): # 记得给 AlarmManager 的字典里加上 "fire"
                print(f"\n[!!! 紧急警报 !!!] {datetime.now().strftime('%H:%M:%S')} 检测到火焰/烟雾！")

        # 4. 显示最终画面
        cv2.imshow("Home Security Camera", display_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()