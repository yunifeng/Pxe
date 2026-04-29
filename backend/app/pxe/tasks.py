"""安装任务管理"""
from datetime import datetime, timezone

from app.database import get_db
from app.exceptions import PxeException
from app.models import InstallReport, InstallTask
from sqlalchemy.orm import Session


def create_task(host_id: int, iso_id: int, template_id: int = None, node_id: int = None, db: Session = None) -> dict:
    """创建安装任务"""
    task = InstallTask(
        host_id=host_id,
        iso_id=iso_id,
        template_id=template_id,
        node_id=node_id,
        status="pending",
        progress=0,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_to_dict(task)


def update_progress(task_id: int, progress: int, db: Session = None) -> dict:
    """更新任务进度"""
    task = _get_task(task_id, db)
    if task.status not in ("pending", "running"):
        raise PxeException("INVALID_TASK_STATE", f"任务状态 {task.status} 不能更新进度")
    task.status = "running"
    task.progress = min(progress, 100)
    if not task.started_at:
        task.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return _task_to_dict(task)


def complete_task(task_id: int, success: bool, duration: int = None, error: str = None, db: Session = None) -> dict:
    """完成任务并生成报告"""
    task = _get_task(task_id, db)
    completed = datetime.now(timezone.utc)
    task.status = "completed" if success else "failed"
    task.progress = 100 if success else task.progress
    task.completed_at = completed
    if duration is None:
        if task.started_at:
            duration = int((completed - task.started_at).total_seconds())
    report = InstallReport(
        task_id=task_id,
        result="success" if success else "failed",
        duration=duration,
        error_details=error,
    )
    db.add(report)
    db.commit()
    db.refresh(task)
    return _task_to_dict(task)


def get_task(task_id: int, db: Session = None) -> dict:
    """查询单个任务"""
    return _task_to_dict(_get_task(task_id, db))


def list_tasks(status: str = None, db: Session = None) -> list:
    """查询任务列表"""
    query = db.query(InstallTask)
    if status:
        query = query.filter_by(status=status)
    tasks = query.order_by(InstallTask.created_at.desc()).all()
    return [_task_to_dict(t) for t in tasks]


def retry_task(task_id: int, db: Session = None) -> dict:
    """重试失败任务"""
    task = _get_task(task_id, db)
    if task.status != "failed":
        raise PxeException("INVALID_TASK_STATE", f"只有失败任务可以重试 (当前: {task.status})")
    task.status = "pending"
    task.progress = 0
    task.started_at = None
    task.completed_at = None
    db.commit()
    db.refresh(task)
    return _task_to_dict(task)


def _get_task(task_id: int, db: Session):
    task = db.query(InstallTask).filter_by(id=task_id).first()
    if not task:
        raise PxeException("TASK_NOT_FOUND", f"安装任务不存在: {task_id}")
    return task


def _task_to_dict(task: InstallTask) -> dict:
    return {
        "id": task.id,
        "host_id": task.host_id,
        "iso_id": task.iso_id,
        "template_id": task.template_id,
        "node_id": task.node_id,
        "status": task.status,
        "progress": task.progress,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "log_path": task.log_path,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }
