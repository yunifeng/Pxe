"""测试配置系统"""
import os
import sys

# 确保能导入 backend/app 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestConfig:
    """测试配置加载"""

    def _default_settings(self):
        """创建无 .env 的配置实例，用于验证默认值"""
        from pydantic_settings import BaseSettings, SettingsConfigDict

        class DefaultSettings(BaseSettings):
            app_mode: str = "agent"
            db_path: str = "/opt/pxe/data/pxe.db"
            jwt_secret: str = "test"
            jwt_expire_minutes: int = 1440
            fernet_key_path: str = "/root/.pxe/secret.key"
            ssh_key_path: str = "/root/.ssh/pxe_id_ed25519"
            log_dir: str = "/opt/pxe/logs/"
            tftp_root: str = "/opt/pxe/tftpboot/"
            images_dir: str = "/opt/pxe/images/"
            files_dir: str = "/opt/pxe/files/"

            model_config = SettingsConfigDict(env_file=None)

        return DefaultSettings()

    def test_default_config_loads(self):
        """测试默认配置能正常加载"""
        from app.config import settings
        assert settings is not None

    def test_app_mode_default(self):
        """测试 app_mode 默认值为 agent"""
        assert self._default_settings().app_mode == "agent"

    def test_db_path_default(self):
        """测试 db_path 默认值"""
        assert self._default_settings().db_path == "/opt/pxe/data/pxe.db"

    def test_jwt_expire_minutes_default(self):
        """测试 jwt_expire_minutes 默认值"""
        assert self._default_settings().jwt_expire_minutes == 1440

    def test_jwt_secret_generated(self):
        """测试 jwt_secret 默认生成随机值"""
        from app.config import settings
        assert len(settings.jwt_secret) > 0

    def test_fernet_key_path_default(self):
        """测试 fernet_key_path 默认值"""
        assert self._default_settings().fernet_key_path == "/root/.pxe/secret.key"

    def test_ssh_key_path_default(self):
        """测试 ssh_key_path 默认值"""
        assert self._default_settings().ssh_key_path == "/root/.ssh/pxe_id_ed25519"

    def test_log_dir_default(self):
        """测试 log_dir 默认值"""
        assert self._default_settings().log_dir == "/opt/pxe/logs/"

    def test_tftp_root_default(self):
        """测试 tftp_root 默认值"""
        assert self._default_settings().tftp_root == "/opt/pxe/tftpboot/"

    def test_images_dir_default(self):
        """测试 images_dir 默认值"""
        assert self._default_settings().images_dir == "/opt/pxe/images/"

    def test_files_dir_default(self):
        """测试 files_dir 默认值"""
        assert self._default_settings().files_dir == "/opt/pxe/files/"
