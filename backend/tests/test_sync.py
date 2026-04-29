"""文件同步逻辑测试"""
import os
from unittest.mock import patch

import pytest
import tempfile
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.exceptions import PxeException
from app.filemgr.sync import sync_to_agent, _md5
from app.models import FileInfo, Node
from app.database import Base

test_engine = create_engine(
    "sqlite:///file::memory:?cache=shared",
    connect_args={"check_same_thread": False},
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

from app import models  # noqa: F401


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    with test_engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        for table in Base.metadata.tables.values():
            conn.execute(text(f'DELETE FROM "{table.name}"'))
        conn.execute(text("PRAGMA foreign_keys=ON"))


class TestMD5:
    def test_md5_known_content(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello")
            fpath = f.name
        try:
            assert _md5(fpath) == "5d41402abc4b2a76b9719d911017c592"
        finally:
            os.unlink(fpath)


class TestSyncToAgent:
    def test_node_not_found(self):
        db = TestSession()
        with pytest.raises(PxeException) as exc:
            sync_to_agent([], 999, db=db)
        assert exc.value.code == "NODE_NOT_FOUND"
        db.close()

    def test_sync_with_no_files(self):
        db = TestSession()
        node = Node(hostname="agent1", ip="10.0.0.1", mode="agent")
        db.add(node)
        db.commit()
        nid = node.id
        with patch("app.filemgr.sync.exec_command", return_value={"stdout": "", "exit_code": 0}):
            result = sync_to_agent([], nid, db=db)
        assert result["synced"] == 0
        assert result["total"] == 0
        db.close()

    def test_sync_skips_missing_files(self):
        db = TestSession()
        node = Node(hostname="agent1", ip="10.0.0.1", mode="agent")
        db.add(node)
        db.commit()
        nid = node.id
        fi = FileInfo(name="x.sh", type="script", path="script/x.sh", category="script")
        db.add(fi)
        db.commit()
        fid = fi.id
        with (
            patch("app.filemgr.sync.exec_command", return_value={"stdout": "", "exit_code": 0}),
            patch("os.path.exists", return_value=False),
        ):
            result = sync_to_agent([fid], nid, db=db)
        assert result["synced"] == 0
        assert result["total"] == 1
        db.close()
