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
from .settings_menu import SettingsMenu

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
        
        # 初始化各个菜单模块
        self.send_menu = SendEmailMenu(self)
        self.receive_menu = ReceiveEmailMenu(self)
        self.view_menu = ViewEmailMenu(self)
        self.search_menu = SearchEmailMenu(self)
        self.settings_menu = SettingsMenu(self)

    def main_menu(self):
        """显示主菜单并处理用户输入"""
        while True:
            self._clear_screen()
            print("\n===== 邮件客户端 =====")
            print("1. 发送邮件")
            print("2. 接收邮件")
            print("3. 查看邮件列表")
            print("4. 搜索邮件")
            print("5. 账户设置")
            print("0. 退出")

            choice = input("\n请选择操作 [0-5]: ")

            if choice == "1":
                self.send_menu.show_menu()
            elif choice == "2":
                self.receive_menu.show_menu()
            elif choice == "3":
                self.view_menu.show_menu()
            elif choice == "4":
                self.search_menu.show_menu()
            elif choice == "5":
                self.settings_menu.show_menu()
            elif choice == "0":
                print("感谢使用，再见！")
                sys.exit(0)
            else:
                input("无效选择，请按回车键继续...")

    def _clear_screen(self):
        """清屏"""
        os.system("cls" if os.name == "nt" else "clear")

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
