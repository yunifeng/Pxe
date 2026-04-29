"""脚本/软件仓库管理"""
import os
import shutil

from app.config import settings
from app.database import get_db
from app.exceptions import PxeException
from app.models import FileInfo
from sqlalchemy.orm import Session

ALLOWED_CATEGORIES = {"script", "config", "repo"}


def list_files(category: str = None, db: Session = None) -> list:
    """按分类列出文件"""
    sess = db or next(get_db())
    try:
        query = sess.query(FileInfo)
        if category and category in ALLOWED_CATEGORIES:
            query = query.filter_by(category=category)
        files = query.all()
        return [
            {
                "id": f.id,
                "name": f.name,
                "type": f.type,
                "category": f.category,
                "path": f.path,
                "size": f.size,
                "sync_status": f.sync_status,
            }
            for f in files
        ]
    finally:
        if not db:
            sess.close()


def upload_file(filename: str, file_content: bytes, category: str, node_id: int = None, db: Session = None) -> dict:
    """上传文件"""
    if category not in ALLOWED_CATEGORIES:
        raise PxeException("INVALID_CATEGORY", f"不支持的分类: {category}")
    sess = db or next(get_db())
    try:
        target_dir = os.path.join(settings.files_dir, category)
        os.makedirs(target_dir, exist_ok=True)
        filepath = os.path.join(target_dir, filename)
        with open(filepath, "wb") as f:
            f.write(file_content)
        size = len(file_content)
        info = FileInfo(
            name=filename,
            type=category,
            path=os.path.join(category, filename),
            size=size,
            category=category,
            node_id=node_id,
        )
        sess.add(info)
        sess.commit()
        sess.refresh(info)
        return {
            "id": info.id,
            "name": info.name,
            "path": info.path,
            "size": info.size,
        }
    finally:
        if not db:
            sess.close()


def remove_file(file_id: int, db: Session = None) -> None:
    """删除文件"""
    sess = db or next(get_db())
    try:
        f = sess.query(FileInfo).filter_by(id=file_id).first()
        if not f:
            raise PxeException("FILE_NOT_FOUND", f"文件不存在: {file_id}")
        full_path = os.path.join(settings.files_dir, f.path)
        if os.path.exists(full_path):
            os.remove(full_path)
        sess.delete(f)
        sess.commit()
    finally:
        if not db:
            sess.close()
