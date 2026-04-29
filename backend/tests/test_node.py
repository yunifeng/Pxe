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
from app.models import BmcInfo, Node

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


class TestAgentHandleStatus:
    """agent.handle_status 测试"""

    def test_handle_status_with_db(self):
        from app.node.agent import handle_status
        db = TestSession()
        node = Node(hostname="agent01", ip="10.0.0.10", mode="agent", status="online")
        db.add(node)
        db.commit()
        result = handle_status(db=db)
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["hostname"] == "agent01"
        db.close()

    def test_handle_status_empty(self):
        from app.node.agent import handle_status
        db = TestSession()
        result = handle_status(db=db)
        assert result["nodes"] == []
        db.close()


class TestAgentHandleBmcList:
    """agent.handle_bmc_list 测试"""

    def test_handle_bmc_list(self):
        from app.node.agent import handle_bmc_list
        db = TestSession()
        bmc = BmcInfo(
            hostname="srv01",
            bmc_ip="10.0.0.1",
            username="admin",
            password="pass",
            protocol="redfish",
        )
        db.add(bmc)
        db.commit()
        result = handle_bmc_list(db=db)
        assert len(result) == 1
        assert result[0]["hostname"] == "srv01"
        assert result[0]["protocol"] == "redfish"
        db.close()

    def test_handle_bmc_list_empty(self):
        from app.node.agent import handle_bmc_list
        db = TestSession()
        result = handle_bmc_list(db=db)
        assert result == []
        db.close()


class TestAgentHandleBmcPower:
    """agent.handle_bmc_power 测试"""

    def test_handle_bmc_power_ipmi(self):
        from app.node.agent import handle_bmc_power
        db = TestSession()
        bmc = BmcInfo(
            hostname="srv01",
            bmc_ip="10.0.0.1",
            username="admin",
            password="pass",
            protocol="ipmi",
        )
        db.add(bmc)
        db.commit()
        mock_handler = MagicMock()
        # Only mock the handler module import, not BmcInfo
        original_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

        def custom_import(name, *args, **kwargs):
            if name == "app.bmc.ipmi_handler":
                return mock_handler
            if name == "app.bmc.redfish_handler":
                return MagicMock()
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            result = handle_bmc_power(bmc.id, "on", db=db)
        assert result["success"] is True
        mock_handler.power_on.assert_called_once()
        db.close()

    def test_handle_bmc_power_not_found(self):
        from app.node.agent import handle_bmc_power
        db = TestSession()
        with pytest.raises(Exception) as exc:
            handle_bmc_power(99999, "on", db=db)
        assert "BMC not found" in str(exc.value)
        db.close()


class TestAgentHandleFileSync:
    """agent.handle_file_sync 测试"""

    def test_handle_file_sync(self):
        from app.node.agent import handle_file_sync
        from app.models import FileInfo
        db = TestSession()
        f = FileInfo(
            name="test.iso",
            type="script",
            path="/opt/pxe/files/test.iso",
            size=1024,
            sync_status="pending",
        )
        db.add(f)
        db.commit()
        result = handle_file_sync([f.id], db=db)
        assert result["synced"] == 1
        synced_file = db.get(FileInfo, f.id)
        assert synced_file.sync_status == "synced"
        db.close()

    def test_handle_file_sync_empty(self):
        from app.node.agent import handle_file_sync
        db = TestSession()
        result = handle_file_sync([], db=db)
        assert result["synced"] == 0
        db.close()


class TestAgentHandleLog:
    """agent.handle_log 测试"""

    def test_handle_log_file_exists(self, tmp_path):
        from app.node.agent import handle_log
        log_file = tmp_path / "pxe.log"
        log_file.write_text("line1\nline2\nline3\n")
        with patch("app.config.settings") as mock_settings:
            mock_settings.log_dir = str(tmp_path)
            result = handle_log(lines=2)
        assert "line2" in result
        assert "line3" in result

    def test_handle_log_file_not_found(self, tmp_path):
        from app.node.agent import handle_log
        with patch("app.config.settings") as mock_settings:
            mock_settings.log_dir = str(tmp_path)
            result = handle_log()
        assert result == ""


class TestAgentHandleInstallTask:
    """agent.handle_install_task 测试"""

    def test_handle_install_task_create(self):
        from app.node.agent import handle_install_task
        with patch("app.pxe.tasks.create_task") as mock_create:
            mock_create.return_value = {"id": 1, "status": "created"}
            result = handle_install_task(
                action="create",
                params={"host_id": 1, "iso_id": 2, "template_id": None, "node_id": None},
            )
        assert result["id"] == 1

    def test_handle_install_task_get(self):
        from app.node.agent import handle_install_task
        with patch("app.pxe.tasks.get_task") as mock_get:
            mock_get.return_value = {"id": 1, "status": "running"}
            result = handle_install_task(action="get", task_id=1)
        assert result["id"] == 1

    def test_handle_install_task_retry(self):
        from app.node.agent import handle_install_task
        with patch("app.pxe.tasks.retry_task") as mock_retry:
            mock_retry.return_value = {"id": 1, "status": "retrying"}
            result = handle_install_task(action="retry", task_id=1)
        assert result["id"] == 1

    def test_handle_install_task_unknown_action(self):
        from app.node.agent import handle_install_task
        with pytest.raises(Exception) as exc:
            handle_install_task(action="unknown")
        assert "Unknown action" in str(exc.value)
