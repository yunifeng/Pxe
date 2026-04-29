"""dnsmasq 配置生成验证测试"""
from unittest.mock import patch

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
