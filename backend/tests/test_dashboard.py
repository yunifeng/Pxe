"""仪表盘聚合 API 测试"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.auth.jwt_handler import create_token
from app.database import Base, get_db
from app.main import app
from app.models import BmcInfo, Host, InstallTask, Node

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


class TestDashboardAPI:
    """仪表盘聚合数据验证"""

    def test_dashboard_empty_data(self):
        token = _admin_token()
        with patch("app.api.dashboard.is_active", return_value=False):
            resp = client.get("/api/v1/dashboard/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["nodes"]["total"] == 0
        assert data["hosts"]["total"] == 0
        assert data["bmc"]["total"] == 0
        assert "services" in data
        assert "recent_tasks" in data
        assert "quick_actions" in data

    def test_dashboard_node_stats(self):
        token = _admin_token()
        db = TestSession()
        db.add(Node(hostname="m1", ip="10.0.0.1", mode="master", status="online"))
        db.add(Node(hostname="a1", ip="10.0.0.2", mode="agent", status="online"))
        db.add(Node(hostname="a2", ip="10.0.0.3", mode="agent", status="offline"))
        db.commit()
        db.close()
        with patch("app.api.dashboard.is_active", return_value=True):
            resp = client.get("/api/v1/dashboard/", headers={"Authorization": f"Bearer {token}"})
        data = resp.json()["data"]
        assert data["nodes"]["total"] == 3
        assert data["nodes"]["online"] == 2
        assert data["nodes"]["offline"] == 1

    def test_dashboard_host_stats(self):
        token = _admin_token()
        db = TestSession()
        db.add(Host(hostname="h1", deploy_status="pending"))
        db.add(Host(hostname="h2", deploy_status="installing"))
        db.add(Host(hostname="h3", deploy_status="running"))
        db.add(Host(hostname="h4", deploy_status="failed"))
        db.commit()
        db.close()
        with patch("app.api.dashboard.is_active", return_value=False):
            resp = client.get("/api/v1/dashboard/", headers={"Authorization": f"Bearer {token}"})
        data = resp.json()["data"]
        assert data["hosts"]["total"] == 4
        assert data["hosts"]["pending"] == 1
        assert data["hosts"]["installing"] == 1
        assert data["hosts"]["running"] == 1
        assert data["hosts"]["failed"] == 1

    def test_dashboard_bmc_stats(self):
        token = _admin_token()
        db = TestSession()
        db.add(BmcInfo(hostname="b1", bmc_ip="10.0.0.1", username="admin", protocol="redfish", power_status="on"))
        db.add(BmcInfo(hostname="b2", bmc_ip="10.0.0.2", username="admin", protocol="ipmi", power_status="off"))
        db.add(BmcInfo(hostname="b3", bmc_ip="10.0.0.3", username="admin", protocol="redfish", power_status="unknown"))
        db.commit()
        db.close()
        with patch("app.api.dashboard.is_active", return_value=False):
            resp = client.get("/api/v1/dashboard/", headers={"Authorization": f"Bearer {token}"})
        data = resp.json()["data"]
        assert data["bmc"]["total"] == 3
        assert data["bmc"]["on"] == 1
        assert data["bmc"]["off"] == 1
        assert data["bmc"]["unknown"] == 1

    def test_dashboard_recent_tasks(self):
        token = _admin_token()
        db = TestSession()
        for i in range(3):
            db.add(InstallTask(status="completed", progress=100))
        db.commit()
        db.close()
        with patch("app.api.dashboard.is_active", return_value=False):
            resp = client.get("/api/v1/dashboard/", headers={"Authorization": f"Bearer {token}"})
        data = resp.json()["data"]
        assert len(data["recent_tasks"]) == 3

    def test_readonly_can_access_dashboard(self):
        token = _readonly_token()
        with patch("app.api.dashboard.is_active", return_value=False):
            resp = client.get("/api/v1/dashboard/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_dashboard_requires_auth(self):
        resp = client.get("/api/v1/dashboard/")
        assert resp.status_code in (401, 403)
