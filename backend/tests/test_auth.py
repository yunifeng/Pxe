"""
认证系统测试
覆盖 JWT 令牌管理、角色权限检查、登录流程、频率限制等
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.auth.jwt_handler import ALGORITHM, create_token, verify_token
from app.auth.roles import PERMISSION_MATRIX, Role, check_permission
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import User

# ============================================================
# 测试用内存数据库 (使用 shared cache 确保所有连接共享同一数据库)
# ============================================================

test_engine = create_engine(
    "sqlite:///file::memory:?cache=shared",
    connect_args={"check_same_thread": False},
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# 确保所有模型被注册到 Base.metadata
from app import models  # noqa: F401


def override_get_db():
    """测试用数据库依赖覆盖"""
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """每个测试前创建表，测试后清空"""
    # 创建所有表
    Base.metadata.create_all(bind=test_engine)
    yield
    # 清空所有表 - 使用事务确保正确执行
    with test_engine.begin() as conn:
        # 禁用外键检查以安全删除
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        for table in Base.metadata.tables.values():
            conn.execute(text(f'DELETE FROM "{table.name}"'))
        conn.execute(text("PRAGMA foreign_keys=ON"))


@pytest.fixture(autouse=True)
def reset_rate_limit():
    """重置登录频率限制计数器"""
    from app.api import auth as auth_module

    auth_module._login_attempts.clear()
    yield
    auth_module._login_attempts.clear()


def _login_admin():
    """辅助函数: 使用默认管理员登录并返回 token"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200
    return response.json()["data"]["token"]


# 延迟创建 TestClient，确保依赖覆盖已设置
client = TestClient(app)


# ============================================================
# JWT 令牌测试
# ============================================================


