"""
统一异常处理
"""
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class PxeException(HTTPException):
    """
    PXE 系统自定义异常

    Args:
        code: 错误代码 (用于前端识别错误类型)
        message: 错误消息 (用于展示给用户)
        status_code: HTTP 状态码 (默认 400)
    """

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
    ):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message


async def pxe_exception_handler(request: Request, exc: PxeException):
    """PxeException 异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        },
    )


async def not_found_handler(request: Request, exc: HTTPException):
    """404 异常处理器"""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": f"资源未找到: {request.url.path}",
            },
        },
    )


async def server_error_handler(request: Request, exc: Exception):
    """500 服务器错误处理器"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "服务器内部错误",
            },
        },
    )
