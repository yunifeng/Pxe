"""主机管理测试"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.auth.jwt_handler import create_token
from app.database import Base, get_db
from app.exceptions import PxeException
from app.main import app
from app.models import BmcInfo, Host, Node

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


def _operator_token():
    return create_token(user_id=2, role="operator")


def _readonly_token():
    return create_token(user_id=3, role="readonly")


class TestHostCRUD:
    """主机 CRUD API 测试"""

    def test_add_host(self):
        token = _admin_token()
        resp = client.post(
            "/api/v1/host/",
            json={"hostname": "srv01", "ip": "10.0.0.1", "mac_address": "AA:BB:CC:DD:EE:01"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["hostname"] == "srv01"

    def test_list_hosts(self):
        token = _admin_token()
        client.post(
            "/api/v1/host/",
            json={"hostname": "srv01", "ip": "10.0.0.1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = client.get("/api/v1/host/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_list_hosts_filter_status(self):
        token = _admin_token()
        client.post(
            "/api/v1/host/",
            json={"hostname": "srv01", "ip": "10.0.0.1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = client.get(
            "/api/v1/host/?status=pending",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert len(resp.json()["data"]) == 1
        resp = client.get(
            "/api/v1/host/?status=running",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert len(resp.json()["data"]) == 0

    def test_remove_host(self):
        token = _admin_token()
        add_resp = client.post(
            "/api/v1/host/",
            json={"hostname": "srv01", "ip": "10.0.0.1"},
            headers={"Authorization": f"Bearer {token}"},
        )
        host_id = add_resp.json()["data"]["id"]
        resp = client.delete(f"/api/v1/host/{host_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_remove_nonexistent_host(self):
        token = _admin_token()
        resp = client.delete("/api/v1/host/999", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400

    def test_readonly_can_list_hosts(self):
        token = _readonly_token()
        resp = client.get("/api/v1/host/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_readonly_cannot_add_host(self):
        token = _readonly_token()
        resp = client.post(
            "/api/v1/host/",
            json={"hostname": "srv01"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_readonly_cannot_delete_host(self):
        token = _readonly_token()
        resp = client.delete("/api/v1/host/1", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


class TestHardwareInfo:
    """硬件清单 API 测试"""

    def test_get_hardware(self):
        token = _admin_token()
        db = TestSession()
        host = Host(hostname="srv01", ip="10.0.0.1")
        db.add(host)
        db.commit()
        host_id = host.id
        db.close()
        with patch("app.host.inventory.exec_command", return_value={"stdout": "{}", "exit_code": 0}):
            resp = client.get(f"/api/v1/host/{host_id}/hardware", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "cpu" in resp.json()["data"]

    def test_get_hardware_missing_ip(self):
        token = _admin_token()
        db = TestSession()
        host = Host(hostname="srv01")
        db.add(host)
        db.commit()
        host_id = host.id
        db.close()
        resp = client.get(f"/api/v1/host/{host_id}/hardware", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400
        assert "MISSING_IP" in resp.json()["error"]["code"]

    def test_get_hardware_not_found(self):
        token = _admin_token()
        resp = client.get("/api/v1/host/999/hardware", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400


class TestAnsibleAPI:
    """Ansible API 测试"""

    def test_run_ansible(self):
        token = _admin_token()
        db = TestSession()
        host = Host(hostname="srv01", ip="10.0.0.1")
        db.add(host)
        db.commit()
        host_id = host.id
        db.close()
        with patch("app.host.ansible.run_playbook", return_value="ok"):
            resp = client.post(
                f"/api/v1/host/{host_id}/ansible?playbook=/opt/play.yml",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        assert resp.json()["data"]["output"] == "ok"

    def test_operator_can_run_ansible(self):
        token = _operator_token()
        db = TestSession()
        host = Host(hostname="srv01", ip="10.0.0.1")
        db.add(host)
        db.commit()
        host_id = host.id
        db.close()
        with patch("app.host.ansible.run_playbook", return_value="ok"):
            resp = client.post(
                f"/api/v1/host/{host_id}/ansible?playbook=/opt/play.yml",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200


class TestSSHAPI:
    """SSH 连接信息 API 测试"""

    def test_get_ssh_info(self):
        token = _admin_token()
        db = TestSession()
        host = Host(hostname="srv01", ip="10.0.0.1")
        db.add(host)
        db.commit()
        host_id = host.id
        db.close()
        resp = client.post(f"/api/v1/host/{host_id}/ssh", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["host"] == "10.0.0.1"
        assert data["port"] == 22

    def test_host_requires_ip_for_ssh(self):
        token = _admin_token()
        db = TestSession()
        host = Host(hostname="srv01")
        db.add(host)
        db.commit()
        host_id = host.id
        db.close()
        resp = client.post(f"/api/v1/host/{host_id}/ssh", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400
