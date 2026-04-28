"""
JWT 令牌管理模块
提供令牌的签发和验证功能
"""
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings
from app.exceptions import PxeException

# JWT 算法
ALGORITHM = "HS256"


def create_token(user_id: int, role: str) -> str:
    """
    签发 JWT 令牌

    Args:
        user_id: 用户 ID
        role: 用户角色 (admin/operator/readonly)

    Returns:
        签发的 JWT 字符串
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    return token


def verify_token(token: str) -> dict:
    """
    验证 JWT 令牌并返回 payload

    Args:
        token: JWT 字符串

    Returns:
        payload 字典 (包含 user_id, role, exp)

    Raises:
        PxeException: 令牌无效或过期时抛出
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        role: str = payload.get("role")
        exp: datetime = payload.get("exp")
        if user_id is None or role is None or exp is None:
            raise PxeException("INVALID_TOKEN", "Token 无效或已过期")
        return payload
    except JWTError:
        raise PxeException("INVALID_TOKEN", "Token 无效或已过期")
