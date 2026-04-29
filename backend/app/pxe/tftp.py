"""TFTP 服务管理"""
import os
import subprocess
from pathlib import Path

from app.config import settings
from app.exceptions import PxeException
from app.utils.systemd import is_active


def setup_tftp(root_dir: str = "") -> dict:
    """初始化 TFTP 根目录结构

    Args:
        root_dir: TFTP 根目录，默认使用配置值

    Returns:
        创建的目录结构信息
    """
    base = root_dir or settings.tftp_root
    dirs = {
        "tftp_root": base,
        "ipxe": os.path.join(base, "ipxe"),
        "pxelinux.cfg": os.path.join(base, "pxelinux.cfg"),
        "images": os.path.join(base, "images"),
    }
    for path in dirs.values():
        os.makedirs(path, exist_ok=True)
    return dirs


def get_status() -> dict:
    """检查 TFTP 服务状态"""
    return {
        "running": is_active("tftp-hpa"),
        "root": settings.tftp_root,
    }


def start() -> None:
    """启动 TFTP 服务"""
    try:
        subprocess.run(
            ["systemctl", "start", "tftp-hpa"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as e:
        raise PxeException("TFTP_START_ERROR", f"启动 TFTP 失败: {e.stderr.strip()}")


def stop() -> None:
    """停止 TFTP 服务"""
    try:
        subprocess.run(
            ["systemctl", "stop", "tftp-hpa"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as e:
        raise PxeException("TFTP_STOP_ERROR", f"停止 TFTP 失败: {e.stderr.strip()}")


def restart() -> None:
    """重启 TFTP 服务"""
    try:
        subprocess.run(
            ["systemctl", "restart", "tftp-hpa"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as e:
        raise PxeException("TFTP_RESTART_ERROR", f"重启 TFTP 失败: {e.stderr.strip()}")


def list_files(path: str = "") -> list:
    """列出 TFTP 目录文件"""
    target = os.path.join(settings.tftp_root, path)
    if not os.path.isdir(target):
        raise PxeException("DIRECTORY_NOT_FOUND", f"TFTP 目录不存在: {target}")
    items = []
    for entry in os.listdir(target):
        full = os.path.join(target, entry)
        items.append({
            "name": entry,
            "is_dir": os.path.isdir(full),
            "size": os.path.getsize(full) if os.path.isfile(full) else 0,
        })
    return items
