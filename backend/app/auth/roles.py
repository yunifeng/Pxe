"""
角色定义与权限检查模块
管理系统中的角色类型以及各角色的路由访问权限
"""
from enum import Enum


class Role(str, Enum):
    """用户角色枚举"""

    ADMIN = "admin"
    OPERATOR = "operator"
    READONLY = "readonly"


# 权限矩阵: (路由前缀, HTTP 方法) -> 允许的角色集合
# 注意: DELETE 方法仅允许 admin
PERMISSION_MATRIX: dict[tuple[str, str], set[str]] = {
    # 认证相关路由 - 所有角色可访问
    ("/auth", "GET"): {"admin", "operator", "readonly"},
    ("/auth", "POST"): {"admin", "operator", "readonly"},
    ("/auth", "DELETE"): {"admin"},
    # 仪表盘 - 所有角色可访问
    ("/dashboard", "GET"): {"admin", "operator", "readonly"},
    ("/dashboard", "POST"): {"admin", "operator", "readonly"},
    ("/dashboard", "DELETE"): {"admin"},
    # PXE 配置 - admin 和 operator
    ("/pxe", "GET"): {"admin", "operator"},
    ("/pxe", "POST"): {"admin", "operator"},
    ("/pxe", "DELETE"): {"admin"},
    # BMC 管理 - admin 和 operator
    ("/bmc", "GET"): {"admin", "operator"},
    ("/bmc", "POST"): {"admin", "operator"},
    ("/bmc", "DELETE"): {"admin"},
    # 节点管理 - 所有角色
    ("/node", "GET"): {"admin", "operator", "readonly"},
    ("/node", "POST"): {"admin", "operator", "readonly"},
    ("/node", "DELETE"): {"admin"},
    # 主机管理 - 所有角色
    ("/host", "GET"): {"admin", "operator", "readonly"},
    ("/host", "POST"): {"admin", "operator", "readonly"},
    ("/host", "DELETE"): {"admin"},
    # 文件管理 - admin 和 operator
    ("/file", "GET"): {"admin", "operator"},
    ("/file", "POST"): {"admin", "operator"},
    ("/file", "DELETE"): {"admin"},
    # 模板管理 - 仅 admin
    ("/template", "GET"): {"admin"},
    ("/template", "POST"): {"admin"},
    ("/template", "DELETE"): {"admin"},
}


def check_permission(role: str, path: str, method: str) -> bool:
    """
    检查指定角色对给定路径和方法是否有访问权限

    Args:
        role: 用户角色字符串 (admin/operator/readonly)
        path: 请求路径 (如 /pxe/config)
        method: HTTP 方法 (GET/POST/DELETE 等)

    Returns:
        True 表示有权限，False 表示无权限
    """
    method_upper = method.upper()

    # 遍历权限矩阵，查找匹配的路由前缀
    for (route_prefix, perm_method), allowed_roles in PERMISSION_MATRIX.items():
        # 检查路径是否以路由前缀开头
        if path.startswith(route_prefix) and method_upper == perm_method:
            return role in allowed_roles

    # 如果没有匹配的规则，默认拒绝
    return False
