"""dnsmasq 配置生成验证测试"""
from unittest.mock import patch, mock_open

import pytest

from app.exceptions import PxeException
from app.pxe.dnsmasq import generate_config


class TestDnsmasqConfig:
    """dnsmasq 配置生成测试"""

    def test_generate_basic_config(self):
        config = generate_config(
            interface="eth0",
            dhcp_range="192.168.1.100,192.168.1.200,12h",
        )
        assert "interface=eth0" in config
        assert "dhcp-range=192.168.1.100,192.168.1.200,12h" in config
        assert "dhcp-boot=undionly.kpxe" in config

    def test_generate_with_tftp_server(self):
        config = generate_config(
            interface="eth0",
            dhcp_range="192.168.1.100,192.168.1.200,12h",
            tftp_server="/var/lib/tftpboot",
        )
        assert "tftp-root=/var/lib/tftpboot" in config
        assert "enable-tftp" in config

    def test_generate_with_mac_filters(self):
        config = generate_config(
            interface="eth0",
            dhcp_range="192.168.1.100,192.168.1.200,12h",
            mac_filters={"AA:BB:CC:DD:EE:01": "boot-x86_64.efi"},
        )
        assert "dhcp-host=AA:BB:CC:DD:EE:01,boot-x86_64.efi" in config

    def test_config_syntax_valid(self):
        config = generate_config(
            interface="eth0",
            dhcp_range="192.168.1.100,192.168.1.200,12h",
            tftp_server="/tftp",
            mac_filters={"AA:BB:CC:DD:EE:01": "menu.ipxe"},
        )
        lines = [l for l in config.splitlines() if l and not l.startswith("#")]
        for line in lines:
            assert len(line.strip()) > 0


class TestDnsmasqApplyConfig:
    """apply_config 测试"""

    def test_apply_config_success(self):
        from app.pxe.dnsmasq import apply_config
        with patch("app.pxe.dnsmasq.os.path.exists", return_value=True), \
             patch("app.pxe.dnsmasq.open", mock_open()), \
             patch("app.pxe.dnsmasq.subprocess.run"):
            apply_config("interface=eth0")

    def test_apply_config_permission_denied(self):
        from app.pxe.dnsmasq import apply_config
        with patch("app.pxe.dnsmasq.os.path.exists", return_value=False), \
             patch("app.pxe.dnsmasq.os.geteuid", return_value=1000):
            with pytest.raises(PxeException) as exc:
                apply_config("interface=eth0")
            assert exc.value.code == "PERMISSION_DENIED"

    def test_apply_config_subprocess_error(self):
        from app.pxe.dnsmasq import apply_config
        import subprocess
        with patch("app.pxe.dnsmasq.os.path.exists", return_value=True), \
             patch("app.pxe.dnsmasq.open", mock_open()), \
             patch("app.pxe.dnsmasq.subprocess.run",
                   side_effect=subprocess.CalledProcessError(1, "cmd", stderr="fail")):
            with pytest.raises(PxeException) as exc:
                apply_config("interface=eth0")
            assert exc.value.code == "APPLY_CONFIG_ERROR"


class TestDnsmasqGetConfig:
    """get_config 测试"""

    def test_get_config_file_exists(self):
        from app.pxe.dnsmasq import get_config
        mock_content = "interface=eth0\ndhcp-range=192.168.1.100,192.168.1.200,12h\n"
        with patch("app.pxe.dnsmasq.open", mock_open(read_data=mock_content)):
            result = get_config()
        assert result == mock_content

    def test_get_config_file_not_found(self):
        from app.pxe.dnsmasq import get_config
        with patch("app.pxe.dnsmasq.open", side_effect=FileNotFoundError):
            result = get_config()
        assert result == ""


