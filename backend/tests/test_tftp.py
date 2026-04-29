"""TFTP 服务管理测试"""
import os
from unittest.mock import patch

import pytest

from app.exceptions import PxeException
from app.pxe import tftp


class TestTFTPSetup:
    """setup_tftp 测试"""

    def test_setup_tftp_creates_dirs(self, tmp_path):
        result = tftp.setup_tftp(str(tmp_path))
        assert result["tftp_root"] == str(tmp_path)
        assert os.path.isdir(os.path.join(str(tmp_path), "ipxe"))
        assert os.path.isdir(os.path.join(str(tmp_path), "pxelinux.cfg"))
        assert os.path.isdir(os.path.join(str(tmp_path), "images"))

    def test_setup_tftp_default_uses_settings(self, tmp_path):
        with patch("app.pxe.tftp.settings") as mock_settings:
            mock_settings.tftp_root = str(tmp_path)
            result = tftp.setup_tftp()
        assert result["tftp_root"] == str(tmp_path)


class TestTFTPStatus:
    """get_status 测试"""

    def test_get_status_running(self, tmp_path):
        with patch("app.pxe.tftp.is_active", return_value=True), \
             patch("app.pxe.tftp.settings") as mock_settings:
            mock_settings.tftp_root = str(tmp_path)
            result = tftp.get_status()
        assert result["running"] is True
        assert result["root"] == str(tmp_path)

    def test_get_status_not_running(self, tmp_path):
        with patch("app.pxe.tftp.is_active", return_value=False), \
             patch("app.pxe.tftp.settings") as mock_settings:
            mock_settings.tftp_root = str(tmp_path)
            result = tftp.get_status()
        assert result["running"] is False


class TestTFTPStart:
    """start 测试"""

    def test_start_success(self):
        with patch("app.pxe.tftp.subprocess.run"):
            tftp.start()

    def test_start_failure(self):
        import subprocess
        with patch("app.pxe.tftp.subprocess.run",
                   side_effect=subprocess.CalledProcessError(1, "cmd", stderr="permission denied")):
            with pytest.raises(PxeException) as exc:
                tftp.start()
            assert exc.value.code == "TFTP_START_ERROR"
            assert "permission denied" in exc.value.message


class TestTFTPStop:
    """stop 测试"""

    def test_stop_success(self):
        with patch("app.pxe.tftp.subprocess.run"):
            tftp.stop()

    def test_stop_failure(self):
        import subprocess
        with patch("app.pxe.tftp.subprocess.run",
                   side_effect=subprocess.CalledProcessError(1, "cmd", stderr="unit not loaded")):
            with pytest.raises(PxeException) as exc:
                tftp.stop()
            assert exc.value.code == "TFTP_STOP_ERROR"


class TestTFTPRestart:
    """restart 测试"""

    def test_restart_success(self):
        with patch("app.pxe.tftp.subprocess.run"):
            tftp.restart()

    def test_restart_failure(self):
        import subprocess
        with patch("app.pxe.tftp.subprocess.run",
                   side_effect=subprocess.CalledProcessError(1, "cmd", stderr="active dead")):
            with pytest.raises(PxeException) as exc:
                tftp.restart()
            assert exc.value.code == "TFTP_RESTART_ERROR"


class TestTFTPListFiles:
    """list_files 测试"""

    def test_list_files_success(self, tmp_path):
        # Create test files
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (tmp_path / "file1.txt").write_text("hello")
        (tmp_path / "file2.bin").write_bytes(b"\x00\x01\x02")

        with patch("app.pxe.tftp.settings") as mock_settings:
            mock_settings.tftp_root = str(tmp_path)
            result = tftp.list_files()
        names = {item["name"] for item in result}
        assert "file1.txt" in names
        assert "file2.bin" in names
        assert "subdir" in names
        # Check types
        for item in result:
            if item["name"] == "subdir":
                assert item["is_dir"] is True
                assert item["size"] == 0
            else:
                assert item["is_dir"] is False
                assert item["size"] > 0

    def test_list_files_subdirectory(self, tmp_path):
        subdir = tmp_path / "images"
        subdir.mkdir()
        (subdir / "vmlinuz").write_text("fake kernel")

        with patch("app.pxe.tftp.settings") as mock_settings:
            mock_settings.tftp_root = str(tmp_path)
            result = tftp.list_files("images")
        assert len(result) == 1
        assert result[0]["name"] == "vmlinuz"

    def test_list_files_directory_not_found(self):
        with patch("app.pxe.tftp.settings") as mock_settings:
            mock_settings.tftp_root = "/nonexistent"
            with pytest.raises(PxeException) as exc:
                tftp.list_files("nonexistent/path")
            assert exc.value.code == "DIRECTORY_NOT_FOUND"
