# src/core/alarm_manager.py
#报警防抖机制
import time

class AlarmManager:
    def __init__(self, cooldown_seconds=10):
        """
        :param cooldown_seconds: 冷却时间（秒）。在冷却时间内重复检测到同一事件，视为同一次报警。
        """
        self.cooldown = cooldown_seconds
        # 记录每种报警类型最后一次触发的时间戳
        self.last_alarm_time = {
            "fire": 0.0,
            "person": 0.0
        }

    def should_trigger_alarm(self, event_type):
        """
        判断是否应该触发新报警（过滤重复报警）
        :param event_type: "fire" 或 "person"
        :return: True (触发新报警) / False (忽略，视为重复报警合并)
        """
        current_time = time.time()
        time_since_last = current_time - self.last_alarm_time[event_type]

        if time_since_last > self.cooldown:
            # 距离上次报警已经超过了冷却时间，说明是“新事件”，允许报警
            self.last_alarm_time[event_type] = current_time
            return True
        else:
            # 距离上次报警很近，说明是“同一个事件”，过滤掉，只更新时间戳（延长报警状态）
            self.last_alarm_time[event_type] = current_time 
            return False