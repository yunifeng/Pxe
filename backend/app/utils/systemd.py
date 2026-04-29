"""Systemd 服务控制工具"""
import subprocess

from app.exceptions import PxeException


def systemctl(action: str, service: str, timeout: int = 30) -> str:
    """执行 systemctl 命令

    Args:
        action: 操作 (start/stop/restart/status/enable/disable)
        service: 服务名称
        timeout: 超时秒数

    Returns:
        命令输出
    """
    allowed = {"start", "stop", "restart", "status", "enable", "disable"}
    if action not in allowed:
        raise PxeException("INVALID_ACTION", f"不支持的 systemctl 操作: {action}")
    try:
        result = subprocess.run(
            ["systemctl", action, service],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise PxeException(
            "SYSTEMCTL_ERROR",
            f"systemctl {action} {service} 失败: {e.stderr.strip()}",
        )
    except subprocess.TimeoutExpired:
        raise PxeException(
            "SYSTEMCTL_TIMEOUT",
            f"systemctl {action} {service} 超时 ({timeout}s)",
        )


def is_active(service: str) -> bool:
    """检查服务是否运行"""
    try:
        subprocess.run(
            ["systemctl", "is-active", service],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def get_service_status(service: str) -> str:
    """获取服务详细信息"""
    return systemctl("status", service)
