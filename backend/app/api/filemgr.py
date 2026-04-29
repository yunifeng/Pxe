"""文件管理 API 路由"""
import os

from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.auth.roles import Role
from app.config import settings
from app.database import get_db
from app.exceptions import PxeException
from app.filemgr import repo
from app.models import FileInfo

filemgr_router = APIRouter()


@filemgr_router.get("/")
def list_files(
    category: str = Query(None, description="筛选: script/config/repo"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR)),
):
    """列出文件"""
    files = repo.list_files(category, db)
    return {"success": True, "data": files}


@filemgr_router.post("/upload")
async def upload_file(
    file: UploadFile,
    category: str = "script",
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR)),
):
    """上传文件"""
    content = await file.read()
    result = repo.upload_file(file.filename, content, category, db=db)
    return {"success": True, "data": result}


@filemgr_router.delete("/{file_id}")
def remove_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN)),
):
    """删除文件"""
    repo.remove_file(file_id, db)
    return {"success": True}


@filemgr_router.post("/sync")
def sync_files(
    file_ids: list[int],
    node_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR)),
):
    """同步到指定 agent"""
    from app.filemgr.sync import sync_to_agent
    result = sync_to_agent(file_ids, node_id, db)
    return {"success": True, "data": result}


@filemgr_router.get("/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(Role.ADMIN, Role.OPERATOR)),
):
    """下载文件"""
    from fastapi.responses import FileResponse
    f = db.query(FileInfo).filter_by(id=file_id).first()
    if not f:
        raise PxeException("FILE_NOT_FOUND", f"文件不存在: {file_id}")
    full_path = os.path.join(settings.files_dir, f.path)
    if not os.path.exists(full_path):
        raise PxeException("FILE_NOT_FOUND", "文件不存在于磁盘")
    return FileResponse(full_path, filename=f.name)
