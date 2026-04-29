"""
WebSocket 实时通信模块
"""
import json
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app.utils.logs import setup_logging

logger = setup_logging()


class WebSocketManager:
    """管理所有 WebSocket 连接"""

    def __init__(self):
        # user_id -> set of WebSocket connections
        self.active_connections: dict[str, set] = {}

    def connect(self, user_id: str, websocket: WebSocket):
        """注册一个 WebSocket 连接"""
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected: user={user_id}, total={len(self.active_connections.get(user_id, set()))}")

    def disconnect(self, user_id: str, websocket: WebSocket):
        """移除一个 WebSocket 连接"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected: user={user_id}")

    async def _send(self, websocket: WebSocket, event_type: str, data: Any):
        """通过单个 WebSocket 发送消息"""
        message = {"type": event_type, "data": data}
        try:
            await websocket.send_json(message)
        except Exception:
            logger.warning(f"Failed to send message to WebSocket: type={event_type}")

    async def broadcast(self, event_type: str, data: Any):
        """广播消息给所有已连接的客户端"""
        message = {"type": event_type, "data": data}
        to_remove = []
        for user_id, connections in list(self.active_connections.items()):
            for ws in list(connections):
                try:
                    await ws.send_json(message)
                except Exception:
                    to_remove.append((user_id, ws))
        for user_id, ws in to_remove:
            self.disconnect(user_id, ws)

    async def send_to(self, user_id: str, event_type: str, data: Any):
        """发送消息给指定用户的所有连接"""
        connections = self.active_connections.get(user_id)
        if not connections:
            logger.warning(f"No active connections for user={user_id}")
            return
        message = {"type": event_type, "data": data}
        to_remove = []
        for ws in list(connections):
            try:
                await ws.send_json(message)
            except Exception:
                to_remove.append(ws)
        for ws in to_remove:
            self.disconnect(user_id, ws)


# 全局单例
ws_manager = WebSocketManager()


# ---------------------------------------------------------------------------
# WebSocket 端点
# ---------------------------------------------------------------------------

async def _accept_and_register(websocket: WebSocket, scope: str):
    """接受连接并注册到管理器中"""
    await websocket.accept()
    user_id = websocket.query_params.get("user_id", "anonymous")
    ws_manager.connect(user_id, websocket)
    try:
        while True:
            # 保持连接 alive，接收客户端消息（可用于心跳）
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                logger.debug(f"WS [{scope}] received from user={user_id}: {msg}")
            except json.JSONDecodeError:
                logger.warning(f"WS [{scope}] invalid JSON from user={user_id}")
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id, websocket)
    except Exception:
        logger.exception(f"WS [{scope}] error for user={user_id}")
        ws_manager.disconnect(user_id, websocket)


async def ws_endpoint(websocket: WebSocket):
    """通用认证 WebSocket 端点 - /ws"""
    await _accept_and_register(websocket, "ws")


async def ws_tasks(websocket: WebSocket):
    """安装任务进度 WebSocket - /ws/tasks"""
    await _accept_and_register(websocket, "ws/tasks")


async def ws_bmc(websocket: WebSocket):
    """BMC 批量操作结果 WebSocket - /ws/bmc"""
    await _accept_and_register(websocket, "ws/bmc")


async def ws_services(websocket: WebSocket):
    """服务状态变更 WebSocket - /ws/services"""
    await _accept_and_register(websocket, "ws/services")


# ---------------------------------------------------------------------------
# 业务流通知辅助函数
# ---------------------------------------------------------------------------

async def notify_task_update(task_id: str, status: str, progress: int):
    """广播安装任务状态变更"""
    await ws_manager.broadcast("task_update", {
        "task_id": task_id,
        "status": status,
        "progress": progress,
    })


async def notify_bmc_result(bmc_id: str, success: bool, error: str = None):
    """广播 BMC 操作结果"""
    await ws_manager.broadcast("bmc_result", {
        "bmc_id": bmc_id,
        "success": success,
        "error": error,
    })


async def notify_service_change(service_name: str, active: bool):
    """广播服务状态变更"""
    await ws_manager.broadcast("service_change", {
        "service_name": service_name,
        "active": active,
    })
