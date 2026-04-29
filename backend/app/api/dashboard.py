"""仪表盘聚合 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.auth.roles import Role
from app.database import get_db
from app.models import BmcInfo, Host, InstallTask, Node
from app.pxe.dnsmasq import get_service_status as get_dnsmasq_status
from app.pxe.tftp import get_status as get_tftp_status
from app.utils.systemd import is_active

dashboard_router = APIRouter()


@dashboard_router.get("/")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR, Role.READONLY)),
):
    """聚合查询"""
    nodes = db.query(Node).all()
    node_stats = {
        "total": len(nodes),
        "online": sum(1 for n in nodes if n.status == "online"),
        "offline": sum(1 for n in nodes if n.status == "offline"),
    }
    hosts = db.query(Host).all()
    host_stats = {
        "total": len(hosts),
        "pending": sum(1 for h in hosts if h.deploy_status == "pending"),
        "installing": sum(1 for h in hosts if h.deploy_status == "installing"),
        "running": sum(1 for h in hosts if h.deploy_status == "running"),
        "failed": sum(1 for h in hosts if h.deploy_status == "failed"),
    }
    bmcs = db.query(BmcInfo).all()
    bmc_stats = {
        "total": len(bmcs),
        "on": sum(1 for b in bmcs if b.power_status == "on"),
        "off": sum(1 for b in bmcs if b.power_status == "off"),
        "unknown": sum(1 for b in bmcs if b.power_status in (None, "unknown")),
    }
    services = {
        "dnsmasq": is_active("dnsmasq"),
        "tftp": is_active("tftp-hpa"),
    }
    recent_tasks = (
        db.query(InstallTask)
        .order_by(InstallTask.created_at.desc())
        .limit(5)
        .all()
    )
    return {
        "success": True,
        "data": {
            "nodes": node_stats,
            "hosts": host_stats,
            "bmc": bmc_stats,
            "services": services,
            "recent_tasks": [
                {
                    "id": t.id,
                    "status": t.status,
                    "progress": t.progress,
                    "started_at": t.started_at.isoformat() if t.started_at else None,
                }
                for t in recent_tasks
            ],
            "quick_actions": [
                {"label": "添加节点", "path": "/node"},
                {"label": "创建安装任务", "path": "/pxe"},
                {"label": "批量电源操作", "path": "/bmc"},
            ],
        },
    }
