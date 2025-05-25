# -*- coding: utf-8 -*-
"""
设置菜单模块
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.config import EMAIL_STORAGE_DIR, DB_PATH

# 设置日志
logger = setup_logging("settings_menu")


class SettingsMenu:
    """设置菜单"""

    def __init__(self, main_cli):
        """初始化设置菜单"""
        self.main_cli = main_cli
        self.smtp_config = None
        self.pop3_config = None

    def show_menu(self):
        """显示设置菜单"""
        while True:
            self.main_cli.clear_screen()
            print("\n===== 账户设置 =====")
            print("1. 设置SMTP服务器")
            print("2. 设置POP3服务器")
            print("3. 查看当前设置")
            print("0. 返回主菜单")

            choice = input("\n请选择操作 [0-3]: ")

            if choice == "1":
                self._set_smtp_server()
            elif choice == "2":
                self._set_pop3_server()
            elif choice == "3":
                self._view_current_settings()
            elif choice == "0":
                return
            else:
                input("无效选择，请按回车键继续...")

    def _set_smtp_server(self):
        """设置SMTP服务器"""
        self.main_cli.clear_screen()
        print("\n===== 设置SMTP服务器 =====")

        host = input("服务器地址 (默认: localhost): ") or "localhost"
        port = input("端口 (默认: 465): ") or "465"
        use_ssl = input("使用SSL (y/n, 默认: y): ").lower() != "n"
        username = input("用户名 (默认: testuser): ") or "testuser"
        
        import getpass
        password = getpass.getpass("密码 (默认: testpass): ") or "testpass"
        
        auth_method = input("认证方法 (AUTO/LOGIN/PLAIN, 默认: AUTO): ") or "AUTO"

        # 保存设置
        self.smtp_config = {
            "host": host,
            "port": int(port) if port.isdigit() else port,
            "use_ssl": use_ssl,
            "username": username,
            "password": password,
            "auth_method": auth_method,
        }

        print("\nSMTP服务器设置已保存")
        input("按回车键继续...")

    def _set_pop3_server(self):
        """设置POP3服务器"""
        self.main_cli.clear_screen()
        print("\n===== 设置POP3服务器 =====")

        host = input("服务器地址 (默认: localhost): ") or "localhost"
        port = input("端口 (默认: 995): ") or "995"
        use_ssl = input("使用SSL (y/n, 默认: y): ").lower() != "n"
        username = input("用户名 (默认: testuser): ") or "testuser"
        
        import getpass
        password = getpass.getpass("密码 (默认: testpass): ") or "testpass"
        
        auth_method = input("认证方法 (AUTO/BASIC/APOP, 默认: AUTO): ") or "AUTO"

        # 保存设置
        self.pop3_config = {
            "host": host,
            "port": int(port) if port.isdigit() else port,
            "use_ssl": use_ssl,
            "username": username,
            "password": password,
            "auth_method": auth_method,
        }

        print("\nPOP3服务器设置已保存")
        input("按回车键继续...")

    def _view_current_settings(self):
        """查看当前设置"""
        self.main_cli.clear_screen()
        print("\n===== 当前设置 =====")

        # 显示SMTP设置
        print("SMTP服务器设置:")
        if self.smtp_config:
            print(f"  服务器地址: {self.smtp_config.get('host', '')}")
            print(f"  端口: {self.smtp_config.get('port', '')}")
            print(f"  使用SSL: {'是' if self.smtp_config.get('use_ssl', True) else '否'}")
            print(f"  用户名: {self.smtp_config.get('username', '')}")
            print(f"  密码: {'已设置' if self.smtp_config.get('password') else '未设置'}")
            print(f"  认证方法: {self.smtp_config.get('auth_method', 'AUTO')}")
        else:
            print("  未设置")

        print("\nPOP3服务器设置:")
        if self.pop3_config:
            print(f"  服务器地址: {self.pop3_config.get('host', '')}")
            print(f"  端口: {self.pop3_config.get('port', '')}")
            print(f"  使用SSL: {'是' if self.pop3_config.get('use_ssl', True) else '否'}")
            print(f"  用户名: {self.pop3_config.get('username', '')}")
            print(f"  密码: {'已设置' if self.pop3_config.get('password') else '未设置'}")
            print(f"  认证方法: {self.pop3_config.get('auth_method', 'AUTO')}")
        else:
            print("  未设置")

        print("\n存储设置:")
        print(f"  邮件存储目录: {EMAIL_STORAGE_DIR}")
        print(f"  数据库路径: {DB_PATH}")

        input("\n按回车键继续...")

    def get_smtp_config(self):
        """获取SMTP配置"""
        return self.smtp_config

    def get_pop3_config(self):
        """获取POP3配置"""
        return self.pop3_config
