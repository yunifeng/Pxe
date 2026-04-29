"""
PXE Manager - FastAPI 应用入口
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.routing import WebSocketRoute

from app.config import settings
from app.database import init_db
from app.exceptions import (
    PxeException,
    pxe_exception_handler,
    not_found_handler,
    server_error_handler,
)
from app.utils.logs import setup_logging

# 初始化日志
logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """应用生命周期管理"""
    # 启动事件
    logger.info("PXE Manager 启动中...")
    init_db()
    logger.info("数据库初始化完成")
    yield
    # 关闭事件
    logger.info("PXE Manager 正在关闭...")


# 创建 FastAPI 应用
app = FastAPI(
    title="PXE Manager",
    version="0.1.0",
    description="PXE 网络启动管理系统 - 支持 Master/Agent 架构",
    lifespan=lifespan,
)

# CORS 中间件 (允许前端访问)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册异常处理器
app.add_exception_handler(PxeException, pxe_exception_handler)
app.add_exception_handler(404, not_found_handler)
app.add_exception_handler(Exception, server_error_handler)


@app.get("/")
async def root():
    """根端点 - 健康检查"""
    return {
        "name": "PXE Manager",
        "version": "0.1.0",
    }


if app.debug:

    @app.get("/api/v1/test-raise-exception")
    async def test_raise_exception():
        """测试端点 - 触发 PxeException (仅 debug 模式)"""
        raise PxeException(
            code="TEST_ERROR",
            message="这是一个测试异常",
            status_code=400,
        )


# API 路由前缀
from app.api import router as api_router  # noqa: E402
from app.api.auth import auth_router  # noqa: E402
from app.api.pxe import pxe_router  # noqa: E402
from app.api.bmc import bmc_router  # noqa: E402
from app.api.node import node_router  # noqa: E402
from app.api.host import host_router  # noqa: E402
from app.api.filemgr import filemgr_router  # noqa: E402
from app.api.template import template_router  # noqa: E402
from app.api.dashboard import dashboard_router  # noqa: E402

app.include_router(api_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(pxe_router, prefix="/api/v1/pxe")
app.include_router(bmc_router, prefix="/api/v1/bmc")
app.include_router(node_router, prefix="/api/v1/node")
app.include_router(host_router, prefix="/api/v1/host")
app.include_router(filemgr_router, prefix="/api/v1/file")
app.include_router(template_router, prefix="/api/v1/template")
app.include_router(dashboard_router, prefix="/api/v1/dashboard")

# WebSocket 实时通信端点
from app.ws import ws_endpoint, ws_tasks, ws_bmc, ws_services  # noqa: E402

app.routes.append(WebSocketRoute("/ws", ws_endpoint))
app.routes.append(WebSocketRoute("/ws/tasks", ws_tasks))
app.routes.append(WebSocketRoute("/ws/bmc", ws_bmc))
app.routes.append(WebSocketRoute("/ws/services", ws_services))