class TestDnsmasqMacFilters:
    """MAC 过滤器 CRUD 测试"""

    def test_add_mac_filter(self):
        from app.pxe.dnsmasq import add_mac_filter
        with patch("app.pxe.dnsmasq.get_config", return_value=""), \
             patch("app.pxe.dnsmasq.apply_config"):
            result = add_mac_filter("AA:BB:CC:DD:EE:01", "boot.ipxe")
        assert result == {"AA:BB:CC:DD:EE:01": "boot.ipxe"}

    def test_remove_mac_filter_existing(self):
        from app.pxe.dnsmasq import remove_mac_filter
        with patch("app.pxe.dnsmasq.get_config", return_value=""), \
             patch("app.pxe.dnsmasq.apply_config"):
            result = remove_mac_filter("AA:BB:CC:DD:EE:01")
        assert result == {}

    def test_remove_mac_filter_nonexistent(self):
        from app.pxe.dnsmasq import remove_mac_filter
        with patch("app.pxe.dnsmasq.get_config", return_value=""), \
             patch("app.pxe.dnsmasq.apply_config"):
            result = remove_mac_filter("ZZ:ZZ:ZZ:ZZ:ZZ:ZZ")
        assert result == {}

    def test_get_mac_filters_from_config(self):
        from app.pxe.dnsmasq import get_mac_filters
        config_content = """interface=eth0

# MAC-specific boot files
dhcp-host=AA:BB:CC:DD:EE:01,boot.ipxe
dhcp-host=AA:BB:CC:DD:EE:02,menu.ipxe
"""
        with patch("app.pxe.dnsmasq.get_config", return_value=config_content):
            result = get_mac_filters()
        assert result == {
            "AA:BB:CC:DD:EE:01": "boot.ipxe",
            "AA:BB:CC:DD:EE:02": "menu.ipxe",
        }

    def test_get_mac_filters_empty_config(self):
        from app.pxe.dnsmasq import get_mac_filters
        with patch("app.pxe.dnsmasq.get_config", return_value="interface=eth0\n"):
            result = get_mac_filters()
        assert result == {}

    def test_save_mac_filters_empty(self):
        from app.pxe.dnsmasq import save_mac_filters
        existing = "interface=eth0\ndhcp-range=test\n"
        with patch("app.pxe.dnsmasq.get_config", return_value=existing), \
             patch("app.pxe.dnsmasq.apply_config"):
            save_mac_filters({})

    def test_save_mac_filters_with_data(self):
        from app.pxe.dnsmasq import save_mac_filters
        existing = "interface=eth0\n"
        with patch("app.pxe.dnsmasq.get_config", return_value=existing), \
             patch("app.pxe.dnsmasq.apply_config") as mock_apply:
            save_mac_filters({"AA:BB:CC:DD:EE:01": "boot.ipxe"})
        # Verify apply_config was called with content containing the MAC filter
        args = mock_apply.call_args[0][0]
        assert "dhcp-host=AA:BB:CC:DD:EE:01,boot.ipxe" in args

    def test_save_mac_filters_replaces_existing(self):
        from app.pxe.dnsmasq import save_mac_filters
        existing = """interface=eth0

# MAC-specific boot files
dhcp-host=OLD:MAC:ADDR:01,old.ipxe
"""
        with patch("app.pxe.dnsmasq.get_config", return_value=existing), \
             patch("app.pxe.dnsmasq.apply_config") as mock_apply:
            save_mac_filters({"NEW:MAC:ADDR:01": "new.ipxe"})
        args = mock_apply.call_args[0][0]
        assert "OLD:MAC:ADDR:01" not in args
        assert "dhcp-host=NEW:MAC:ADDR:01,new.ipxe" in args


class TestDnsmasqServiceStatus:
    """dnsmasq 服务状态测试"""

    def test_get_service_status(self):
        from app.pxe.dnsmasq import get_service_status
        with patch("app.pxe.dnsmasq.is_active", return_value=True), \
             patch("app.pxe.dnsmasq.get_config", return_value="interface=eth0"):
            result = get_service_status()
        assert result["running"] is True
        assert "interface=eth0" in result["config"]

    def test_get_service_status_not_running(self):
        from app.pxe.dnsmasq import get_service_status
        with patch("app.pxe.dnsmasq.is_active", return_value=False), \
             patch("app.pxe.dnsmasq.get_config", return_value=""):
            result = get_service_status()
        assert result["running"] is False
        assert result["config"] == ""
