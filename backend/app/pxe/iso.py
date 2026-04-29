"""ISO 镜像管理"""
import os
import subprocess
import tempfile

from app.config import settings
from app.database import get_db
from app.exceptions import PxeException
from app.models import IsoImage
from sqlalchemy.orm import Session


def list_images(node_id: int = None, db: Session = None) -> list:
    """列出 ISO 镜像"""
    query = db.query(IsoImage)
    if node_id:
        query = query.filter_by(node_id=node_id)
    images = query.all()
    return [
        {
            "id": img.id,
            "name": img.name,
            "local_path": img.local_path,
            "size": img.size,
            "arch": img.arch,
            "node_id": img.node_id,
            "status": img.status,
        }
        for img in images
    ]


def register_image(name: str, path: str, arch: str = "x86_64", node_id: int = None, db: Session = None) -> dict:
    """注册镜像到数据库"""
    if not os.path.exists(path):
        raise PxeException("FILE_NOT_FOUND", f"ISO 文件不存在: {path}")
    size = os.path.getsize(path)
    existing = db.query(IsoImage).filter_by(local_path=path).first()
    if existing:
        return {
            "id": existing.id,
            "name": existing.name,
            "local_path": existing.local_path,
            "message": "镜像已存在",
        }
    img = IsoImage(
        name=name,
        local_path=path,
        size=size,
        arch=arch,
        node_id=node_id,
    )
    db.add(img)
    db.commit()
    db.refresh(img)
    return {
        "id": img.id,
        "name": img.name,
        "local_path": img.local_path,
        "size": img.size,
        "arch": img.arch,
    }


def remove_image(image_id: int, db: Session = None) -> None:
    """移除镜像"""
    img = db.query(IsoImage).filter_by(id=image_id).first()
    if not img:
        raise PxeException("IMAGE_NOT_FOUND", f"ISO 镜像不存在: {image_id}")
    db.delete(img)
    db.commit()


def get_kernel_and_initrd(path: str) -> dict:
    """从 ISO 提取内核和 initrd 路径

    挂载 ISO 并读取 boot/grub/ 或 isolinux/ 目录

    Returns:
        {"kernel": "path/to/vmlinuz", "initrd": "path/to/initrd"}
    """
    if not os.path.exists(path):
        raise PxeException("FILE_NOT_FOUND", f"ISO 文件不存在: {path}")
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            subprocess.run(
                ["mount", "-o", "loop,ro", path, tmpdir],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            kernel = None
            initrd = None
            grub_dir = os.path.join(tmpdir, "boot", "grub")
            isolinux_dir = os.path.join(tmpdir, "isolinux")
            if os.path.isdir(grub_dir):
                for f in os.listdir(grub_dir):
                    if f.startswith("vmlinuz") or f.startswith("linux"):
                        kernel = os.path.join("boot", "grub", f)
                    if f.startswith("initrd") or f.startswith("initramfs"):
                        initrd = os.path.join("boot", "grub", f)
            if not kernel and os.path.isdir(isolinux_dir):
                for f in os.listdir(isolinux_dir):
                    if f.startswith("vmlinuz") or f.startswith("linux"):
                        kernel = os.path.join("isolinux", f)
                    if f.startswith("initrd") or f.startswith("initramfs"):
                        initrd = os.path.join("isolinux", f)
            return {"kernel": kernel, "initrd": initrd}
        except subprocess.CalledProcessError as e:
            raise PxeException("ISO_MOUNT_ERROR", f"挂载 ISO 失败: {e.stderr.strip()}")
        finally:
            subprocess.run(["umount", tmpdir], capture_output=True, timeout=10)
