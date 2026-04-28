"""Pytest 配置 - 异步测试支持"""
import asyncio
import pytest


def pytest_configure(config):
    """配置 pytest 使用 asyncio 事件循环"""
    config.addinivalue_line("markers", "asyncio: mark test as async")


@pytest.fixture
def event_loop():
    """为异步测试提供事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
