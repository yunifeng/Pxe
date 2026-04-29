"""
数据库模块
SQLite 引擎、会话工厂、依赖注入
"""
import os
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


# 确保数据库目录存在
try:
    db_dir = os.path.dirname(settings.db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
except PermissionError:
    pass

# 数据库 URL
DATABASE_URL = "sqlite:///" + settings.db_path

# 创建引擎 (check_same_thread=False 允许跨线程使用连接)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,  # 连接前检测有效性
)

# 会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


def get_db() -> Generator[Session, None, None]:
    """
    数据库会话依赖注入
    使用 yield 确保请求结束后正确关闭会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库
    创建所有表，启用 WAL 模式优化写性能
    """
    # 导入所有模型以确保它们被注册到 Base.metadata
    from app import models  # noqa: F401

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    # 启用 WAL 模式提高并发写性能
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))


def get_test_engine(db_path: str = ":memory:"):
    """
    获取测试用引擎 (内存数据库)
    """
    return create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
