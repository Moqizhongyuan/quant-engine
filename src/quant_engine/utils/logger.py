"""
日志模块

提供统一的日志配置和获取接口。
"""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger


def setup_logger(
    level: str = "INFO",
    log_path: Optional[str] = None,
    rotation: str = "10 MB",
    retention: str = "30 days",
    log_format: Optional[str] = None,
) -> None:
    """
    配置日志系统。

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_path: 日志文件路径，None 则只输出到控制台
        rotation: 日志轮转大小
        retention: 日志保留时间
        log_format: 日志格式
    """
    logger.remove()

    default_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    fmt = log_format or default_format

    logger.add(
        sys.stderr,
        format=fmt,
        level=level,
        colorize=True,
    )

    if log_path:
        log_file = Path(log_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_path,
            format=fmt.replace("<green>", "")
            .replace("</green>", "")
            .replace("<level>", "")
            .replace("</level>", "")
            .replace("<cyan>", "")
            .replace("</cyan>", ""),
            level=level,
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
        )


def get_logger(name: str) -> "logger":
    """
    获取带有模块名称的 logger。

    Args:
        name: 模块名称

    Returns:
        配置好的 logger 实例
    """
    return logger.bind(name=name)
