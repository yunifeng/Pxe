"""批量 BMC 操作"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session

from app.bmc import ipmi_handler, redfish_handler
from app.database import get_db
from app.exceptions import PxeException
from app.models import BmcInfo

MAX_CONCURRENT = 10


def _do_action(bmc: BmcInfo, action: str) -> dict:
    info = {
        "bmc_ip": bmc.bmc_ip,
        "username": bmc.username,
        "password": bmc.password,
    }
    handler = redfish_handler if bmc.protocol == "redfish" else ipmi_handler
    try:
        getattr(handler, action)(info)
        return {"success": True}
    except PxeException as e:
        return {"success": False, "error": e.message}
    except Exception as e:
        return {"success": False, "error": str(e)}


def batch_power_action(bmc_ids: list, action: str, db: Session = None) -> dict:
    """批量电源操作

    Args:
        bmc_ids: BMC ID 列表
        action: 电源操作 (power_on/power_off/restart/cycle)

    Returns:
        {bmc_id: {"success": bool, "error": str}}
    """
    valid_actions = {"power_on", "power_off", "restart", "cycle"}
    if action not in valid_actions:
        raise PxeException("INVALID_ACTION", f"不支持的电源操作: {action}")
    bmcs = db.query(BmcInfo).filter(BmcInfo.id.in_(bmc_ids)).all()
    if len(bmcs) != len(bmc_ids):
        found = {b.id for b in bmcs}
        missing = set(bmc_ids) - found
        raise PxeException("BMC_NOT_FOUND", f"BMC 不存在: {missing}")
    results = {}
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as pool:
        futures = {pool.submit(_do_action, bmc, action): bmc.id for bmc in bmcs}
        for future in as_completed(futures):
            bmc_id = futures[future]
            results[bmc_id] = future.result()
    return results
