"""IPMI 协议操作封装"""
from app.exceptions import PxeException

IPMI_CONNECT_TIMEOUT = 10
IPMI_RETRY_COUNT = 1


def _get_conn(bmc_info: dict):
    try:
        import ipmi
        return ipmi.BMC(
            hostname=bmc_info["bmc_ip"],
            user=bmc_info["username"],
            password=bmc_info["password"],
        )
    except ImportError:
        raise PxeException("MISSING_DEPENDENCY", "python-ipmi 未安装")
    except Exception as e:
        raise PxeException("IPMI_CONNECT_ERROR", f"IPMI 连接失败: {e}")


def get_power_status(bmc_info: dict) -> str:
    """查询电源状态"""
    conn = _get_conn(bmc_info)
    try:
        conn.open()
        status = conn.get_power_status()
        conn.close()
        return status.lower()
    except Exception as e:
        raise PxeException("IPMI_POWER_STATUS_ERROR", f"获取电源状态失败: {e}")


def power_on(bmc_info: dict) -> None:
    conn = _get_conn(bmc_info)
    try:
        conn.open()
        conn.power_on()
        conn.close()
    except Exception as e:
        raise PxeException("IPMI_POWER_ON_ERROR", f"开机失败: {e}")


def power_off(bmc_info: dict) -> None:
    conn = _get_conn(bmc_info)
    try:
        conn.open()
        conn.power_off()
        conn.close()
    except Exception as e:
        raise PxeException("IPMI_POWER_OFF_ERROR", f"关机失败: {e}")


def restart(bmc_info: dict) -> None:
    power_off(bmc_info)
    power_on(bmc_info)


def cycle(bmc_info: dict) -> None:
    conn = _get_conn(bmc_info)
    try:
        conn.open()
        conn.power_cycle()
        conn.close()
    except Exception as e:
        raise PxeException("IPMI_POWER_CYCLE_ERROR", f"电源循环失败: {e}")


def get_sensor_data(bmc_info: dict) -> dict:
    """获取传感器数据"""
    conn = _get_conn(bmc_info)
    try:
        conn.open()
        sdr = conn.get_sensor_data()
        conn.close()
        return {sensor.name: sensor.value for sensor in sdr}
    except Exception as e:
        raise PxeException("IPMI_SENSOR_ERROR", f"获取传感器数据失败: {e}")
