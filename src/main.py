import cv2
from datetime import datetime
import time

def check_time_in_range(start_time_str, end_time_str):
    """判断当前时间是否在监控时间段内，比如 '23:00' 到 '06:00' """
    now = datetime.now().time()
    start_time = datetime.strptime(start_time_str, "%H:%M").time()
    end_time = datetime.strptime(end_time_str, "%H:%M").time()
    
    if start_time <= end_time:
        return start_time <= now <= end_time
    else: # 跨夜情况，比如 23:00 到 06:00
        return now >= start_time or now <= end_time

def main():
    print("系统启动：初始化摄像头...")
    # 0 代表电脑自带的摄像头。如果没有，可以换成一段本地测试视频的路径，如 'datasets/test_video.mp4'
    cap = cv2.VideoCapture(0) 
    
    if not cap.isOpened():
        print("错误：无法打开摄像头")
        return

    print("开始监控... 按 'q' 键退出系统")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 获取当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 1. 在画面上显示当前时间
        cv2.putText(frame, current_time, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # 2. 判断是否处于“陌生人入侵”的监控时段 (例如 23:00 - 06:00)
        is_monitor_time = check_time_in_range("23:00", "06:00")
        if is_monitor_time:
            cv2.putText(frame, "Security Mode: ON", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # --- 这里预留给同学B的 AI 检测代码 ---
            # detected_person = detect_person_with_yolo(frame)
            # if detected_person:
            #     trigger_alarm("检测到异常闯入！")
            # -------------------------------------
        else:
            cv2.putText(frame, "Security Mode: OFF", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

        # 3. 预留给火焰检测的代码（火焰是全天候24小时监控的，不受时间段限制）
        # has_fire = detect_fire_with_yolo(frame)
        # if has_fire:
        #     trigger_alarm("检测到火灾！")

        # 4. 显示画面 (预留给同学C的 GUI 接入点)
        cv2.imshow("Home Security Monitor", frame)

        # 按 'q' 键退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()