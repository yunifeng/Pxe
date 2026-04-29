"""BMC 管理 API 路由"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.auth.roles import Role
from app.database import get_db
from app.exceptions import PxeException
from app.models import BmcInfo

bmc_router = APIRouter()


class BmcCreateRequest(BaseModel):
    hostname: str
    bmc_ip: str
    username: str
    password: str
    protocol: str = "redfish"


class BmcBatchAddRequest(BaseModel):
    csv_data: str = Field(..., description="CSV 格式: hostname,ip,user,pass,protocol")


class BmcPowerActionRequest(BaseModel):
    action: str = Field(..., description="on/off/restart/cycle")


class BmcBatchActionRequest(BaseModel):
    bmc_ids: list[int]
    action: str = Field(..., description="on/off/restart/cycle")


@bmc_router.get("/")
def list_bmcs(
    status: str = Query(None, description="筛选: on/off/unknown"),
    protocol: str = Query(None, description="筛选: ipmi/redfish"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR, Role.READONLY)),
):
    """列出 BMC (支持筛选)"""
    query = db.query(BmcInfo)
    if status:
        query = query.filter_by(power_status=status)
    if protocol:
        query = query.filter_by(protocol=protocol)
    bmcs = query.all()
    return {
        "success": True,
        "data": [
            {
                "id": b.id,
                "hostname": b.hostname,
                "bmc_ip": b.bmc_ip,
                "username": b.username,
                "protocol": b.protocol,
                "power_status": b.power_status,
                "status": b.status,
            }
            for b in bmcs
        ],
    }


@bmc_router.post("/")
def add_bmc(
    req: BmcCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR)),
):
    """添加单个 BMC"""
    bmc = BmcInfo(
        hostname=req.hostname,
        bmc_ip=req.bmc_ip,
        username=req.username,
        protocol=req.protocol,
    )
    bmc.password = req.password
    db.add(bmc)
    db.commit()
    db.refresh(bmc)
    return {
        "success": True,
        "data": {
            "id": bmc.id,
            "hostname": bmc.hostname,
            "bmc_ip": bmc.bmc_ip,
            "protocol": bmc.protocol,
        },
    }


@bmc_router.post("/batch")
def batch_add_bmcs(
    req: BmcBatchAddRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN)),
):
    """批量添加 BMC (CSV 格式: hostname,ip,user,pass,protocol)"""
    added = 0
    for line in req.csv_data.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) < 4:
            continue
        protocol = parts[4] if len(parts) > 4 else "redfish"
        bmc = BmcInfo(
            hostname=parts[0],
            bmc_ip=parts[1],
            username=parts[2],
            protocol=protocol,
        )
        bmc.password = parts[3]
        db.add(bmc)
        added += 1
    db.commit()
    return {"success": True, "data": {"added": added}}


@bmc_router.post("/{bmc_id}/power/{action}")
def power_action(
    bmc_id: int,
    action: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR)),
):
    """单个 BMC 电源操作"""
    valid = {"on", "off", "restart", "cycle"}
    if action not in valid:
        raise PxeException("INVALID_ACTION", f"不支持的电源操作: {action}")
    bmc = db.query(BmcInfo).filter_by(id=bmc_id).first()
    if not bmc:
        raise PxeException("BMC_NOT_FOUND", f"BMC 不存在: {bmc_id}")
    info = {
        "bmc_ip": bmc.bmc_ip,
        "username": bmc.username,
        "password": bmc.password,
    }
    handler = (
        __import__("app.bmc.redfish_handler", fromlist=[""])
        if bmc.protocol == "redfish"
        else __import__("app.bmc.ipmi_handler", fromlist=[""])
    )
    getattr(handler, f"power_{action}")(info)
    bmc.power_status = action if action in ("on", "off") else "unknown"
    db.commit()
    return {"success": True, "data": {"bmc_id": bmc_id, "power_status": bmc.power_status}}


@bmc_router.post("/batch-action")
def batch_power_action(
    req: BmcBatchActionRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN)),
):
    """批量 BMC 电源操作"""
    from app.bmc.batch import batch_power_action as do_batch
    results = do_batch(req.bmc_ids, req.action, db)
    for bmc_id, result in results.items():
        bmc = db.query(BmcInfo).filter_by(id=bmc_id).first()
        if bmc and result.get("success"):
            bmc.power_status = req.action if req.action in ("on", "off") else "unknown"
    db.commit()
    return {"success": True, "data": results}


@bmc_router.get("/stats")
def bmc_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR, Role.READONLY)),
):
    """BMC 统计信息"""
    total = db.query(BmcInfo).count()
    on_count = db.query(BmcInfo).filter_by(power_status="on").count()
    off_count = db.query(BmcInfo).filter_by(power_status="off").count()
    unknown_count = total - on_count - off_count
    return {
        "success": True,
        "data": {
            "total": total,
            "on": on_count,
            "off": off_count,
            "unknown": unknown_count,
        },
    }
