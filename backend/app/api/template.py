"""配置模板 API 路由"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import require_role
from app.auth.roles import Role
from app.database import get_db
from app.template import preseed

template_router = APIRouter()


class TemplateCreateRequest(BaseModel):
    name: str
    type: str = Field(..., description="user-data/kickstart/preseed")
    content: str
    description: str = ""
    defaults: dict = None


class TemplateUpdateRequest(BaseModel):
    name: str = None
    type: str = None
    content: str = None
    description: str = None
    defaults: dict = None


class TemplateRenderRequest(BaseModel):
    variables: dict = {}


@template_router.get("/")
def list_templates(
    type: str = Query(None, description="筛选类型"),
    current_user: dict = Depends(require_role(Role.ADMIN)),
):
    """列出模板"""
    templates = preseed.list_templates(type)
    return {"success": True, "data": templates}


@template_router.post("/")
def create_template(
    req: TemplateCreateRequest,
    current_user: dict = Depends(require_role(Role.ADMIN)),
):
    """创建模板"""
    tmpl = preseed.create_template(req.name, req.type, req.content, req.defaults)
    return {"success": True, "data": tmpl}


@template_router.get("/{template_id}")
def get_template(
    template_id: int,
    current_user: dict = Depends(require_role(Role.ADMIN)),
):
    """获取模板"""
    tmpl = preseed.get_template(template_id)
    return {"success": True, "data": tmpl}


@template_router.put("/{template_id}")
def update_template(
    template_id: int,
    req: TemplateUpdateRequest,
    current_user: dict = Depends(require_role(Role.ADMIN)),
):
    """更新模板"""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    tmpl = preseed.update_template(template_id, **updates)
    return {"success": True, "data": tmpl}


@template_router.delete("/{template_id}")
def delete_template(
    template_id: int,
    current_user: dict = Depends(require_role(Role.ADMIN)),
):
    """删除模板"""
    preseed.delete_template(template_id)
    return {"success": True}


@template_router.post("/{template_id}/render")
def render_template(
    template_id: int,
    req: TemplateRenderRequest,
    current_user: dict = Depends(require_role(Role.ADMIN)),
):
    """渲染模板"""
    content = preseed.render_template(template_id, req.variables)
    return {"success": True, "data": {"content": content}}
