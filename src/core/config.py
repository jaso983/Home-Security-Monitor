import os
import logging
from typing import Any, Dict, Optional

import yaml


class ConfigReader:
    """配置文件读取器，从 config.yaml 加载系统参数。"""

    _DEFAULT_CONFIG: Dict[str, Any] = {
        "monitor": {"person_start": "00:00", "person_end": "23:59"},
        "alarm": {"cooldown_seconds": 10},
        "detection": {"person_conf": 0.8, "person_classes": [0], "fire_conf": 0.8, "fire_classes": [0, 1], "fire_model_path": ""},
        "camera": {"device_id": 0, "width": 640, "height": 480},
        "recognition": {"faces_dir": "src/models/family_faces", "tolerance": 80.0},
        "gui": {"loop_delay_ms": 30, "fps_interval": 1.0, "min_width": 1024, "min_height": 700},
        "logging": {"level": "INFO", "file": "security_monitor.log"},
    }

    def __init__(self, config_path: Optional[str] = None) -> None:
        """
        初始化配置读取器。

        Args:
            config_path: 配置文件路径，默认为项目根目录下 config.yaml。
        """
        if config_path is None:
            project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(project_dir, "config.yaml")

        self._config: Dict[str, Any] = self._DEFAULT_CONFIG.copy()

        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    self._merge(self._config, user_config)
            logging.getLogger(__name__).info("Config loaded from %s", config_path)
        else:
            logging.getLogger(__name__).warning("Config file not found: %s, using defaults", config_path)

    def _merge(self, base: Dict, override: Dict) -> None:
        """递归合并字典，override 覆盖 base 中的同名键。"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge(base[key], value)
            else:
                base[key] = value

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        获取配置项。

        Args:
            section: 配置节名（如 "monitor"、"alarm"）。
            key: 配置键名。
            default: 键不存在时的默认值。

        Returns:
            配置值。
        """
        return self._config.get(section, {}).get(key, default)

    @property
    def config(self) -> Dict[str, Any]:
        """返回完整配置字典。"""
        return self._config
