"""PXE API 端点集成测试"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.auth.jwt_handler import create_token
from app.database import Base, get_db
from app.main import app
from app.models import User

# 测试数据库
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


def _readonly_token():
    return create_token(user_id=2, role="readonly")


class TestPxeAuth:
    """PXE 路由权限测试"""

    def test_readonly_cannot_access_pxe_config(self):
        db = TestSession()
        user = User(username="viewer", role="readonly")
        user.password = "pass"
        db.add(user)
        db.commit()
        db.close()
        resp = client.post("/api/v1/auth/login", json={"username": "viewer", "password": "pass"})
        assert resp.status_code == 200
        token = resp.json()["data"]["token"]
        resp = client.get("/api/v1/pxe/config", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_admin_can_access_pxe_config(self):
        token = _admin_token()
        with patch("app.pxe.dnsmasq.get_config", return_value="# empty\n"):
            resp = client.get("/api/v1/pxe/config", headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200


class TestTasksAPI:
    """安装任务 API 集成测试"""

    def test_create_task(self):
        token = _admin_token()
        resp = client.post(
            "/api/v1/pxe/tasks",
            json={"host_id": 1, "iso_id": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["status"] == "pending"

    def test_list_tasks(self):
        token = _admin_token()
        client.post("/api/v1/pxe/tasks", json={"host_id": 1, "iso_id": 1}, headers={"Authorization": f"Bearer {token}"})
        resp = client.get("/api/v1/pxe/tasks", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_get_task_not_found(self):
        token = _admin_token()
        resp = client.get("/api/v1/pxe/tasks/999", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400

    def test_retry_nonexistent_task(self):
        token = _admin_token()
        resp = client.post("/api/v1/pxe/tasks/999/retry", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400
