"""
日志配置模块
支持文件轮转和 stdout 输出
"""
import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler

from app.config import settings


def setup_logging(
    level: int = logging.INFO,
    enable_stdout: bool = True,
    enable_file: bool = True,
) -> logging.Logger:
    """
    配置 Python 日志系统

    Args:
        level: 日志级别 (默认 INFO)
        enable_stdout: 是否输出到 stdout (开发模式)
        enable_file: 是否输出到文件 (生产模式)

    Returns:
        配置好的根日志记录器
    """
    logger = logging.getLogger("pxe")
    logger.setLevel(level)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # stdout 处理器 (开发模式)
    if enable_stdout:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 文件处理器 (生产模式)
    if enable_file:
        try:
            log_dir = settings.log_dir
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "pxe.log")
            file_handler = TimedRotatingFileHandler(
                filename=log_file,
                when="midnight",
                interval=1,
                backupCount=30,
                encoding="utf-8",
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            file_handler.suffix = "%Y-%m-%d.log"
            logger.addHandler(file_handler)
        except PermissionError:
            pass

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取子模块日志记录器

    Args:
        name: 子模块名称

    Returns:
        子模块日志记录器
    """
    return logging.getLogger(f"pxe.{name}")
