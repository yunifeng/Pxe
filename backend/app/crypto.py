"""
加密工具模块
提供密码哈希 (bcrypt) 和对称加密 (Fernet) 功能
"""
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from passlib.context import CryptContext

from app.config import settings

# bcrypt 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Fernet 密钥管理
_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """获取 Fernet 加密实例"""
    global _fernet
    if _fernet is None:
        key_path = settings.fernet_key_path
        key_dir = os.path.dirname(key_path)
        if key_dir:
            os.makedirs(key_dir, exist_ok=True)

        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(key_path, "wb") as f:
                f.write(key)
        _fernet = Fernet(key)
    return _fernet


def encrypt_password(plain_password: str) -> str:
    """使用 Fernet 加密密码"""
    if not plain_password:
        return ""
    return _get_fernet().encrypt(plain_password.encode("utf-8")).decode("utf-8")


def decrypt_password(encrypted_password: str) -> str:
    """使用 Fernet 解密密码"""
    if not encrypted_password:
        return ""
    try:
        return _get_fernet().decrypt(encrypted_password.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""
