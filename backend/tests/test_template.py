"""配置模板 API 端点集成测试"""
from unittest.mock import patch

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


def _preseed_test_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


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


class TestTemplateAPI:
    """模板 API 端点集成测试"""

    def setup_method(self):
        self._patcher = patch("app.template.preseed.get_db", side_effect=_preseed_test_get_db)
        self._patcher.start()

    def teardown_method(self):
        self._patcher.stop()

    def test_create_template(self):
        token = _admin_token()
        resp = client.post(
            "/api/v1/template/",
            json={
                "name": "Custom Preseed",
                "type": "preseed",
                "content": "d-i partman-auto/method string regular",
                "defaults": {"hostname": "host01"},
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Custom Preseed"

    def test_list_templates(self):
        token = _admin_token()
        client.post(
            "/api/v1/template/",
            json={"name": "T1", "type": "preseed", "content": "x"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = client.get("/api/v1/template/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_get_template(self):
        token = _admin_token()
        create_resp = client.post(
            "/api/v1/template/",
            json={"name": "T2", "type": "kickstart", "content": "%packages"},
            headers={"Authorization": f"Bearer {token}"},
        )
        tid = create_resp.json()["data"]["id"]
        resp = client.get(f"/api/v1/template/{tid}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["data"]["type"] == "kickstart"

    def test_update_template(self):
        token = _admin_token()
        create_resp = client.post(
            "/api/v1/template/",
            json={"name": "Old", "type": "preseed", "content": "x"},
            headers={"Authorization": f"Bearer {token}"},
        )
        tid = create_resp.json()["data"]["id"]
        resp = client.put(
            f"/api/v1/template/{tid}",
            json={"name": "New"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "New"

    def test_delete_template(self):
        token = _admin_token()
        create_resp = client.post(
            "/api/v1/template/",
            json={"name": "Del", "type": "preseed", "content": "x"},
            headers={"Authorization": f"Bearer {token}"},
        )
        tid = create_resp.json()["data"]["id"]
        resp = client.delete(f"/api/v1/template/{tid}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        resp = client.get(f"/api/v1/template/{tid}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400

    def test_render_template(self):
        token = _admin_token()
        create_resp = client.post(
            "/api/v1/template/",
            json={"name": "R", "type": "preseed", "content": "Host: {name}"},
            headers={"Authorization": f"Bearer {token}"},
        )
        tid = create_resp.json()["data"]["id"]
        resp = client.post(
            f"/api/v1/template/{tid}/render",
            json={"variables": {"name": "srv01"}},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert "srv01" in resp.json()["data"]["content"]

    def test_operator_cannot_access_template(self):
        token = _operator_token()
        resp = client.get("/api/v1/template/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_requires_auth(self):
        resp = client.get("/api/v1/template/")
        assert resp.status_code in (401, 403)
