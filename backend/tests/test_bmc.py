"""BMC 管理测试"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.auth.jwt_handler import create_token
from app.database import Base, get_db
from app.exceptions import PxeException
from app.main import app
from app.models import BmcInfo

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


class TestIPMIHandler:
    """IPMI 操作 Mock 测试"""

    def test_missing_dependency_raises(self):
        from app.bmc import ipmi_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        with patch.object(ipmi_handler, "IPMI_CONNECT_TIMEOUT", 10):
            with pytest.raises(PxeException) as exc:
                ipmi_handler.get_power_status(info)
            assert exc.value.code in ("MISSING_DEPENDENCY", "IPMI_CONNECT_ERROR")


class TestBmcAPI:
    """BMC API 端点集成测试"""

    def test_add_bmc(self):
        token = _admin_token()
        resp = client.post(
            "/api/v1/bmc/",
            json={
                "hostname": "srv01",
                "bmc_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "protocol": "redfish",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["hostname"] == "srv01"

    def test_list_bmcs(self):
        token = _admin_token()
        client.post(
            "/api/v1/bmc/",
            json={
                "hostname": "srv01",
                "bmc_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "protocol": "redfish",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = client.get("/api/v1/bmc/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_batch_add(self):
        token = _admin_token()
        resp = client.post(
            "/api/v1/bmc/batch",
            json={"csv_data": "srv01,10.0.0.1,admin,pass,redfish\nsrv02,10.0.0.2,admin,pass,ipmi"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["added"] == 2

    def test_bmc_stats(self):
        token = _admin_token()
        resp = client.get("/api/v1/bmc/stats", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total" in data
        assert "on" in data
        assert "off" in data

    def test_bmc_requires_auth(self):
        resp = client.get("/api/v1/bmc/")
        assert resp.status_code in (401, 403)
