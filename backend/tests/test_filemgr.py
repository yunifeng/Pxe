"""文件管理 API 端点集成测试"""
from unittest.mock import patch, mock_open

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.auth.jwt_handler import create_token
from app.database import Base, get_db
from app.main import app

test_engine = create_engine(
    "sqlite:///file::memory:?cache=shared",
    connect_args={"check_same_thread": False},
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

from app import models  # noqa: F401


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    with test_engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        for table in Base.metadata.tables.values():
            conn.execute(text(f'DELETE FROM "{table.name}"'))
        conn.execute(text("PRAGMA foreign_keys=ON"))


client = TestClient(app)


def _admin_token():
    return create_token(user_id=1, role="admin")


class TestFileAPI:
    """文件管理 API 端点集成测试"""

    def test_list_files_empty(self):
        token = _admin_token()
        with patch("app.filemgr.repo.list_files", return_value=[]):
            resp = client.get("/api/v1/file/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_list_files_with_category(self):
        token = _admin_token()
        mock_files = [{"id": 1, "name": "a.sh", "category": "script"}]
        with patch("app.filemgr.repo.list_files", return_value=mock_files):
            resp = client.get(
                "/api/v1/file/?category=script",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_upload_file(self):
        token = _admin_token()
        with (
            patch("app.filemgr.repo.upload_file", return_value={"id": 1, "name": "test.sh"}),
            patch("builtins.open", mock_open(read_data=b"echo hi")),
        ):
            resp = client.post(
                "/api/v1/file/upload?category=script",
                files={"file": ("test.sh", b"echo hi", "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "test.sh"

    def test_remove_file(self):
        token = _admin_token()
        with patch("app.filemgr.repo.remove_file"):
            resp = client.delete(
                "/api/v1/file/1",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200

    def test_sync_files(self):
        token = _admin_token()
        with patch("app.filemgr.sync.sync_to_agent", return_value={"synced": 2, "total": 2}):
            resp = client.post(
                "/api/v1/file/sync?node_id=1",
                json=[1, 2],
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        assert resp.json()["data"]["synced"] == 2

    def test_file_requires_auth(self):
        resp = client.get("/api/v1/file/")
        assert resp.status_code in (401, 403)

    def test_readonly_cannot_upload(self):
        token = create_token(user_id=2, role="readonly")
        with patch("builtins.open", mock_open(read_data=b"")):
            resp = client.post(
                "/api/v1/file/upload?category=script",
                files={"file": ("x.sh", b"", "text/plain")},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403
