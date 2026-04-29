"""Ansible 操作 Mock 测试"""
from unittest.mock import patch
import subprocess

import pytest

from app.exceptions import PxeException
from app.host.ansible import run_playbook, run_module


class TestRunPlaybook:
    def test_success(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], returncode=0, stdout="ok", stderr=""
            )
            result = run_playbook("srv01", "/opt/playbook.yml", {"key": "val"})
            assert result == "ok"
            args = mock_run.call_args_list[0].args[0]
            assert args[:4] == ["ansible-playbook", "/opt/playbook.yml", "-l", "srv01"]
            assert "-e" in args
            assert "key=val" in args

    def test_failure_raises(self):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, [], output="", stderr="failed")
            with pytest.raises(PxeException) as exc:
                run_playbook("srv01", "/opt/playbook.yml")
            assert "ANSIBLE_ERROR" == exc.value.code

    def test_no_extra_vars(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], returncode=0, stdout="done", stderr=""
            )
            run_playbook("srv01", "/opt/playbook.yml")
            args = mock_run.call_args_list[0].args[0]
            assert "-e" not in args


class TestRunModule:
    def test_success(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], returncode=0, stdout="pong", stderr=""
            )
            result = run_module("srv01", "ping")
            assert result["exit_code"] == 0
            assert result["stdout"] == "pong"

    def test_with_args(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], returncode=0, stdout="{}", stderr=""
            )
            run_module("srv01", "shell", "uptime")
            assert "shell" in mock_run.call_args_list[0].args[0]

    def test_failure_returns_exit_code(self):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(2, [], output="", stderr="err")
            result = run_module("srv01", "shell", "bad_cmd")
            assert result["exit_code"] == 2
