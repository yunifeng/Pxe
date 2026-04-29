"""节点管理 API 路由"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.auth.roles import Role
from app.database import get_db
from app.exceptions import PxeException
from app.models import Node

node_router = APIRouter()


class NodeCreateRequest(BaseModel):
    hostname: str
    ip: str
    mode: str = "agent"


@node_router.get("/")
def list_nodes(
    status: str = Query(None, description="筛选: online/offline"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR, Role.READONLY)),
):
    """列出节点 (支持筛选)"""
    query = db.query(Node)
    if status:
        query = query.filter_by(status=status)
    nodes = query.all()
    return {
        "success": True,
        "data": [
            {
                "id": n.id,
                "hostname": n.hostname,
                "ip": n.ip,
                "mode": n.mode,
                "status": n.status,
                "last_heartbeat": n.last_heartbeat.isoformat() if n.last_heartbeat else None,
            }
            for n in nodes
        ],
    }


@node_router.post("/")
def add_node(
    req: NodeCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR)),
):
    """添加节点"""
    node = Node(
        hostname=req.hostname,
        ip=req.ip,
        mode=req.mode,
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return {
        "success": True,
        "data": {
            "id": node.id,
            "hostname": node.hostname,
            "ip": node.ip,
            "mode": node.mode,
        },
    }


@node_router.delete("/{node_id}")
def remove_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN)),
):
    """移除节点"""
    node = db.query(Node).filter_by(id=node_id).first()
    if not node:
        raise PxeException("NODE_NOT_FOUND", f"节点不存在: {node_id}")
    db.delete(node)
    db.commit()
    return {"success": True}


@node_router.post("/{node_id}/check")
def check_node(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR)),
):
    """手动检查节点状态"""
    from app.node.monitor import check_node_status
    node = db.query(Node).filter_by(id=node_id).first()
    if not node:
        raise PxeException("NODE_NOT_FOUND", f"节点不存在: {node_id}")
    result = check_node_status(node)
    db.commit()
    return {"success": True, "data": result}


@node_router.get("/{node_id}/ssh")
def get_ssh_info(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR)),
):
    """获取 SSH 连接信息 (用于终端连接)"""
    from app.config import settings
    node = db.query(Node).filter_by(id=node_id).first()
    if not node:
        raise PxeException("NODE_NOT_FOUND", f"节点不存在: {node_id}")
    return {
        "success": True,
        "data": {
            "host": node.ip,
            "port": 22,
            "key_path": settings.ssh_key_path,
        },
    }
