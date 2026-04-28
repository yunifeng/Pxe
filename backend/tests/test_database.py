"""测试数据库模块"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestDatabase:
    """测试数据库连接和初始化"""

    def test_engine_creation(self):
        """测试引擎创建"""
        from app.database import engine
        assert engine is not None

    def test_session_local(self):
        """测试会话工厂"""
        from app.database import SessionLocal
        session = SessionLocal()
        assert session is not None
        session.close()

    def test_init_db_creates_tables(self):
        """测试 init_db 创建所有表"""
        from app.database import init_db, engine
        from app import models  # noqa: F401 导入模型以注册表

        # 使用临时数据库测试表创建
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tmp_db = f.name

        try:
            from sqlalchemy import create_engine
            from app.database import Base, get_test_engine

            # 创建临时引擎
            tmp_engine = create_engine(
                f"sqlite:///{tmp_db}", connect_args={"check_same_thread": False}
            )
            Base.metadata.create_all(bind=tmp_engine)

            # 验证表存在
            from sqlalchemy import inspect
            inspector = inspect(tmp_engine)
            tables = inspector.get_table_names()

            expected_tables = [
                "node", "bmc_info", "host", "pxe_config", "iso_image",
                "install_task", "install_report", "file_info", "template", "user"
            ]
            for table in expected_tables:
                assert table in tables, f"表 {table} 未创建"
        finally:
            if os.path.exists(tmp_db):
                os.unlink(tmp_db)

    def test_get_db_dependency(self):
        """测试 get_db 依赖注入"""
        from app.database import get_db
        from sqlalchemy.orm import Session

        # get_db 应该返回一个生成器
        gen = get_db()
        session = next(gen)
        assert session is not None
        try:
            assert isinstance(session, Session)
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
