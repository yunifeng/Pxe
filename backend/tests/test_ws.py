"""WebSocket 测试"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

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


class TestWebSocketManager:
    """WebSocketManager 单元测试"""

    def setup_method(self):
        from app.ws import WebSocketManager
        self.manager = WebSocketManager()

    def test_connect_and_disconnect(self):
        ws = MagicMock()
        self.manager.connect("user1", ws)
        assert ws in self.manager.active_connections.get("user1", set())
        self.manager.disconnect("user1", ws)
        assert ws not in self.manager.active_connections.get("user1", set())

    def test_broadcast(self):
        import asyncio
        ws1 = MagicMock()
        ws2 = MagicMock()
        self.manager.connect("user1", ws1)
        self.manager.connect("user2", ws2)
        asyncio.run(self.manager.broadcast("status", {"ok": True}))
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()
        assert ws1.send_json.call_args[0][0]["type"] == "status"

    def test_broadcast_no_connections(self):
        import asyncio
        asyncio.run(self.manager.broadcast("event", {}))

    def test_send_to(self):
        import asyncio
        ws = MagicMock()
        self.manager.connect("user1", ws)
        asyncio.run(self.manager.send_to("user1", "test_event", {"key": "val"}))
        ws.send_json.assert_called_once_with(
            {"type": "test_event", "data": {"key": "val"}}
        )

    def test_send_to_nonexistent_user(self):
        import asyncio
        asyncio.run(self.manager.send_to("nobody", "event", {}))

    def test_disconnect_nonexistent(self):
        self.manager.disconnect("user1", MagicMock())


class TestHelperFunctions:
    """WebSocket 通知辅助函数测试"""

    def test_notify_task_update(self):
        import asyncio
        from app.ws import notify_task_update, ws_manager
        async def run():
            with patch.object(ws_manager, "broadcast", new_callable=AsyncMock) as mock_bc:
                await notify_task_update(1, "running", 50)
                call_args = mock_bc.call_args[0]
                assert call_args[0] == "task_update"
                assert call_args[1]["task_id"] == 1
                assert call_args[1]["status"] == "running"
        asyncio.run(run())

    def test_notify_bmc_result(self):
        import asyncio
        from app.ws import notify_bmc_result, ws_manager
        async def run():
            with patch.object(ws_manager, "broadcast", new_callable=AsyncMock) as mock_bc:
                await notify_bmc_result(1, True, None)
                call_args = mock_bc.call_args[0]
                assert call_args[0] == "bmc_result"
                assert call_args[1]["success"] is True
        asyncio.run(run())

    def test_notify_service_change(self):
        import asyncio
        from app.ws import notify_service_change, ws_manager
        async def run():
            with patch.object(ws_manager, "broadcast", new_callable=AsyncMock) as mock_bc:
                await notify_service_change("dnsmasq", True)
                call_args = mock_bc.call_args[0]
                assert call_args[0] == "service_change"
                assert call_args[1]["service_name"] == "dnsmasq"
        asyncio.run(run())


class TestWebSocketEndpoint:
    """WebSocket 端点集成测试"""

    def test_ws_general(self):
        with client.websocket_connect("/ws?user_id=1"):
            pass

    def test_ws_tasks(self):
        with client.websocket_connect("/ws/tasks?user_id=1"):
            pass

    def test_ws_bmc(self):
        with client.websocket_connect("/ws/bmc?user_id=1"):
            pass

    def test_ws_services(self):
        with client.websocket_connect("/ws/services?user_id=1"):
            pass
