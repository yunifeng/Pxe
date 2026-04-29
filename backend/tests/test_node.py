"""节点管理测试"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.auth.jwt_handler import create_token
from app.database import Base, get_db
from app.exceptions import PxeException
from app.main import app
from app.models import Node

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


class TestNodeCRUD:
    """节点 CRUD 测试"""

    def test_add_node(self):
        token = _admin_token()
        resp = client.post(
            "/api/v1/node/",
            json={"hostname": "agent01", "ip": "10.0.0.10", "mode": "agent"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["hostname"] == "agent01"

    def test_list_nodes(self):
        token = _admin_token()
        client.post("/api/v1/node/", json={"hostname": "agent01", "ip": "10.0.0.10"}, headers={"Authorization": f"Bearer {token}"})
        resp = client.get("/api/v1/node/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_list_nodes_with_status_filter(self):
        token = _admin_token()
        db = TestSession()
        node = Node(hostname="test", ip="10.0.0.10", mode="agent", status="online")
        db.add(node)
        db.commit()
        db.close()
        resp = client.get("/api/v1/node/?status=online", headers={"Authorization": f"Bearer {token}"})
        assert len(resp.json()["data"]) == 1

    def test_remove_node(self):
        token = _admin_token()
        client.post("/api/v1/node/", json={"hostname": "agent01", "ip": "10.0.0.10"}, headers={"Authorization": f"Bearer {token}"})
        resp = client.get("/api/v1/node/", headers={"Authorization": f"Bearer {token}"})
        node_id = resp.json()["data"][0]["id"]
        resp = client.delete(f"/api/v1/node/{node_id}", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_get_ssh_info(self):
        token = _admin_token()
        client.post("/api/v1/node/", json={"hostname": "agent01", "ip": "10.0.0.10"}, headers={"Authorization": f"Bearer {token}"})
        resp = client.get("/api/v1/node/", headers={"Authorization": f"Bearer {token}"})
        node_id = resp.json()["data"][0]["id"]
        resp = client.get(f"/api/v1/node/{node_id}/ssh", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["data"]["host"] == "10.0.0.10"

    def test_node_requires_auth(self):
        resp = client.get("/api/v1/node/")
        assert resp.status_code in (401, 403)


class TestNodeMonitor:
    """节点状态检测逻辑测试"""

    def test_check_node_offline(self):
        db = TestSession()
        node = Node(hostname="test", ip="10.0.0.10", mode="agent", status="online")
        db.add(node)
        db.commit()
        db.refresh(node)
        from app.node.monitor import check_node_status
        result = check_node_status(node, fail_count=2)
        assert result["status"] == "offline"
        db.close()
