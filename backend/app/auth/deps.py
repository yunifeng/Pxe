"""
FastAPI 依赖注入模块
提供认证和授权相关的依赖函数
"""
from collections.abc import Callable

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.auth.jwt_handler import verify_token

# OAuth2 Bearer 令牌提取器
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    从 Bearer 令牌获取当前用户信息

    从请求的 Authorization 头中提取 Bearer token，验证后返回用户 payload

    Args:
        token: 通过 OAuth2PasswordBearer 自动提取的 Bearer token

    Returns:
        包含用户信息的字典 (user_id, role, exp)

    Raises:
        PxeException: 令牌无效或过期时抛出
    """
    payload = verify_token(token)
    return payload


def require_role(*roles: str) -> Callable:
    """
    角色校验依赖工厂函数

    生成一个依赖函数，检查当前用户角色是否在允许的角色列表中

    Args:
        *roles: 允许的角色列表

    Returns:
        依赖函数，可注入到 FastAPI 路由中

    Raises:
        PxeException: 用户角色不在允许列表中时抛出
    """

    def _check_role(current_user: dict = Depends(get_current_user)) -> dict:
        """角色检查内部函数"""
        if current_user.get("role") not in roles:
            from app.exceptions import PxeException

            raise PxeException(
                "FORBIDDEN",
                "无权访问此资源",
                status_code=403,
            )
        return current_user

    return _check_role