class TestJWTHandler:
    """JWT 令牌签发和验证测试"""

    def test_create_token_returns_string(self):
        """测试 create_token 返回非空字符串"""
        token = create_token(user_id=1, role="admin")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_valid_token(self):
        """测试验证有效令牌返回正确 payload"""
        token = create_token(user_id=42, role="operator")
        payload = verify_token(token)
        assert payload["user_id"] == 42
        assert payload["role"] == "operator"
        assert "exp" in payload

    def test_verify_token_has_correct_keys(self):
        """测试 payload 包含所需 keys: user_id, role, exp"""
        token = create_token(user_id=1, role="readonly")
        payload = verify_token(token)
        assert {"user_id", "role", "exp"}.issubset(set(payload.keys()))

    def test_verify_invalid_token_raises_exception(self):
        """测试无效令牌抛出 PxeException"""
        from app.exceptions import PxeException

        with pytest.raises(PxeException) as exc_info:
            verify_token("invalid.token.here")
        assert exc_info.value.code == "INVALID_TOKEN"
        assert "Token 无效或已过期" in exc_info.value.message

    def test_verify_expired_token_raises_exception(self):
        """测试过期令牌抛出 PxeException"""
        from app.exceptions import PxeException
        from jose import jwt

        # 创建一个已过期的令牌
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {"user_id": 1, "role": "admin", "exp": past}
        expired_token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)

        with pytest.raises(PxeException) as exc_info:
            verify_token(expired_token)
        assert exc_info.value.code == "INVALID_TOKEN"

    def test_verify_token_with_wrong_secret(self):
        """测试用错误密钥签名时抛出异常"""
        from app.exceptions import PxeException
        from jose import jwt

        token = jwt.encode(
            {
                "user_id": 1,
                "role": "admin",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            "wrong_secret",
            algorithm=ALGORITHM,
        )
        with pytest.raises(PxeException):
            verify_token(token)


# ============================================================
# 角色权限测试
# ============================================================


class TestRolesAndPermissions:
    """角色定义与权限矩阵测试"""

    def test_role_enum_values(self):
        """测试角色枚举值"""
        assert Role.ADMIN.value == "admin"
        assert Role.OPERATOR.value == "operator"
        assert Role.READONLY.value == "readonly"

    def test_permission_matrix_auth_all_roles(self):
        """测试 /auth 路由所有角色可访问"""
        assert check_permission("admin", "/auth/login", "GET") is True
        assert check_permission("operator", "/auth/login", "GET") is True
        assert check_permission("readonly", "/auth/login", "GET") is True

    def test_permission_matrix_dashboard_all_roles(self):
        """测试 /dashboard 路由所有角色可访问"""
        assert check_permission("admin", "/dashboard", "GET") is True
        assert check_permission("operator", "/dashboard", "GET") is True
        assert check_permission("readonly", "/dashboard", "GET") is True

    def test_permission_matrix_pxe_no_readonly(self):
        """测试 /pxe 路由 readonly 无访问权限"""
        assert check_permission("admin", "/pxe/config", "GET") is True
        assert check_permission("operator", "/pxe/config", "GET") is True
        assert check_permission("readonly", "/pxe/config", "GET") is False

    def test_permission_matrix_bmc_no_readonly(self):
        """测试 /bmc 路由 readonly 无访问权限"""
        assert check_permission("admin", "/bmc/info", "GET") is True
        assert check_permission("operator", "/bmc/info", "GET") is True
        assert check_permission("readonly", "/bmc/info", "GET") is False

    def test_permission_matrix_node_all_roles(self):
        """测试 /node 路由所有角色可访问"""
        assert check_permission("admin", "/node/list", "GET") is True
        assert check_permission("operator", "/node/list", "GET") is True
        assert check_permission("readonly", "/node/list", "GET") is True

    def test_permission_matrix_host_all_roles(self):
        """测试 /host 路由所有角色可访问"""
        assert check_permission("admin", "/host/list", "GET") is True
        assert check_permission("operator", "/host/list", "GET") is True
        assert check_permission("readonly", "/host/list", "GET") is True

    def test_permission_matrix_file_no_readonly(self):
        """测试 /file 路由 readonly 无访问权限"""
        assert check_permission("admin", "/file/list", "GET") is True
        assert check_permission("operator", "/file/list", "GET") is True
        assert check_permission("readonly", "/file/list", "GET") is False

    def test_permission_matrix_template_admin_only(self):
        """测试 /template 路由仅 admin 可访问"""
        assert check_permission("admin", "/template/list", "GET") is True
        assert check_permission("operator", "/template/list", "GET") is False
        assert check_permission("readonly", "/template/list", "GET") is False

    def test_permission_delete_only_admin(self):
        """测试 DELETE 方法仅 admin 可访问"""
        assert check_permission("admin", "/pxe/config", "DELETE") is True
        assert check_permission("operator", "/pxe/config", "DELETE") is False
        assert check_permission("readonly", "/pxe/config", "DELETE") is False
        assert check_permission("admin", "/template/list", "DELETE") is True
        assert check_permission("operator", "/template/list", "DELETE") is False

    def test_unknown_path_returns_false(self):
        """测试未知路径返回 False"""
        assert check_permission("admin", "/unknown/path", "GET") is False

    def test_permission_matrix_contains_expected_entries(self):
        """测试权限矩阵包含预期条目"""
        prefixes = {key[0] for key in PERMISSION_MATRIX.keys()}
        assert "/auth" in prefixes
        assert "/dashboard" in prefixes
        assert "/pxe" in prefixes
        assert "/bmc" in prefixes
        assert "/node" in prefixes
        assert "/host" in prefixes
        assert "/file" in prefixes
        assert "/template" in prefixes


# ============================================================
# 登录流程测试
# ============================================================


class TestLoginFlow:
    """登录端点测试"""

    def test_default_admin_user_created_on_first_login(self):
        """测试首次登录自动创建默认管理员用户"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data["data"]
        assert data["data"]["user"]["username"] == "admin"
        assert data["data"]["user"]["role"] == "admin"

    def test_login_with_valid_credentials(self):
        """测试有效凭证登录成功"""
        db = TestSession()
        user = User(username="operator1", role="operator")
        user.password = "pass456"
        db.add(user)
        db.commit()
        db.refresh(user)
        uid = user.id
        db.close()

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "operator1", "password": "pass456"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "token" in data["data"]
        assert data["data"]["user"]["id"] == uid

    def test_login_with_invalid_password(self):
        """测试错误密码返回 401"""
        db = TestSession()
        user = User(username="user1", role="readonly")
        user.password = "correct"
        db.add(user)
        db.commit()
        db.close()

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "user1", "password": "wrong"},
        )
        assert response.status_code == 401

    def test_login_with_nonexistent_user(self):
        """测试不存在的用户返回 401"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "pass"},
        )
        assert response.status_code == 401

    def test_login_returns_token_and_user_info(self):
        """测试登录响应包含 token 和用户信息"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data["data"]
        assert "user" in data["data"]
        assert "id" in data["data"]["user"]
        assert "username" in data["data"]["user"]
        assert "role" in data["data"]["user"]


# ============================================================
# 频率限制测试
# ============================================================


class TestRateLimiting:
    """登录频率限制测试"""

    def test_rate_limit_blocks_after_5_attempts(self):
        """测试超过 5 次尝试后返回 429"""
        # 前 5 次失败但不应触发频率限制
        for i in range(5):
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "wrong"},
            )
            assert response.status_code == 401, f"第 {i + 1} 次应该返回 401"

        # 第 6 次应该被频率限制拦截
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
        assert response.status_code == 429


# ============================================================
# Profile 端点测试
# ============================================================


class TestProfileEndpoint:
    """获取当前用户信息端点测试"""

    def test_profile_returns_401_without_token(self):
        """测试无 token 访问 profile 返回 401"""
        response = client.get("/api/v1/auth/profile")
        assert response.status_code in (401, 403)

    def test_profile_returns_user_info_with_valid_token(self):
        """测试有效 token 访问 profile 返回用户信息"""
        token = _login_admin()
        response = client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_profile_with_invalid_token(self):
        """测试无效 token 访问 profile 返回错误"""
        response = client.get(
            "/api/v1/auth/profile",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 400


# ============================================================
# Logout 端点测试
# ============================================================


class TestLogoutEndpoint:
    """登出端点测试"""

    def test_logout_returns_success(self):
        """测试登出返回成功"""
        token = _login_admin()
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_logout_without_token_returns_error(self):
        """测试无 token 登出返回错误"""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code in (401, 403)


# ============================================================
# 默认管理员测试
# ============================================================


class TestDefaultAdmin:
    """默认管理员用户创建测试"""

    def test_default_admin_exists_after_first_login(self):
        """测试首次登录后默认管理员存在于数据库"""
        # 触发默认管理员创建
        client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )

        # 验证数据库中确实存在
        db = TestSession()
        admin = db.query(User).filter_by(username="admin").first()
        assert admin is not None
        assert admin.role == "admin"
        assert admin.verify_password("admin123")
        db.close()
