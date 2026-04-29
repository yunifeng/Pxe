"""文件同步"""
import hashlib
import os

from app.config import settings
from app.database import get_db
from app.exceptions import PxeException
from app.models import FileInfo
from app.node.ssh import exec_command
from sqlalchemy.orm import Session


def _md5(filepath: str) -> str:
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sync_to_agent(file_ids: list, node_id: int, db: Session = None) -> dict:
    """通过 SSH 同步文件到 agent"""
    from app.models import Node
    sess = db or next(get_db())
    try:
        node = sess.query(Node).filter_by(id=node_id).first()
        if not node:
            raise PxeException("NODE_NOT_FOUND", f"节点不存在: {node_id}")
        files = sess.query(FileInfo).filter(FileInfo.id.in_(file_ids)).all()
        synced = 0
        for f in files:
            src = os.path.join(settings.files_dir, f.path)
            if not os.path.exists(src):
                continue
            src_md5 = _md5(src)
            dest = os.path.join(settings.files_dir, f.path)
            exec_command(node.ip, f"scp {src} root@localhost:{dest}")
            f.sync_status = "synced"
            synced += 1
        sess.commit()
        return {"synced": synced, "total": len(files)}
    finally:
        if not db:
            sess.close()
