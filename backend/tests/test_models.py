"""测试数据模型"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def get_test_session():
    """获取测试数据库会话"""
    from sqlalchemy import create_engine
    from app.database import Base
    from sqlalchemy.orm import sessionmaker

    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    engine = create_engine(f"sqlite:///{tmp_db}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session(), tmp_db


class TestModels:
    """测试所有数据模型"""

    def test_node_model(self):
        """测试 Node 模型"""
        from app.models import Node
        session, tmp_db = get_test_session()
        try:
            node = Node(hostname="test-node", ip="192.168.1.100", mode="agent", status="online")
            session.add(node)
            session.commit()
            assert node.id is not None
            assert node.hostname == "test-node"
            assert node.ip == "192.168.1.100"
            assert node.mode == "agent"
            assert node.status == "online"
            assert node.created_at is not None
        finally:
            session.close()
            os.unlink(tmp_db)

    def test_bmc_info_model(self):
        """测试 BmcInfo 模型"""
        from app.models import BmcInfo, Node
        session, tmp_db = get_test_session()
        try:
            node = Node(hostname="test-node", ip="192.168.1.100", mode="agent")
            session.add(node)
            session.commit()

            bmc = BmcInfo(
                hostname="bmc-server",
                bmc_ip="192.168.1.200",
                username="admin",
                password="secret123",  # 应该被 Fernet 加密
                protocol="redfish",
                power_status="on",
                host_id=1
            )
            session.add(bmc)
            session.commit()
            assert bmc.id is not None
            assert bmc.hostname == "bmc-server"
            assert bmc.bmc_ip == "192.168.1.200"
            assert bmc.username == "admin"
            # 验证解密后密码正确
            assert bmc.password == "secret123"
            assert bmc.protocol == "redfish"
        finally:
            session.close()
            os.unlink(tmp_db)

    def test_host_model(self):
        """测试 Host 模型"""
        from app.models import Host
        session, tmp_db = get_test_session()
        try:
            host = Host(
                hostname="server-01",
                ip="192.168.1.50",
                mac_address="AA:BB:CC:DD:EE:FF",
                node_id=1,
                bmc_id=1,
                os="ubuntu-22.04",
                deploy_status="pending"
            )
            session.add(host)
            session.commit()
            assert host.id is not None
            assert host.hostname == "server-01"
            assert host.deploy_status == "pending"
            assert host.install_progress == 0
        finally:
            session.close()
            os.unlink(tmp_db)

    def test_pxe_config_model(self):
        """测试 PxeConfig 模型"""
        from app.models import PxeConfig
        session, tmp_db = get_test_session()
        try:
            pxe = PxeConfig(
                node_id=1,
                dnsmasq_config="dhcp-range=192.168.1.100,192.168.1.200",
                tftp_root="/tftpboot",
                ipxe_menu="default menu",
                dhcp_config="dhcp-config",
                mac_filters="[\"AA:BB:CC:DD:EE:FF\"]",
                status="enabled"
            )
            session.add(pxe)
            session.commit()
            assert pxe.id is not None
            assert pxe.status == "enabled"
        finally:
            session.close()
            os.unlink(tmp_db)

    def test_iso_image_model(self):
        """测试 IsoImage 模型"""
        from app.models import IsoImage
        session, tmp_db = get_test_session()
        try:
            iso = IsoImage(
                name="ubuntu-22.04.iso",
                local_path="/opt/pxe/images/ubuntu-22.04.iso",
                size=1024 * 1024 * 100,
                arch="x86_64",
                node_id=1,
                status="available"
            )
            session.add(iso)
            session.commit()
            assert iso.id is not None
            assert iso.name == "ubuntu-22.04.iso"
            assert iso.arch == "x86_64"
        finally:
            session.close()
            os.unlink(tmp_db)

    def test_install_task_model(self):
        """测试 InstallTask 模型"""
        from app.models import InstallTask
        session, tmp_db = get_test_session()
        try:
            task = InstallTask(
                host_id=1,
                iso_id=1,
                template_id=1,
                node_id=1,
                status="pending",
                progress=0
            )
            session.add(task)
            session.commit()
            assert task.id is not None
            assert task.status == "pending"
            assert task.progress == 0
        finally:
            session.close()
            os.unlink(tmp_db)

    def test_install_report_model(self):
        """测试 InstallReport 模型"""
        from app.models import InstallReport
        session, tmp_db = get_test_session()
        try:
            report = InstallReport(
                task_id=1,
                result="success",
                duration=3600,
                report_content="Install completed successfully"
            )
            session.add(report)
            session.commit()
            assert report.id is not None
            assert report.result == "success"
            assert report.duration == 3600
        finally:
            session.close()
            os.unlink(tmp_db)

    def test_file_info_model(self):
        """测试 FileInfo 模型"""
        from app.models import FileInfo
        session, tmp_db = get_test_session()
        try:
            fi = FileInfo(
                name="install.sh",
                type="script",
                path="/opt/pxe/files/scripts/install.sh",
                size=2048,
                category="install",
                sync_status="synced",
                node_id=1
            )
            session.add(fi)
            session.commit()
            assert fi.id is not None
            assert fi.type == "script"
            assert fi.sync_status == "synced"
        finally:
            session.close()
            os.unlink(tmp_db)

    def test_template_model(self):
        """测试 Template 模型"""
        from app.models import Template
        session, tmp_db = get_test_session()
        try:
            tpl = Template(
                name="Ubuntu Autoinstall",
                type="user-data",
                content="#cloud-config\nhostname: test",
                description="Ubuntu 22.04 autoinstall template",
                defaults='{"hostname": "server"}'
            )
            session.add(tpl)
            session.commit()
            assert tpl.id is not None
            assert tpl.name == "Ubuntu Autoinstall"
            assert tpl.type == "user-data"
        finally:
            session.close()
            os.unlink(tmp_db)

    def test_user_model(self):
        """测试 User 模型"""
        from app.models import User
        session, tmp_db = get_test_session()
        try:
            user = User(
                username="admin",
                password="admin123",  # 应该被 bcrypt 哈希
                role="admin"
            )
            session.add(user)
            session.commit()
            assert user.id is not None
            assert user.username == "admin"
            assert user.role == "admin"
            # 验证密码被哈希
            assert user.password_hash != "admin123"
            # 验证密码验证
            assert user.verify_password("admin123") is True
            assert user.verify_password("wrong") is False
        finally:
            session.close()
            os.unlink(tmp_db)

    def test_user_role_defaults(self):
        """测试 User 角色默认值"""
        from app.models import User
        session, tmp_db = get_test_session()
        try:
            user = User(username="test", password="test123")
            session.add(user)
            session.commit()
            assert user.role == "readonly"
        finally:
            session.close()
            os.unlink(tmp_db)
