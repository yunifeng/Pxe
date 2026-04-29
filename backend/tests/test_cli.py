"""Phase 11 - Agent CLI tests"""
import json
from unittest.mock import patch

import pytest

from cli import main

HANDLERS = "app.node.agent"


@pytest.fixture
def mocks():
    m_status = patch(f"{HANDLERS}.handle_status", return_value={"nodes": []}).start()
    m_pxe = patch(f"{HANDLERS}.handle_pxe_config", return_value="# config").start()
    m_bmc_list = patch(f"{HANDLERS}.handle_bmc_list", return_value=[]).start()
    m_bmc_power = patch(f"{HANDLERS}.handle_bmc_power", return_value={"success": True}).start()
    m_install = patch(f"{HANDLERS}.handle_install_task", return_value={"status": "ok"}).start()
    m_sync = patch(f"{HANDLERS}.handle_file_sync", return_value={"synced": 2}).start()
    m_log = patch(f"{HANDLERS}.handle_log", return_value="log line\n").start()
    patch("sys.stdin.isatty", return_value=True).start()
    yield {
        "status": m_status, "pxe_config": m_pxe, "bmc_list": m_bmc_list,
        "bmc_power": m_bmc_power, "install_task": m_install,
        "file_sync": m_sync, "log": m_log,
    }
    patch.stopall()


def _stdout_json(capsys):
    return json.loads(capsys.readouterr()[0])


class TestCliCommands:
    """Test each CLI command path."""

    def test_status(self, mocks, capsys):
        main(["status"])
        mocks["status"].assert_called_once()
        out = _stdout_json(capsys)
        assert out["success"] is True
        assert out["data"]["nodes"] == []

    def test_pxe_config(self, mocks, capsys):
        main(["pxe-config"])
        out = _stdout_json(capsys)
        assert out["data"] == "# config"

    def test_bmc_list(self, mocks, capsys):
        main(["bmc-list"])
        out = _stdout_json(capsys)
        assert out["data"] == []

    def test_bmc_power_on(self, mocks, capsys):
        main(["bmc-power", "--bmc-id", "1", "--action", "on"])
        mocks["bmc_power"].assert_called_with(1, "on")
        out = _stdout_json(capsys)
        assert out["success"] is True

    def test_install_task_get(self, mocks, capsys):
        main(["install-task", "--action", "get", "--task-id", "1"])
        out = _stdout_json(capsys)
        assert out["data"]["status"] == "ok"

    def test_file_sync(self, mocks, capsys):
        main(["file-sync", "--file-ids", "1", "2"])
        out = _stdout_json(capsys)
        assert out["data"]["synced"] == 2

    def test_log_with_lines(self, mocks, capsys):
        main(["log", "--lines", "50"])
        mocks["log"].assert_called_with(50)
        out = _stdout_json(capsys)
        assert "log line" in out["data"]


class TestCliEdgeCases:
    """Test no-command and error paths."""

    def test_no_command_shows_help(self, mocks, capsys):
        with pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code == 1
        assert "usage:" in capsys.readouterr()[0].lower()  # print_help goes to stdout

    def test_handler_error_outputs_json(self, mocks, capsys):
        mocks["status"].side_effect = Exception("db fail")
        with pytest.raises(SystemExit):
            main(["status"])
        err = json.loads(capsys.readouterr()[1])
        assert err["success"] is False
        assert "db fail" in err["error"]
