"""iPXE 引导菜单语法验证测试"""
from app.pxe.ipxe import generate_menu


class TestIpxeMenu:
    """iPXE 菜单生成测试"""

    def test_basic_menu(self):
        menu = generate_menu()
        assert "#!ipxe" in menu
        assert "install-ubuntu" in menu
        assert ":install-ubuntu" in menu

    def test_menu_with_isos(self):
        isos = [
            {"name": "Ubuntu 22.04", "local_path": "/iso/ubuntu.iso"},
            {"name": "CentOS 9", "local_path": "/iso/centos.iso"},
        ]
        menu = generate_menu(isos=isos)
        assert "Install Ubuntu 22.04" in menu
        assert "Install CentOS 9" in menu
        assert ":install-ubuntu-22.04" in menu
        assert ":install-centos-9" in menu

    def test_menu_with_hosts(self):
        hosts = [
            {"hostname": "srv01", "mac_address": "AA:BB:CC:DD:EE:01"},
            {"hostname": "srv02", "mac_address": "AA:BB:CC:DD:EE:02"},
        ]
        menu = generate_menu(hosts=hosts)
        assert "Boot srv01" in menu
        assert "Boot srv02" in menu
        assert ":boot-srv01" in menu
        assert ":boot-srv02" in menu

    def test_menu_syntax(self):
        menu = generate_menu()
        lines = menu.splitlines()
        assert lines[0] == "#!ipxe"
        assert ":menu" in menu
        assert "goto menu" in menu
        assert ":shell" in menu
