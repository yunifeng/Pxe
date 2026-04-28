"""测试错误处理"""
import asyncio


class TestPxeException:
    """测试 PxeException 类"""

    def test_exception_default_code(self):
        """测试异常默认错误码"""
        from app.exceptions import PxeException
        exc = PxeException(code="INTERNAL_ERROR", message="test error")
        assert exc.message == "test error"
        assert exc.code == "INTERNAL_ERROR"

    def test_exception_custom_code(self):
        """测试异常自定义错误码"""
        from app.exceptions import PxeException
        exc = PxeException(code="NOT_FOUND", message="not found")
        assert exc.code == "NOT_FOUND"
        assert exc.message == "not found"


class TestErrorHandlers:
    """测试错误处理器"""

    def test_pxe_exception_handler(self):
        """测试 PxeException 异常处理器返回格式"""
        from app.exceptions import PxeException, pxe_exception_handler

        async def _run():
            exc = PxeException(
                code="TEST_ERROR",
                message="这是一个测试异常",
                status_code=400,
            )
            response = await pxe_exception_handler(None, exc)
            assert response.status_code == 400
            data = response.body
            import json

            data = json.loads(data)
            assert data["success"] is False
            assert data["error"]["code"] == "TEST_ERROR"
            assert "测试异常" in data["error"]["message"]

        asyncio.run(_run())

    def test_root_endpoint(self):
        """测试根端点"""
        from app.main import app
        from httpx import AsyncClient, ASGITransport

        async def _run():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/")
                assert response.status_code == 200
                data = response.json()
                assert data["name"] == "PXE Manager"
                assert data["version"] == "0.1.0"

        asyncio.run(_run())

    def test_404_handler(self):
        """测试 404 处理器"""
        from app.main import app
        from httpx import AsyncClient, ASGITransport

        async def _run():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/nonexistent-path")
                assert response.status_code == 404

        asyncio.run(_run())
