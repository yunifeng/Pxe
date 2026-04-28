"""
数据模型模块
定义所有 SQLAlchemy ORM 模型
"""
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship

from app.crypto import decrypt_password, encrypt_password, pwd_context
from app.database import Base


class Node(Base):
    """集群节点 (Master/Agent)"""

    __tablename__ = "node"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hostname = Column(String(255), nullable=False, index=True)
    ip = Column(String(45), nullable=False)  # IPv4/IPv6
    mode = Column(String(20), nullable=False, default="agent")  # master/agent
    status = Column(String(20), nullable=False, default="offline")  # online/offline
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    hosts = relationship("Host", back_populates="node")
    pxe_configs = relationship("PxeConfig", back_populates="node")
    iso_images = relationship("IsoImage", back_populates="node")
    install_tasks = relationship("InstallTask", back_populates="node")
    file_infos = relationship("FileInfo", back_populates="node")

    def __repr__(self):
        return f"<Node(id={self.id}, hostname='{self.hostname}', mode='{self.mode}')>"


class BmcInfo(Base):
    """服务器 BMC 信息"""

    __tablename__ = "bmc_info"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hostname = Column(String(255), nullable=False)
    bmc_ip = Column(String(45), nullable=False)
    username = Column(String(100), nullable=False)
    encrypted_password = Column(Text, nullable=True)  # Fernet 加密的密码
    protocol = Column(String(20), nullable=False, default="redfish")  # ipmi/redfish
    power_status = Column(String(20), nullable=True)  # on/off/unknown
    host_id = Column(Integer, ForeignKey("host.id"), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # host_id 列为外键引用 Host，但 ORM 关联方向通过 Host.bmc 实现
    # (双向 FK 场景下不能同时建立双向 ORM relationship)

    @property
    def password(self) -> str:
        """解密密码"""
        return decrypt_password(self.encrypted_password)

    @password.setter
    def password(self, value: str):
        """加密并存储密码"""
        self.encrypted_password = encrypt_password(value) if value else None

    def __repr__(self):
        return f"<BmcInfo(id={self.id}, hostname='{self.hostname}', bmc_ip='{self.bmc_ip}')>"


class Host(Base):
    """物理服务器"""

    __tablename__ = "host"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hostname = Column(String(255), nullable=False, index=True)
    ip = Column(String(45), nullable=True)
    mac_address = Column(String(17), nullable=True, index=True)  # AA:BB:CC:DD:EE:FF
    node_id = Column(Integer, ForeignKey("node.id"), nullable=True)
    bmc_id = Column(Integer, ForeignKey("bmc_info.id"), nullable=True)
    os = Column(String(100), nullable=True)
    deploy_status = Column(
        String(20), nullable=False, default="pending"
    )  # pending/installing/running/failed
    install_progress = Column(Integer, nullable=False, default=0)  # 0-100
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    node = relationship("Node", back_populates="hosts")
    bmc = relationship("BmcInfo", foreign_keys=[bmc_id])
    install_tasks = relationship("InstallTask", back_populates="host")

    def __repr__(self):
        return f"<Host(id={self.id}, hostname='{self.hostname}', status='{self.deploy_status}')>"


class PxeConfig(Base):
    """PXE 服务配置"""

    __tablename__ = "pxe_config"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    node_id = Column(Integer, ForeignKey("node.id"), nullable=True)
    dnsmasq_config = Column(Text, nullable=True)  # dnsmasq 配置内容
    tftp_root = Column(String(500), nullable=True)  # TFTP 根目录
    ipxe_menu = Column(Text, nullable=True)  # iPXE 菜单脚本
    dhcp_config = Column(Text, nullable=True)  # DHCP 配置
    mac_filters = Column(Text, nullable=True)  # MAC 地址过滤 (JSON)
    status = Column(String(20), nullable=False, default="disabled")  # enabled/disabled
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    node = relationship("Node", back_populates="pxe_configs")

    def __repr__(self):
        return f"<PxeConfig(id={self.id}, node_id={self.node_id}, status='{self.status}')>"


class IsoImage(Base):
    """ISO 镜像管理"""

    __tablename__ = "iso_image"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    local_path = Column(String(1000), nullable=False)
    size = Column(Integer, nullable=True)  # 文件大小 (字节)
    arch = Column(String(20), nullable=False, default="x86_64")  # x86_64/arm64
    node_id = Column(Integer, ForeignKey("node.id"), nullable=True)
    status = Column(String(20), nullable=False, default="available")  # available/active
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    node = relationship("Node", back_populates="iso_images")
    install_tasks = relationship("InstallTask", back_populates="iso")

    def __repr__(self):
        return f"<IsoImage(id={self.id}, name='{self.name}', arch='{self.arch}')>"


class InstallTask(Base):
    """系统安装任务"""

    __tablename__ = "install_task"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    host_id = Column(Integer, ForeignKey("host.id"), nullable=True)
    iso_id = Column(Integer, ForeignKey("iso_image.id"), nullable=True)
    template_id = Column(Integer, ForeignKey("template.id"), nullable=True)
    node_id = Column(Integer, ForeignKey("node.id"), nullable=True)
    status = Column(
        String(20), nullable=False, default="pending"
    )  # pending/running/completed/failed
    progress = Column(Integer, nullable=False, default=0)  # 0-100
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    log_path = Column(String(1000), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    host = relationship("Host", back_populates="install_tasks")
    iso = relationship("IsoImage", back_populates="install_tasks")
    template = relationship("Template", back_populates="install_tasks")
    node = relationship("Node", back_populates="install_tasks")
    reports = relationship("InstallReport", back_populates="task")

    def __repr__(self):
        return f"<InstallTask(id={self.id}, host_id={self.host_id}, status='{self.status}')>"


class InstallReport(Base):
    """安装结果报告"""

    __tablename__ = "install_report"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("install_task.id"), nullable=True)
    result = Column(String(20), nullable=False, default="failed")  # success/failed
    duration = Column(Integer, nullable=True)  # 安装耗时 (秒)
    error_details = Column(Text, nullable=True)
    report_content = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # 关联
    task = relationship("InstallTask", back_populates="reports")

    def __repr__(self):
        return f"<InstallReport(id={self.id}, task_id={self.task_id}, result='{self.result}')>"


class FileInfo(Base):
    """文件管理"""

    __tablename__ = "file_info"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    type = Column(String(20), nullable=False)  # script/config/repo
    path = Column(String(1000), nullable=False)
    size = Column(Integer, nullable=True)  # 文件大小 (字节)
    category = Column(String(100), nullable=True)
    sync_status = Column(
        String(20), nullable=False, default="pending"
    )  # synced/pending
    node_id = Column(Integer, ForeignKey("node.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    node = relationship("Node", back_populates="file_infos")

    def __repr__(self):
        return f"<FileInfo(id={self.id}, name='{self.name}', type='{self.type}')>"


class Template(Base):
    """安装模板 (Preseed/Kickstart)"""

    __tablename__ = "template"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    type = Column(String(20), nullable=False)  # user-data/kickstart/preseed
    content = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    defaults = Column(Text, nullable=True)  # JSON 默认参数
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关联
    install_tasks = relationship("InstallTask", back_populates="template")

    def __repr__(self):
        return f"<Template(id={self.id}, name='{self.name}', type='{self.type}')>"


class User(Base):
    """系统用户"""

    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="readonly")  # admin/operator/readonly
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, nullable=True)

    @property
    def password(self) -> str:
        """返回空字符串 (密码哈希不可逆)"""
        return ""

    @password.setter
    def password(self, value: str):
        """设置密码并自动哈希"""
        if value:
            self.password_hash = pwd_context.hash(value)

    def verify_password(self, plain_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, self.password_hash)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"
