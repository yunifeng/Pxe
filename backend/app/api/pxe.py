"""PXE 服务管理 API 路由"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.auth.roles import Role
from app.database import get_db
from app.exceptions import PxeException
from app.pxe import dnsmasq, ipxe, iso, tasks, tftp

pxe_router = APIRouter()


# ============================================================
# 请求/响应模型
# ============================================================

class PxeConfigRequest(BaseModel):
    interface: str
    dhcp_range: str
    tftp_server: str = ""
    mac_filters: dict = Field(default_factory=dict)


class ServiceControlRequest(BaseModel):
    action: str = Field(..., description="start/stop/restart")


class IsoRegisterRequest(BaseModel):
    name: str
    path: str
    arch: str = "x86_64"
    node_id: int = None


class InstallTaskRequest(BaseModel):
    host_id: int
    iso_id: int
    template_id: int = None
    node_id: int = None


class MacFilterRequest(BaseModel):
    mac: str
    filename: str


class ProgressUpdateRequest(BaseModel):
    progress: int = Field(ge=0, le=100)


class CompleteTaskRequest(BaseModel):
    success: bool
    duration: int = None
    error: str = None


# ============================================================
# PXE 配置
# ============================================================

@pxe_router.get("/config")
def get_pxe_config(db: Session = Depends(get_db), current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR))):
    """获取当前 PXE 配置"""
    return {"success": True, "data": {"config": dnsmasq.get_config()}}


@pxe_router.put("/config")
def update_pxe_config(req: PxeConfigRequest, db: Session = Depends(get_db), current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR))):
    """更新 PXE 配置 (自动生成并应用 dnsmasq 配置)"""
    content = dnsmasq.generate_config(
        interface=req.interface,
        dhcp_range=req.dhcp_range,
        tftp_server=req.tftp_server,
        mac_filters=req.mac_filters,
    )
    dnsmasq.apply_config(content)
    return {"success": True, "data": {"config": content}}


@pxe_router.get("/services")
def get_services(current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR))):
    """获取服务状态 (dnsmasq, TFTP)"""
    return {
        "success": True,
        "data": {
            "dnsmasq": dnsmasq.get_service_status(),
            "tftp": tftp.get_status(),
        },
    }


@pxe_router.post("/services/{name}/control")
def control_service(name: str, req: ServiceControlRequest, current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR))):
    """服务控制 (start/stop/restart)"""
    action = req.action
    if name == "dnsmasq":
        from app.utils.systemd import systemctl as _systemctl
        _systemctl(action, "dnsmasq")
    elif name == "tftp":
        {"start": tftp.start, "stop": tftp.stop, "restart": tftp.restart}[action]()
    else:
        raise PxeException("UNKNOWN_SERVICE", f"未知服务: {name}")
    return {"success": True}


# ============================================================
# MAC 过滤
# ============================================================

@pxe_router.post("/config/mac-filter")
def add_mac_filter(req: MacFilterRequest, current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR))):
    """添加 MAC 地址到引导文件映射"""
    filters = dnsmasq.add_mac_filter(req.mac, req.filename)
    return {"success": True, "data": {"mac_filters": filters}}


@pxe_router.delete("/config/mac-filter/{mac}")
def remove_mac_filter(mac: str, current_user: dict = Depends(require_role(Role.ADMIN))):
    """移除 MAC 过滤规则"""
    filters = dnsmasq.remove_mac_filter(mac)
    return {"success": True, "data": {"mac_filters": filters}}


# ============================================================
# ISO 镜像
# ============================================================

@pxe_router.get("/images")
def list_images_ep(node_id: int = None, db: Session = Depends(get_db), current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR))):
    """列出 ISO 镜像"""
    images = iso.list_images(node_id, db)
    return {"success": True, "data": images}


@pxe_router.post("/images")
def register_image_ep(req: IsoRegisterRequest, db: Session = Depends(get_db), current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR))):
    """注册 ISO 镜像"""
    img = iso.register_image(req.name, req.path, req.arch, req.node_id, db)
    return {"success": True, "data": img}


@pxe_router.delete("/images/{image_id}")
def remove_image_ep(image_id: int, db: Session = Depends(get_db), current_user: dict = Depends(require_role(Role.ADMIN))):
    """移除 ISO 镜像"""
    iso.remove_image(image_id, db)
    return {"success": True}


# ============================================================
# iPXE 菜单
# ============================================================

@pxe_router.post("/menu/generate")
def generate_menu_ep(db: Session = Depends(get_db), current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR))):
    """根据当前 ISO 和主机生成 iPXE 菜单"""
    from app.models import Host, IsoImage
    imgs = [{"name": i.name, "local_path": i.local_path, "arch": i.arch} for i in db.query(IsoImage).all()]
    hosts = [{"hostname": h.hostname, "mac_address": h.mac_address} for h in db.query(Host).all()]
    menu = ipxe.generate_menu(isos=imgs, hosts=hosts)
    ipxe.write_menu(menu)
    return {"success": True, "data": {"menu": menu}}


# ============================================================
# 安装任务
# ============================================================

@pxe_router.post("/tasks")
def create_task_ep(req: InstallTaskRequest, db: Session = Depends(get_db), current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR))):
    """创建安装任务"""
    task = tasks.create_task(req.host_id, req.iso_id, req.template_id, req.node_id, db)
    return {"success": True, "data": task}


@pxe_router.get("/tasks")
def list_tasks_ep(status: str = None, db: Session = Depends(get_db), current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR))):
    """查询安装任务列表"""
    task_list = tasks.list_tasks(status, db)
    return {"success": True, "data": task_list}


@pxe_router.get("/tasks/{task_id}")
def get_task_ep(task_id: int, db: Session = Depends(get_db), current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR))):
    """查询单个安装任务"""
    task = tasks.get_task(task_id, db)
    return {"success": True, "data": task}


@pxe_router.put("/tasks/{task_id}/progress")
def update_task_progress_ep(task_id: int, req: ProgressUpdateRequest, db: Session = Depends(get_db), current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR))):
    """更新任务进度"""
    task = tasks.update_progress(task_id, req.progress, db)
    return {"success": True, "data": task}


@pxe_router.post("/tasks/{task_id}/complete")
def complete_task_ep(task_id: int, req: CompleteTaskRequest, db: Session = Depends(get_db), current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR))):
    """完成安装任务"""
    task = tasks.complete_task(task_id, req.success, req.duration, req.error, db)
    return {"success": True, "data": task}


@pxe_router.post("/tasks/{task_id}/retry")
def retry_task_ep(task_id: int, db: Session = Depends(get_db), current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR))):
    """重试失败任务"""
    task = tasks.retry_task(task_id, db)
    return {"success": True, "data": task}


@pxe_router.get("/reports/{task_id}")
def get_report_ep(task_id: int, db: Session = Depends(get_db), current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR))):
    """获取安装报告"""
    from app.models import InstallReport
    report = db.query(InstallReport).filter_by(task_id=task_id).first()
    if not report:
        raise PxeException("REPORT_NOT_FOUND", f"安装报告不存在: task_id={task_id}")
    return {
        "success": True,
        "data": {
            "id": report.id,
            "task_id": report.task_id,
            "result": report.result,
            "duration": report.duration,
            "error_details": report.error_details,
            "report_content": report.report_content,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        },
    }
