"""BMC 管理测试"""
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.auth.jwt_handler import create_token
from app.database import Base, get_db
from app.exceptions import PxeException
from app.main import app
from app.models import BmcInfo

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


def _mock_ipmi_module():
    """Create a mock ipmi module with a BMC class and return (mock_module, mock_bmc_instance)."""
    mock_bmc = MagicMock()
    mock_bmc_class = MagicMock(return_value=mock_bmc)
    mock_ipmi = MagicMock()
    mock_ipmi.BMC = mock_bmc_class
    return mock_ipmi, mock_bmc


class TestIPMIHandler:
    """IPMI 操作 Mock 测试"""

    def test_missing_dependency_raises(self):
        from app.bmc import ipmi_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        with patch.object(ipmi_handler, "IPMI_CONNECT_TIMEOUT", 10):
            with pytest.raises(PxeException) as exc:
                ipmi_handler.get_power_status(info)
            assert exc.value.code in ("MISSING_DEPENDENCY", "IPMI_CONNECT_ERROR")

    def test_get_conn_missing_dependency(self):
        from app.bmc import ipmi_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        with patch.dict("sys.modules", {"ipmi": None}):
            with pytest.raises(PxeException) as exc:
                ipmi_handler._get_conn(info)
            assert exc.value.code == "MISSING_DEPENDENCY"

    def test_get_power_status_success(self):
        from app.bmc import ipmi_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_ipmi, mock_bmc = _mock_ipmi_module()
        mock_bmc.get_power_status.return_value = "On"
        with patch.dict("sys.modules", {"ipmi": mock_ipmi}):
            result = ipmi_handler.get_power_status(info)
        assert result == "on"
        mock_bmc.open.assert_called_once()
        mock_bmc.close.assert_called_once()

    def test_get_power_status_connection_error(self):
        from app.bmc import ipmi_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_ipmi, mock_bmc = _mock_ipmi_module()
        mock_bmc.open.side_effect = Exception("connection refused")
        with patch.dict("sys.modules", {"ipmi": mock_ipmi}):
            with pytest.raises(PxeException) as exc:
                ipmi_handler.get_power_status(info)
            assert exc.value.code == "IPMI_POWER_STATUS_ERROR"

    def test_power_on_success(self):
        from app.bmc import ipmi_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_ipmi, mock_bmc = _mock_ipmi_module()
        with patch.dict("sys.modules", {"ipmi": mock_ipmi}):
            ipmi_handler.power_on(info)
        mock_bmc.power_on.assert_called_once()

    def test_power_on_error(self):
        from app.bmc import ipmi_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_ipmi, mock_bmc = _mock_ipmi_module()
        mock_bmc.open.side_effect = Exception("timeout")
        with patch.dict("sys.modules", {"ipmi": mock_ipmi}):
            with pytest.raises(PxeException) as exc:
                ipmi_handler.power_on(info)
            assert exc.value.code == "IPMI_POWER_ON_ERROR"

    def test_power_off_success(self):
        from app.bmc import ipmi_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_ipmi, mock_bmc = _mock_ipmi_module()
        with patch.dict("sys.modules", {"ipmi": mock_ipmi}):
            ipmi_handler.power_off(info)
        mock_bmc.power_off.assert_called_once()

    def test_power_off_error(self):
        from app.bmc import ipmi_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_ipmi, mock_bmc = _mock_ipmi_module()
        mock_bmc.open.side_effect = Exception("timeout")
        with patch.dict("sys.modules", {"ipmi": mock_ipmi}):
            with pytest.raises(PxeException) as exc:
                ipmi_handler.power_off(info)
            assert exc.value.code == "IPMI_POWER_OFF_ERROR"

    def test_restart_calls_power_off_and_on(self):
        from app.bmc import ipmi_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_ipmi, mock_bmc = _mock_ipmi_module()
        with patch.dict("sys.modules", {"ipmi": mock_ipmi}):
            ipmi_handler.restart(info)
        assert mock_bmc.power_off.call_count == 1
        assert mock_bmc.power_on.call_count == 1

    def test_cycle_success(self):
        from app.bmc import ipmi_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_ipmi, mock_bmc = _mock_ipmi_module()
        with patch.dict("sys.modules", {"ipmi": mock_ipmi}):
            ipmi_handler.cycle(info)
        mock_bmc.power_cycle.assert_called_once()

    def test_cycle_error(self):
        from app.bmc import ipmi_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_ipmi, mock_bmc = _mock_ipmi_module()
        mock_bmc.open.side_effect = Exception("fail")
        with patch.dict("sys.modules", {"ipmi": mock_ipmi}):
            with pytest.raises(PxeException) as exc:
                ipmi_handler.cycle(info)
            assert exc.value.code == "IPMI_POWER_CYCLE_ERROR"

    def test_get_sensor_data_success(self):
        from app.bmc import ipmi_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_ipmi, mock_bmc = _mock_ipmi_module()
        mock_sensor1 = MagicMock()
        mock_sensor1.name = "temp"
        mock_sensor1.value = 42.0
        mock_sensor2 = MagicMock()
        mock_sensor2.name = "fan"
        mock_sensor2.value = 3000
        mock_bmc.get_sensor_data.return_value = [mock_sensor1, mock_sensor2]
        with patch.dict("sys.modules", {"ipmi": mock_ipmi}):
            result = ipmi_handler.get_sensor_data(info)
        assert result == {"temp": 42.0, "fan": 3000}

    def test_get_sensor_data_error(self):
        from app.bmc import ipmi_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_ipmi, mock_bmc = _mock_ipmi_module()
        mock_bmc.open.side_effect = Exception("fail")
        with patch.dict("sys.modules", {"ipmi": mock_ipmi}):
            with pytest.raises(PxeException) as exc:
                ipmi_handler.get_sensor_data(info)
            assert exc.value.code == "IPMI_SENSOR_ERROR"


