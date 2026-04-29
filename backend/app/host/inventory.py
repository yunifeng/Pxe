"""硬件清单"""
import json

from app.exceptions import PxeException
from app.node.ssh import exec_command


def get_hardware_info(host_ip: str) -> dict:
    """收集硬件信息 (CPU, 内存, 磁盘, 网卡)"""
    try:
        cpu = exec_command(host_ip, "lscpu --json 2>/dev/null || lscpu")
        memory = exec_command(host_ip, "free -g")
        disks = exec_command(host_ip, "lsblk -b -o NAME,SIZE,TYPE,MOUNTPOINT -J 2>/dev/null || lsblk")
        nics = exec_command(host_ip, "ip -j link show 2>/dev/null || ip link show")
        return {
            "cpu": _parse_lscpu(cpu["stdout"]),
            "memory": _parse_memory(memory["stdout"]),
            "disks": _parse_disks(disks["stdout"]),
            "network": _parse_nics(nics["stdout"]),
        }
    except Exception as e:
        raise PxeException("HARDWARE_INFO_ERROR", f"获取硬件信息失败: {e}")


def _parse_lscpu(output: str) -> dict:
    try:
        data = json.loads(output)
        return data
    except json.JSONDecodeError:
        info = {}
        for line in output.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = v.strip()
        return info


def _parse_memory(output: str) -> dict:
    info = {}
    for line in output.splitlines():
        parts = line.split()
        if parts and parts[0] == "Mem:":
            info["total_gb"] = int(parts[1])
    return info


def _parse_disks(output: str) -> dict:
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"raw": output}


def _parse_nics(output: str) -> list:
    try:
        data = json.loads(output)
        return [{"name": l["ifname"], "state": l["operstate"]} for l in data]
    except json.JSONDecodeError:
        return []
