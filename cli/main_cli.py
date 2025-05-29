#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主CLI控制器 - 提供基于菜单的邮件客户端操作界面
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from server.new_db_handler import EmailService
from .send_menu import SendEmailMenu
from .receive_menu import ReceiveEmailMenu
from .view_menu import ViewEmailMenu
from .search_menu import SearchEmailMenu
from .modern_settings_menu import ModernSettingsMenu
from .spam_menu import SpamManagementMenu

# 设置日志
logger = setup_logging("cli")


class EmailCLI:
    """邮件客户端命令行界面"""

    def __init__(self):
        """初始化命令行界面"""
        self.db = EmailService()
        self.current_email = None
        self.email_list = []
        self.current_folder = "inbox"

        # 初始化现代化设置菜单
        self.settings_menu = ModernSettingsMenu(self)

        # 初始化其他菜单模块
        self.send_menu = SendEmailMenu(self)
        self.receive_menu = ReceiveEmailMenu(self)
        self.view_menu = ViewEmailMenu(self)
        self.search_menu = SearchEmailMenu(self)
        self.spam_menu = SpamManagementMenu(self)

    def main_menu(self):
        """显示主菜单并处理用户输入"""
        # 首次启动检查
        self._check_first_run()

        while True:
            self._clear_screen()
            self._show_welcome_header()

            # 显示当前账户状态
            self._show_account_status()

            print("\n" + "=" * 60)
            print("📋 主菜单")
            print("=" * 60)
            print("1. 📤 发送邮件")
            print("2. 📥 接收邮件")
            print("3. 📋 查看邮件列表")
            print("4. 🔍 搜索邮件")
            print("5. ⚙️  账户设置")
            print("6. 📊 系统状态")
            print("7. 🛡️  垃圾邮件管理")
            print("0. 👋 退出程序")
            print("=" * 60)

            choice = input("\n请选择操作 [0-7]: ").strip()

            if choice == "1":
                self._handle_send_email()
            elif choice == "2":
                self._handle_receive_email()
            elif choice == "3":
                self.view_menu.show_menu()
            elif choice == "4":
                self.search_menu.show_menu()
            elif choice == "5":
                self.settings_menu.show_menu()
            elif choice == "6":
                self._show_system_status()
            elif choice == "7":
                self.spam_menu.show_menu()
            elif choice == "0":
                self._exit_program()
            else:
                input("❌ 无效选择，请按回车键继续...")

    def _check_first_run(self):
        """检查是否首次运行"""
        accounts = self.settings_menu.account_manager.list_accounts()
        if not accounts:
            self._clear_screen()
            print("\n" + "=" * 60)
            print("🎉 欢迎使用邮件客户端!")
            print("=" * 60)
            print("检测到这是您首次使用本程序。")
            print("为了开始使用邮件功能，您需要先配置邮箱账户。")
            print("\n💡 提示:")
            print("• 支持QQ邮箱、Gmail、163邮箱等主流邮件服务商")
            print("• 提供自动配置功能，简化设置过程")
            print("• 密码采用加密存储，保护您的隐私")

            setup_now = input("\n是否现在设置邮箱账户? (Y/n): ").strip().lower()
            if setup_now not in ["n", "no"]:
                print("\n🚀 正在启动账户设置向导...")
                input("按回车键继续...")
                self.settings_menu._add_account_wizard()

    def _show_welcome_header(self):
        """显示欢迎头部"""
        print("\n" + "=" * 60)
        print("📧 邮件客户端")
        print("=" * 60)

    def _show_account_status(self):
        """显示当前账户状态"""
        current_account_config = self.settings_menu.get_current_account_config()
        if current_account_config:
            account_name = self.settings_menu.account_manager.get_default_account()
            email = current_account_config["email"]
            display_name = current_account_config.get("display_name", account_name)

            print(f"👤 当前账户: {display_name} ({email})")
            print(f"📊 连接状态: ✅ 已配置")
        else:
            print("👤 当前账户: 未配置")
            print("📊 连接状态: ❌ 需要设置")
            print("💡 提示: 请先在 '账户设置' 中添加邮箱账户")

    def _handle_send_email(self):
        """处理发送邮件"""
        # 检查是否有配置的账户
        if not self.settings_menu.get_current_account_config():
            self._clear_screen()
            print("\n❌ 发送邮件失败")
            print("原因: 尚未配置邮箱账户")
            print("\n💡 解决方案:")
            print("1. 进入 '账户设置' 菜单")
            print("2. 添加您的邮箱账户")
            print("3. 配置完成后即可发送邮件")

            setup_now = input("\n是否现在设置账户? (Y/n): ").strip().lower()
            if setup_now not in ["n", "no"]:
                self.settings_menu._add_account_wizard()
            else:
                input("按回车键返回主菜单...")
            return

        self.send_menu.show_menu()

    def _handle_receive_email(self):
        """处理接收邮件"""
        # 检查是否有配置的账户
        if not self.settings_menu.get_current_account_config():
            self._clear_screen()
            print("\n❌ 接收邮件失败")
            print("原因: 尚未配置邮箱账户")
            print("\n💡 解决方案:")
            print("1. 进入 '账户设置' 菜单")
            print("2. 添加您的邮箱账户")
            print("3. 配置完成后即可接收邮件")

            setup_now = input("\n是否现在设置账户? (Y/n): ").strip().lower()
            if setup_now not in ["n", "no"]:
                self.settings_menu._add_account_wizard()
            else:
                input("按回车键返回主菜单...")
            return

        self.receive_menu.show_menu()

    def _show_system_status(self):
        """显示系统状态"""
        self._clear_screen()
        print("\n" + "=" * 60)
        print("📊 系统状态")
        print("=" * 60)

        # 账户统计
        accounts = self.settings_menu.account_manager.list_accounts()
        print(f"📧 已配置账户: {len(accounts)} 个")

        if accounts:
            current_account = self.settings_menu.account_manager.get_default_account()
            print(f"🎯 当前默认账户: {current_account}")

            # 显示账户列表
            print(f"\n📋 账户列表:")
            for i, account_name in enumerate(accounts, 1):
                account_info = self.settings_menu.account_manager.get_account(
                    account_name
                )
                status = "🎯" if account_name == current_account else "  "
                print(f"   {i}. {status} {account_name} ({account_info['email']})")

        # 数据库统计
        try:
            # 这里可以添加邮件数量统计
            print(f"\n📊 邮件统计:")
            print(f"   📥 收件箱: -- 封")
            print(f"   📤 已发送: -- 封")
            print(f"   🗑️  垃圾箱: -- 封")
        except Exception as e:
            print(f"\n❌ 无法获取邮件统计: {e}")

        # 系统信息
        print(f"\n🖥️  系统信息:")
        print(f"   💾 配置目录: {self.settings_menu.account_manager.config_dir}")
        print(f"   📁 数据目录: {Path.cwd()}")
        print(f"   🐍 Python版本: {sys.version.split()[0]}")

        input("\n按回车键返回主菜单...")

    def _exit_program(self):
        """退出程序"""
        self._clear_screen()
        print("\n" + "=" * 60)
        print("👋 感谢使用邮件客户端!")
        print("=" * 60)
        print("程序即将退出...")
        print("\n💡 提示:")
        print("• 您的账户配置已安全保存")
        print("• 下次启动时将自动加载配置")
        print("• 如有问题，请查看帮助文档")

        print("\n🎉 再见!")
        sys.exit(0)

    def _clear_screen(self):
        """清屏"""
        os.system("cls" if os.name == "nt" else "clear")

    # 保持向后兼容的方法
    def get_db(self):
        """获取数据库服务"""
        return self.db

    def set_current_email(self, email):
        """设置当前选中的邮件"""
        self.current_email = email

    def get_current_email(self):
        """获取当前选中的邮件"""
        return self.current_email

    def set_email_list(self, email_list):
        """设置邮件列表"""
        self.email_list = email_list

    def get_email_list(self):
        """获取邮件列表"""
        return self.email_list

    def set_current_folder(self, folder):
        """设置当前文件夹"""
        self.current_folder = folder

    def get_current_folder(self):
        """获取当前文件夹"""
        return self.current_folder

    def clear_screen(self):
        """公共清屏方法"""
        self._clear_screen()

    # 新增方法：为其他模块提供配置访问
    def get_smtp_config(self):
        """获取当前账户的SMTP配置"""
        return self.settings_menu.get_smtp_config()

    def get_pop3_config(self):
        """获取当前账户的POP3配置"""
        return self.settings_menu.get_pop3_config()

    def get_current_account_info(self):
        """获取当前账户信息"""
        return self.settings_menu.get_current_account_config()

    def get_current_account(self):
        """获取当前账户信息 - 为账户隔离功能提供支持"""
        account_config = self.settings_menu.get_current_account_config()
        if account_config:
            # 返回包含必要字段的账户信息
            return {
                "email": account_config["email"],
                "display_name": account_config.get("display_name", ""),
                "account_name": self.settings_menu.account_manager.get_default_account(),
            }
        return None