def _mock_redfish_modules():
    """Create mock redfish modules and return (mock_dict, mock_sess)."""
    mock_sess = MagicMock()
    mock_server_protocol = MagicMock(return_value=mock_sess)
    mock_v1 = MagicMock()
    mock_v1.ServerProtocol = mock_server_protocol
    mock_rest = MagicMock()
    mock_rest.v1 = mock_v1
    mock_redfish = MagicMock()
    mock_redfish.rest = mock_rest

    mock_dict = {
        "redfish": mock_redfish,
        "redfish.rest": mock_rest,
        "redfish.rest.v1": mock_v1,
    }
    return mock_dict, mock_sess


class TestRedfishHandler:
    """Redfish 操作 Mock 测试"""

    def test_get_power_status_on(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_dict, mock_sess = _mock_redfish_modules()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.dict = {"PowerState": "On"}
        mock_sess.get.return_value = mock_resp
        with patch.dict("sys.modules", mock_dict):
            result = redfish_handler.get_power_status(info)
        assert result == "on"
        mock_sess.get.assert_called_with("/redfish/v1/Systems/1")
        mock_sess.logout.assert_called()

    def test_get_power_status_off(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_dict, mock_sess = _mock_redfish_modules()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.dict = {"PowerState": "Off"}
        mock_sess.get.return_value = mock_resp
        with patch.dict("sys.modules", mock_dict):
            result = redfish_handler.get_power_status(info)
        assert result == "off"

    def test_get_power_status_non_200(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_dict, mock_sess = _mock_redfish_modules()
        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_sess.get.return_value = mock_resp
        with patch.dict("sys.modules", mock_dict):
            result = redfish_handler.get_power_status(info)
        assert result == "unknown"

    def test_get_power_status_error(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_dict, mock_sess = _mock_redfish_modules()
        mock_sess.get.side_effect = Exception("connection error")
        with patch.dict("sys.modules", mock_dict):
            with pytest.raises(PxeException) as exc:
                redfish_handler.get_power_status(info)
            assert exc.value.code == "REDFISH_POWER_STATUS_ERROR"

    def test_power_on_success(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_dict, mock_sess = _mock_redfish_modules()
        with patch.dict("sys.modules", mock_dict):
            redfish_handler.power_on(info)
        mock_sess.patch.assert_called_with(
            "/redfish/v1/Systems/1", body={"PowerState": "On"}
        )
        mock_sess.logout.assert_called()

    def test_power_on_error(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_dict, mock_sess = _mock_redfish_modules()
        mock_sess.patch.side_effect = Exception("fail")
        with patch.dict("sys.modules", mock_dict):
            with pytest.raises(PxeException) as exc:
                redfish_handler.power_on(info)
            assert exc.value.code == "REDFISH_POWER_ON_ERROR"

    def test_power_off_success(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_dict, mock_sess = _mock_redfish_modules()
        with patch.dict("sys.modules", mock_dict):
            redfish_handler.power_off(info)
        mock_sess.patch.assert_called_with(
            "/redfish/v1/Systems/1", body={"PowerState": "Off"}
        )

    def test_power_off_error(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_dict, mock_sess = _mock_redfish_modules()
        mock_sess.patch.side_effect = Exception("fail")
        with patch.dict("sys.modules", mock_dict):
            with pytest.raises(PxeException) as exc:
                redfish_handler.power_off(info)
            assert exc.value.code == "REDFISH_POWER_OFF_ERROR"

    def test_restart_success(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_dict, mock_sess = _mock_redfish_modules()
        with patch.dict("sys.modules", mock_dict):
            redfish_handler.restart(info)
        mock_sess.patch.assert_called_with(
            "/redfish/v1/Systems/1", body={"ResetType": "GracefulRestart"}
        )

    def test_restart_error(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_dict, mock_sess = _mock_redfish_modules()
        mock_sess.patch.side_effect = Exception("fail")
        with patch.dict("sys.modules", mock_dict):
            with pytest.raises(PxeException) as exc:
                redfish_handler.restart(info)
            assert exc.value.code == "REDFISH_RESTART_ERROR"

    def test_cycle_success(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_dict, mock_sess = _mock_redfish_modules()
        with patch.dict("sys.modules", mock_dict):
            redfish_handler.cycle(info)
        mock_sess.patch.assert_called_with(
            "/redfish/v1/Systems/1", body={"ResetType": "ForceRestart"}
        )

    def test_cycle_error(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_dict, mock_sess = _mock_redfish_modules()
        mock_sess.patch.side_effect = Exception("fail")
        with patch.dict("sys.modules", mock_dict):
            with pytest.raises(PxeException) as exc:
                redfish_handler.cycle(info)
            assert exc.value.code == "REDFISH_CYCLE_ERROR"

    def test_auto_detect_redfish(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_dict, mock_sess = _mock_redfish_modules()
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.dict = {"PowerState": "On"}
        mock_sess.get.return_value = mock_resp
        with patch.dict("sys.modules", mock_dict):
            result = redfish_handler.auto_detect(info)
        assert result == "redfish"

    def test_auto_detect_fallback_to_ipmi(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_dict, _ = _mock_redfish_modules()
        # Make login fail
        mock_dict["redfish.rest.v1"].ServerProtocol.side_effect = Exception("no redfish")
        with patch.dict("sys.modules", mock_dict):
            result = redfish_handler.auto_detect(info)
        assert result == "ipmi"

    def test_auto_detect_unknown_fallback_to_ipmi(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_dict, mock_sess = _mock_redfish_modules()
        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_sess.get.return_value = mock_resp
        with patch.dict("sys.modules", mock_dict):
            result = redfish_handler.auto_detect(info)
        assert result == "ipmi"

    def test_get_session_missing_dependency(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        with patch.dict("sys.modules", {"redfish": None, "redfish.rest": None, "redfish.rest.v1": None}):
            with pytest.raises(PxeException) as exc:
                redfish_handler._get_session(info)
            assert exc.value.code == "MISSING_DEPENDENCY"

    def test_get_session_login_failure(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.1", "username": "admin", "password": "pass"}
        mock_dict, mock_sess = _mock_redfish_modules()
        mock_sess.login.side_effect = Exception("auth failed")
        with patch.dict("sys.modules", mock_dict):
            with pytest.raises(PxeException) as exc:
                redfish_handler._get_session(info)
            assert exc.value.code == "REDFISH_CONNECT_ERROR"

    def test_get_session_sets_correct_params(self):
        from app.bmc import redfish_handler
        info = {"bmc_ip": "10.0.0.2", "username": "root", "password": "secret"}
        mock_dict, mock_sess = _mock_redfish_modules()
        with patch.dict("sys.modules", mock_dict):
            redfish_handler._get_session(info)
        mock_sess.set_base_url.assert_called_with("https://10.0.0.2")
        mock_sess.set_username.assert_called_with("root")
        mock_sess.set_password.assert_called_with("secret")
        mock_sess.set_timeout.assert_called()


class TestBatchBMC:
    """批量 BMC 操作测试"""

    def _create_bmcs(self, db, count=2):
        """Helper to create BMC records in the test DB."""
        bmcs = []
        for i in range(count):
            bmc = BmcInfo(
                hostname=f"srv{i}",
                bmc_ip=f"10.0.0.{i+1}",
                username="admin",
                password="pass",
                protocol="ipmi" if i == 0 else "redfish",
            )
            db.add(bmc)
            bmcs.append(bmc)
        db.commit()
        return bmcs

    def test_invalid_action_raises(self):
        from app.bmc.batch import batch_power_action
        db = TestSession()
        with pytest.raises(PxeException) as exc:
            batch_power_action([1], "invalid_action", db)
        assert exc.value.code == "INVALID_ACTION"
        db.close()

    def test_bmc_not_found_raises(self):
        from app.bmc.batch import batch_power_action
        db = TestSession()
        with pytest.raises(PxeException) as exc:
            batch_power_action([999], "power_on", db)
        assert exc.value.code == "BMC_NOT_FOUND"
        db.close()

    def test_batch_power_on_all_success(self):
        from app.bmc.batch import batch_power_action
        db = TestSession()
        bmcs = self._create_bmcs(db, 2)
        ids = [b.id for b in bmcs]
        with patch("app.bmc.batch.ipmi_handler.power_on"), \
             patch("app.bmc.batch.redfish_handler.power_on"):
            results = batch_power_action(ids, "power_on", db)
        assert len(results) == 2
        for bmc_id in ids:
            assert results[bmc_id]["success"] is True
        db.close()

    def test_batch_power_on_mixed_results(self):
        from app.bmc.batch import batch_power_action
        db = TestSession()
        bmcs = self._create_bmcs(db, 2)
        ids = [b.id for b in bmcs]
        with patch("app.bmc.batch.ipmi_handler.power_on"), \
             patch("app.bmc.batch.redfish_handler.power_on") as mock_rf:
            mock_rf.side_effect = PxeException("CONN_ERROR", "connection refused")
            results = batch_power_action(ids, "power_on", db)
        assert results[bmcs[0].id]["success"] is True
        assert results[bmcs[1].id]["success"] is False
        assert "connection refused" in results[bmcs[1].id]["error"]
        db.close()

    def test_batch_power_off(self):
        from app.bmc.batch import batch_power_action
        db = TestSession()
        bmcs = self._create_bmcs(db, 1)
        [bmc] = bmcs
        with patch("app.bmc.batch.ipmi_handler.power_off"):
            results = batch_power_action([bmc.id], "power_off", db)
        assert results[bmc.id]["success"] is True
        db.close()

    def test_batch_restart(self):
        from app.bmc.batch import batch_power_action
        db = TestSession()
        bmcs = self._create_bmcs(db, 1)
        [bmc] = bmcs
        with patch("app.bmc.batch.ipmi_handler.restart"):
            results = batch_power_action([bmc.id], "restart", db)
        assert results[bmc.id]["success"] is True
        db.close()

    def test_batch_cycle(self):
        from app.bmc.batch import batch_power_action
        db = TestSession()
        bmcs = self._create_bmcs(db, 1)
        [bmc] = bmcs
        with patch("app.bmc.batch.ipmi_handler.cycle"):
            results = batch_power_action([bmc.id], "cycle", db)
        assert results[bmc.id]["success"] is True
        db.close()

    def test_do_action_generic_exception(self):
        from app.bmc.batch import _do_action
        bmc = BmcInfo(
            hostname="srv0",
            bmc_ip="10.0.0.1",
            username="admin",
            password="pass",
            protocol="ipmi",
        )
        with patch("app.bmc.batch.ipmi_handler.power_on") as mock_ipmi:
            mock_ipmi.side_effect = RuntimeError("unexpected")
            result = _do_action(bmc, "power_on")
        assert result["success"] is False
        assert "unexpected" in result["error"]


class TestBmcAPI:
    """BMC API 端点集成测试"""

    def test_add_bmc(self):
        token = _admin_token()
        resp = client.post(
            "/api/v1/bmc/",
            json={
                "hostname": "srv01",
                "bmc_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "protocol": "redfish",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["hostname"] == "srv01"

    def test_list_bmcs(self):
        token = _admin_token()
        client.post(
            "/api/v1/bmc/",
            json={
                "hostname": "srv01",
                "bmc_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "protocol": "redfish",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = client.get("/api/v1/bmc/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1

    def test_batch_add(self):
        token = _admin_token()
        resp = client.post(
            "/api/v1/bmc/batch",
            json={"csv_data": "srv01,10.0.0.1,admin,pass,redfish\nsrv02,10.0.0.2,admin,pass,ipmi"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["added"] == 2

    def test_bmc_stats(self):
        token = _admin_token()
        resp = client.get("/api/v1/bmc/stats", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total" in data
        assert "on" in data
        assert "off" in data

    def test_bmc_requires_auth(self):
        resp = client.get("/api/v1/bmc/")
        assert resp.status_code in (401, 403)
