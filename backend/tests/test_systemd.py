"""Systemd 工具测试"""
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from app.exceptions import PxeException
from app.utils.systemd import get_service_status, is_active, systemctl


class TestSystemctl:
    """systemctl() 命令封装测试"""

    @patch("app.utils.systemd.subprocess.run")
    def test_systemctl_start(self, mock_run):
        mock_run.return_value = MagicMock(stdout="Started.\n", stderr="", returncode=0)
        out = systemctl("start", "dnsmasq")
        assert out == "Started."
        mock_run.assert_called_once_with(
            ["systemctl", "start", "dnsmasq"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

    @patch("app.utils.systemd.subprocess.run")
    def test_systemctl_restart(self, mock_run):
        mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
        systemctl("restart", "tftp")
        mock_run.assert_called_once()

    def test_invalid_action_raises(self):
        with pytest.raises(PxeException) as exc:
            systemctl("invalid_action", "some_service")
        assert exc.value.code == "INVALID_ACTION"

    @patch("app.utils.systemd.subprocess.run")
    def test_called_process_error(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["systemctl", "start", "bad"], stderr="Failed to start"
        )
        with pytest.raises(PxeException) as exc:
            systemctl("start", "bad")
        assert exc.value.code == "SYSTEMCTL_ERROR"

    @patch("app.utils.systemd.subprocess.run")
    def test_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["systemctl"], timeout=30)
        with pytest.raises(PxeException) as exc:
            systemctl("start", "slow")
        assert exc.value.code == "SYSTEMCTL_TIMEOUT"


class TestIsActive:
    """is_active() 测试"""

    @patch("app.utils.systemd.subprocess.run")
    def test_active_returns_true(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        assert is_active("dnsmasq") is True

    @patch("app.utils.systemd.subprocess.run")
    def test_inactive_returns_false(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=3, cmd=["systemctl", "is-active", "dead"], output="inactive"
        )
        assert is_active("dead") is False


class TestGetServiceStatus:
    """get_service_status() 测试"""

    @patch("app.utils.systemd.systemctl")
    def test_delegates_to_systemctl_status(self, mock_systemctl):
        mock_systemctl.return_value = "● dnsmasq.service - DNS Server"
        result = get_service_status("dnsmasq")
        assert result == "● dnsmasq.service - DNS Server"
        mock_systemctl.assert_called_once_with("status", "dnsmasq")
