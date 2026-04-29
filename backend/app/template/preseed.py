"""Preseed/Kickstart 模板管理"""
import json
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import PxeException
from app.models import Template

BUILTIN_TEMPLATES = [
    {
        "name": "Ubuntu 22.04 Preseed (默认)",
        "type": "user-data",
        "content": "#cloud-config\nhostname: {{ hostname }}\npassword: {{ password }}\nchpasswd: { expire: false }\nssh_authorized_keys:\n  - {{ ssh_key }}\nlocale: zh_CN.UTF-8\ntpmmode: disable\nautoinstall:\n  network:\n    ethernets:\n      eth0:\n        dhcp4: true\n  storage:\n    layout:\n      name: direct\n  identity:\n    hostname: {{ hostname }}\n    username: {{ username }}\n    password: {{ password }}\n  user_data:\n    package_update: true\n    packages: [net-tools, iproute2]",
        "defaults": {"hostname": "pxe-host", "username": "admin", "password": "admin", "ssh_key": ""},
    }
]


def create_template(name: str, type: str, content: str, defaults: dict = None) -> dict:
    db = next(get_db())
    try:
        tmpl = Template(name=name, type=type, content=content, defaults=json.dumps(defaults) if defaults else None)
        db.add(tmpl)
        db.commit()
        db.refresh(tmpl)
        return _to_dict(tmpl)
    finally:
        db.close()


def get_template(tmpl_id: int) -> dict:
    db = next(get_db())
    try:
        tmpl = db.query(Template).filter_by(id=tmpl_id).first()
        if not tmpl:
            raise PxeException("TEMPLATE_NOT_FOUND", f"模板不存在: {tmpl_id}")
        return _to_dict(tmpl)
    finally:
        db.close()


def list_templates(type: str = None, db: Session = None) -> list:
    sess = db or next(get_db())
    try:
        query = sess.query(Template)
        if type:
            query = query.filter_by(type=type)
        return [_to_dict(t) for t in query.all()]
    finally:
        if not db:
            sess.close()


def update_template(tmpl_id: int, **fields) -> dict:
    db = next(get_db())
    try:
        tmpl = db.query(Template).filter_by(id=tmpl_id).first()
        if not tmpl:
            raise PxeException("TEMPLATE_NOT_FOUND", f"模板不存在: {tmpl_id}")
        for key, value in fields.items():
            if hasattr(tmpl, key):
                setattr(tmpl, key, value)
        db.commit()
        db.refresh(tmpl)
        return _to_dict(tmpl)
    finally:
        db.close()


def delete_template(tmpl_id: int) -> None:
    db = next(get_db())
    try:
        tmpl = db.query(Template).filter_by(id=tmpl_id).first()
        if not tmpl:
            raise PxeException("TEMPLATE_NOT_FOUND", f"模板不存在: {tmpl_id}")
        db.delete(tmpl)
        db.commit()
    finally:
        db.close()


def render_template(tmpl_id: int, variables: dict = None) -> str:
    tmpl = get_template(tmpl_id)
    content = tmpl["content"]
    if variables:
        try:
            return content.format(**variables)
        except KeyError as e:
            raise PxeException("RENDER_ERROR", f"模板变量缺失: {e}")
        except Exception as e:
            raise PxeException("RENDER_ERROR", f"模板渲染失败: {e}")
    return content


def _to_dict(tmpl: Template) -> dict:
    return {
        "id": tmpl.id,
        "name": tmpl.name,
        "type": tmpl.type,
        "content": tmpl.content,
        "description": tmpl.description,
        "defaults": json.loads(tmpl.defaults) if tmpl.defaults else None,
        "created_at": tmpl.created_at.isoformat() if tmpl.created_at else None,
    }
