"""SSH 远程执行 (paramiko)"""
import paramiko

from app.config import settings
from app.exceptions import PxeException

_ssh_pool = {}


def connect(host: str, port: int = 22, key_path: str = None) -> paramiko.SSHClient:
    """SSH 连接"""
    if host in _ssh_pool:
        client = _ssh_pool[host]
        if client.get_transport() and client.get_transport().is_active():
            return client
    key = key_path or settings.ssh_key_path
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, port=port, key_filename=key, timeout=30, allow_agent=False)
    except Exception as e:
        raise PxeException("SSH_CONNECT_ERROR", f"连接 {host}:{port} 失败: {e}")
    _ssh_pool[host] = client
    return client


def exec_command(host: str, command: str, port: int = 22, timeout: int = 30) -> dict:
    """执行远程命令"""
    client = connect(host, port)
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        return {
            "stdout": stdout.read().decode("utf-8"),
            "stderr": stderr.read().decode("utf-8"),
            "exit_code": stdout.channel.recv_exit_status(),
        }
    except paramiko.SSHException as e:
        raise PxeException("SSH_EXEC_ERROR", f"命令执行失败: {e}")


def exec_batch(hosts: list, command: str) -> dict:
    """批量执行命令

    Returns:
        {host: {"stdout": ..., "stderr": ..., "exit_code": ...}}
    """
    results = {}
    for host in hosts:
        try:
            results[host] = exec_command(host, command)
        except PxeException as e:
            results[host] = {"stdout": "", "stderr": e.message, "exit_code": -1}
    return results


def close(host: str) -> None:
    """关闭 SSH 连接池中的连接"""
    if host in _ssh_pool:
        try:
            _ssh_pool[host].close()
        except Exception:
            pass
        del _ssh_pool[host]
