"""
认证 API 路由模块
提供登录、登出、获取用户信息等认证相关端点
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_role
from app.auth.jwt_handler import create_token
from app.config import settings
from app.database import get_db
from app.exceptions import PxeException
from app.models import User

# 认证路由
auth_router = APIRouter()

# 登录频率限制: 内存计数器 {ip: [(timestamp, ...), ...]}
_login_attempts: dict[str, list] = {}

# 每分钟最大登录尝试次数
LOGIN_RATE_LIMIT = 5


class LoginRequest(BaseModel):
    """登录请求体"""

    username: str
    password: str


def _init_default_admin(db: Session):
    """
    初始化默认管理员账户

    如果数据库中不存在任何用户，自动创建默认管理员账户
    用户名: admin, 密码: admin123
    """
    existing_user = db.query(User).filter_by(username="admin").first()
    if existing_user is None:
        admin_user = User(
            username="admin",
            role="admin",
        )
        admin_user.password = "admin123"
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)


def _check_rate_limit(ip: str) -> bool:
    """
    检查 IP 的登录频率限制

    Args:
        ip: 客户端 IP 地址

    Returns:
        True 表示未超过限制，False 表示超过限制
    """
    now = datetime.now(timezone.utc)
    if ip not in _login_attempts:
        _login_attempts[ip] = []

    # 清理一分钟前的记录
    _login_attempts[ip] = [
        t for t in _login_attempts[ip] if (now - t).total_seconds() < 60
    ]

    if len(_login_attempts[ip]) >= LOGIN_RATE_LIMIT:
        return False

    # 记录本次尝试
    _login_attempts[ip].append(now)
    return True


@auth_router.post("/login")
def login(request: LoginRequest, request_obj: Request, db: Session = Depends(get_db)):
    """
    用户登录端点

    验证用户名和密码，成功后返回 JWT 令牌

    Args:
        request: 登录请求体 (username, password)
        request_obj: FastAPI 请求对象 (用于获取客户端 IP)
        db: 数据库会话

    Returns:
        包含 token 和用户信息的响应

    Raises:
        PxeException: 凭证无效或超过登录频率限制时抛出
    """
    # 初始化默认管理员
    _init_default_admin(db)

    # 检查登录频率限制
    client_ip = request_obj.client.host
    if not _check_rate_limit(client_ip):
        raise PxeException(
            "RATE_LIMIT_EXCEEDED",
            "登录尝试次数过多，请稍后再试",
            status_code=429,
        )

    # 验证用户名密码
    user = db.query(User).filter_by(username=request.username).first()
    if user is None or not user.verify_password(request.password):
        raise PxeException(
            "INVALID_CREDENTIALS",
            "用户名或密码错误",
            status_code=401,
        )

    # 更新最后登录时间
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    # 生成 JWT 令牌
    token = create_token(user_id=user.id, role=user.role)

    return {
        "success": True,
        "data": {
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
            },
        },
    }


@auth_router.get("/profile")
def profile(current_user: dict = Depends(get_current_user)):
    """
    获取当前用户信息

    需要有效的 Bearer token

    Args:
        current_user: 当前已认证用户

    Returns:
        用户信息字典
    """
    return {
        "success": True,
        "data": current_user,
    }


@auth_router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):
    """
    用户登出

    JWT 为无状态令牌，服务端无法主动撤销。
    此端点用于确认登出操作，实际 token 清除由前端处理。

    Args:
        current_user: 当前已认证用户

    Returns:
        登出成功响应
    """
    return {
        "success": True,
    }
