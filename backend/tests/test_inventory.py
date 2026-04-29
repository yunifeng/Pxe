"""硬件信息收集测试"""
from unittest.mock import patch

import pytest

from app.exceptions import PxeException
from app.host.inventory import get_hardware_info, _parse_lscpu, _parse_memory


class TestGetHardwareInfo:
    def test_success(self):
        mock_output = {"stdout": "data", "exit_code": 0}
        with (
            patch("app.host.inventory.exec_command", return_value=mock_output),
        ):
            result = get_hardware_info("10.0.0.1")
        assert "cpu" in result
        assert "memory" in result
        assert "disks" in result
        assert "network" in result

    def test_ssh_failure_raises(self):
        with (
            patch("app.host.inventory.exec_command", side_effect=PxeException("SSH_ERROR", "connect failed")),
        ):
            with pytest.raises(PxeException) as exc:
                get_hardware_info("10.0.0.1")
            assert "HARDWARE_INFO_ERROR" == exc.value.code


class TestParseLscpu:
    def test_json_output(self):
        result = _parse_lscpu('{"Architecture": "x86_64"}')
        assert result == {"Architecture": "x86_64"}

    def test_text_output(self):
        result = _parse_lscpu("Architecture: x86_64\nCPU(s): 4\n")
        assert result["Architecture"] == "x86_64"
        assert result["CPU(s)"] == "4"

    def test_empty_output(self):
        result = _parse_lscpu("")
        assert result == {}


class TestParseMemory:
    def test_parses_mem_line(self):
        result = _parse_memory("              total       used       free\nMem:       16          4       12\n")
        assert result["total_gb"] == 16

    def test_no_mem_line(self):
        result = _parse_memory("Swap:   2       0       2\n")
        assert result == {}
