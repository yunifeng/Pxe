"""测试配置系统"""
import os
import sys

# 确保能导入 backend/app 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestConfig:
    """测试配置加载"""

    def test_default_config_loads(self):
        """测试默认配置能正常加载"""
        from app.config import settings
        assert settings is not None

    def test_app_mode_default(self):
        """测试 app_mode 默认值为 agent"""
        from app.config import settings
        assert settings.app_mode == "agent"

    def test_db_path_default(self):
        """测试 db_path 默认值"""
        from app.config import settings
        assert settings.db_path == "/opt/pxe/data/pxe.db"

    def test_jwt_expire_minutes_default(self):
        """测试 jwt_expire_minutes 默认值"""
        from app.config import settings
        assert settings.jwt_expire_minutes == 1440

    def test_jwt_secret_generated(self):
        """测试 jwt_secret 默认生成随机值"""
        from app.config import settings
        assert len(settings.jwt_secret) > 0

    def test_fernet_key_path_default(self):
        """测试 fernet_key_path 默认值"""
        from app.config import settings
        assert settings.fernet_key_path == "/root/.pxe/secret.key"

    def test_ssh_key_path_default(self):
        """测试 ssh_key_path 默认值"""
        from app.config import settings
        assert settings.ssh_key_path == "/root/.ssh/pxe_id_ed25519"

    def test_log_dir_default(self):
        """测试 log_dir 默认值"""
        from app.config import settings
        assert settings.log_dir == "/opt/pxe/logs/"

    def test_tftp_root_default(self):
        """测试 tftp_root 默认值"""
        from app.config import settings
        assert settings.tftp_root == "/opt/pxe/tftpboot/"

    def test_images_dir_default(self):
        """测试 images_dir 默认值"""
        from app.config import settings
        assert settings.images_dir == "/opt/pxe/images/"

    def test_files_dir_default(self):
        """测试 files_dir 默认值"""
        from app.config import settings
        assert settings.files_dir == "/opt/pxe/files/"
