"""Pytest 配置 - 异步测试支持"""


def pytest_configure(config):
    """配置 pytest 使用 asyncio 事件循环"""
    config.addinivalue_line("markers", "asyncio: mark test as async")
