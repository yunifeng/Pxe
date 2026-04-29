"""Redfish 协议操作封装"""
from app.exceptions import PxeException

REDFISH_TIMEOUT = 10


def _get_session(bmc_info: dict):
    try:
        from redfish.rest.v1 import ServerProtocol
        from redfish.rest import v1
    except ImportError:
        raise PxeException("MISSING_DEPENDENCY", "redfish-rest-client 未安装")
    sess = ServerProtocol()
    sess.set_base_url(f"https://{bmc_info['bmc_ip']}")
    sess.set_username(bmc_info["username"])
    sess.set_password(bmc_info["password"])
    sess.set_timeout(REDFISH_TIMEOUT)
    try:
        sess.login()
    except Exception as e:
        raise PxeException("REDFISH_CONNECT_ERROR", f"Redfish 连接失败: {e}")
    return sess


def get_power_status(bmc_info: dict) -> str:
    sess = _get_session(bmc_info)
    try:
        system_resp = sess.get("/redfish/v1/Systems/1")
        if system_resp.status != 200:
            return "unknown"
        return system_resp.dict.get("PowerState", "On").lower()
    except Exception as e:
        raise PxeException("REDFISH_POWER_STATUS_ERROR", f"获取电源状态失败: {e}")
    finally:
        sess.logout()


def power_on(bmc_info: dict) -> None:
    sess = _get_session(bmc_info)
    try:
        sess.patch(
            "/redfish/v1/Systems/1",
            body={"PowerState": "On"},
        )
    except Exception as e:
        raise PxeException("REDFISH_POWER_ON_ERROR", f"开机失败: {e}")
    finally:
        sess.logout()


def power_off(bmc_info: dict) -> None:
    sess = _get_session(bmc_info)
    try:
        sess.patch(
            "/redfish/v1/Systems/1",
            body={"PowerState": "Off"},
        )
    except Exception as e:
        raise PxeException("REDFISH_POWER_OFF_ERROR", f"关机失败: {e}")
    finally:
        sess.logout()


def restart(bmc_info: dict) -> None:
    sess = _get_session(bmc_info)
    try:
        sess.patch(
            "/redfish/v1/Systems/1",
            body={"ResetType": "GracefulRestart"},
        )
    except Exception as e:
        raise PxeException("REDFISH_RESTART_ERROR", f"重启失败: {e}")
    finally:
        sess.logout()


def cycle(bmc_info: dict) -> None:
    sess = _get_session(bmc_info)
    try:
        sess.patch(
            "/redfish/v1/Systems/1",
            body={"ResetType": "ForceRestart"},
        )
    except Exception as e:
        raise PxeException("REDFISH_CYCLE_ERROR", f"电源循环失败: {e}")
    finally:
        sess.logout()


def auto_detect(bmc_info: dict) -> str:
    """自动检测: 优先 Redfish，不支持则回退到 IPMI"""
    try:
        import redfish  # noqa: F401
        status = get_power_status(bmc_info)
        if status != "unknown":
            return "redfish"
    except Exception:
        pass
    return "ipmi"
