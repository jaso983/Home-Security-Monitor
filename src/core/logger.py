import os
import logging
from typing import Optional


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    初始化全局日志系统。

    Args:
        level: 日志级别（DEBUG/INFO/WARNING/ERROR）。
        log_file: 日志文件路径，None 则仅输出到控制台。
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    handlers = [
        logging.StreamHandler(),
    ]

    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        handlers.append(
            logging.FileHandler(log_file, encoding="utf-8"),
        )

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )
