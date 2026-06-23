import time
from typing import Dict


class AlarmManager:
    """报警防抖管理器，在冷却期内抑制同类型重复报警。"""

    def __init__(self, cooldown_seconds: float = 10) -> None:
        """
        初始化报警管理器。

        Args:
            cooldown_seconds: 冷却时间（秒），在冷却时间内重复检测到同一事件视为同一次报警。
        """
        self.cooldown: float = cooldown_seconds
        self.last_alarm_time: Dict[str, float] = {"fire": 0.0, "person": 0.0}

    def should_trigger_alarm(self, event_type: str) -> bool:
        """
        判断是否应触发新报警（过滤冷却期内的重复报警）。

        Args:
            event_type: 报警类型，"fire" 或 "person"。

        Returns:
            True 表示触发新报警，False 表示冷却期内抑制。
        """
        current_time: float = time.time()
        time_since_last: float = current_time - self.last_alarm_time[event_type]

        if time_since_last > self.cooldown:
            self.last_alarm_time[event_type] = current_time
            return True
        return False
