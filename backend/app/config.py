"""
配置管理系统
使用 pydantic-settings 读取环境变量和配置文件
"""
import os
import secrets
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    # 应用模式: master (管理节点) 或 agent (代理节点)
    app_mode: str = "agent"

    # 数据库路径 (SQLite)
    db_path: str = "/opt/pxe/data/pxe.db"

    # JWT 密钥 (默认生成随机值)
    jwt_secret: str = secrets.token_hex(32)

    # JWT 过期时间 (分钟)，默认 24 小时
    jwt_expire_minutes: int = 1440

    # Fernet 加密密钥文件路径 (用于加密 BMC 密码)
    fernet_key_path: str = "/root/.pxe/secret.key"

    # SSH 私钥路径 (用于 Master 管理 Agent)
    ssh_key_path: str = "/root/.ssh/pxe_id_ed25519"

    # 日志目录
    log_dir: str = "/opt/pxe/logs/"

    # TFTP 根目录
    tftp_root: str = "/opt/pxe/tftpboot/"

    # ISO 镜像目录
    images_dir: str = "/opt/pxe/images/"

    # 文件管理目录 (脚本、配置文件等)
    files_dir: str = "/opt/pxe/files/"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# 全局配置实例
settings = Settings()


def load_local_config() -> Settings:
    """
    加载本地配置覆盖
    如果存在 backend/app/config.local.py，使用其中的配置覆盖默认值
    """
    local_config_path = os.path.join(
        os.path.dirname(__file__), "config.local.py"
    )
    if os.path.exists(local_config_path):
        # 动态导入本地配置
        import importlib.util
        spec = importlib.util.spec_from_file_location("config_local", local_config_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "settings"):
            return module.settings
    return settings
