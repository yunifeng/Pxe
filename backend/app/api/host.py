"""主机管理 API 路由"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.auth.roles import Role
from app.database import get_db
from app.exceptions import PxeException
from app.models import Host

host_router = APIRouter()


class HostCreateRequest(BaseModel):
    hostname: str
    ip: str = None
    mac_address: str = None
    node_id: int = None
    bmc_id: int = None


@host_router.get("/")
def list_hosts(
    status: str = Query(None, description="筛选: pending/installing/running/failed"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR, Role.READONLY)),
):
    """列出主机"""
    query = db.query(Host)
    if status:
        query = query.filter_by(deploy_status=status)
    hosts = query.all()
    return {
        "success": True,
        "data": [
            {
                "id": h.id,
                "hostname": h.hostname,
                "ip": h.ip,
                "mac_address": h.mac_address,
                "node_id": h.node_id,
                "bmc_id": h.bmc_id,
                "os": h.os,
                "deploy_status": h.deploy_status,
                "install_progress": h.install_progress,
            }
            for h in hosts
        ],
    }


@host_router.post("/")
def add_host(
    req: HostCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR)),
):
    """添加主机"""
    host = Host(
        hostname=req.hostname,
        ip=req.ip,
        mac_address=req.mac_address,
        node_id=req.node_id,
        bmc_id=req.bmc_id,
    )
    db.add(host)
    db.commit()
    db.refresh(host)
    return {
        "success": True,
        "data": {
            "id": host.id,
            "hostname": host.hostname,
            "ip": host.ip,
        },
    }


@host_router.delete("/{host_id}")
def remove_host(
    host_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN)),
):
    """移除主机"""
    host = db.query(Host).filter_by(id=host_id).first()
    if not host:
        raise PxeException("HOST_NOT_FOUND", f"主机不存在: {host_id}")
    db.delete(host)
    db.commit()
    return {"success": True}


@host_router.get("/{host_id}/hardware")
def get_hardware(
    host_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR, Role.READONLY)),
):
    """获取硬件清单"""
    host = db.query(Host).filter_by(id=host_id).first()
    if not host:
        raise PxeException("HOST_NOT_FOUND", f"主机不存在: {host_id}")
    if not host.ip:
        raise PxeException("MISSING_IP", "主机没有 IP 地址")
    from app.host.inventory import get_hardware_info as get_hw
    hw = get_hw(host.ip)
    return {"success": True, "data": hw}


@host_router.post("/{host_id}/ansible")
def run_ansible(
    host_id: int,
    playbook: str,
    extra_vars: str = "",
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR)),
):
    """执行 Ansible 命令"""
    host = db.query(Host).filter_by(id=host_id).first()
    if not host:
        raise PxeException("HOST_NOT_FOUND", f"主机不存在: {host_id}")
    from app.host.ansible import run_playbook as run_pb
    vars_dict = {k: v for k, v in (p.split("=") for p in extra_vars.split(",") if "=" in p)} if extra_vars else {}
    output = run_pb(host.ip, playbook, vars_dict)
    return {"success": True, "data": {"output": output}}


@host_router.post("/{host_id}/ssh")
def get_host_ssh(
    host_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR)),
):
    """SSH 连接信息"""
    from app.config import settings
    host = db.query(Host).filter_by(id=host_id).first()
    if not host:
        raise PxeException("HOST_NOT_FOUND", f"主机不存在: {host_id}")
    if not host.ip:
        raise PxeException("MISSING_IP", "主机没有 IP 地址")
    return {
        "success": True,
        "data": {
            "host": host.ip,
            "port": 22,
            "key_path": settings.ssh_key_path,
        },
    }
