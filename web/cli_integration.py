# -*- coding: utf-8 -*-
"""
CLI集成服务 - 为Web界面提供CLI功能的桥接层
严格遵循最小改动原则，复用现有CLI模块和服务
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from flask_login import current_user

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cli.main_cli import EmailCLI
from cli.send_menu import SendEmailMenu
from cli.receive_menu import ReceiveEmailMenu
from cli.view_menu import ViewEmailMenu
from cli.search_menu import SearchEmailMenu
from cli.modern_settings_menu import ModernSettingsMenu
from cli.spam_menu import SpamManagementMenu
from common.utils import setup_logging

# 设置日志
logger = setup_logging("cli_integration")


class WebCLIBridge:
    """Web-CLI桥接服务，提供Web界面调用CLI功能的接口"""
    
    def __init__(self, user_email: str = None):
        """
        初始化CLI桥接服务
        
        Args:
            user_email: 当前用户邮箱，用于账户隔离
        """
        self.user_email = user_email
        self._cli = None
        self._send_menu = None
        self._receive_menu = None
        self._view_menu = None
        self._search_menu = None
        self._settings_menu = None
        self._spam_menu = None
        
        logger.info(f"初始化CLI桥接服务，用户: {user_email}")
    
    @property
    def cli(self) -> EmailCLI:
        """获取CLI实例（懒加载）"""
        if self._cli is None:
            self._cli = EmailCLI()
            logger.debug("创建EmailCLI实例")
        return self._cli
    
    @property
    def send_menu(self) -> SendEmailMenu:
        """获取发送邮件菜单实例"""
        if self._send_menu is None:
            self._send_menu = SendEmailMenu(self.cli)
            logger.debug("创建SendEmailMenu实例")
        return self._send_menu
    
    @property
    def receive_menu(self) -> ReceiveEmailMenu:
        """获取接收邮件菜单实例"""
        if self._receive_menu is None:
            self._receive_menu = ReceiveEmailMenu(self.cli)
            logger.debug("创建ReceiveEmailMenu实例")
        return self._receive_menu
    
    @property
    def view_menu(self) -> ViewEmailMenu:
        """获取查看邮件菜单实例"""
        if self._view_menu is None:
            self._view_menu = ViewEmailMenu(self.cli)
            logger.debug("创建ViewEmailMenu实例")
        return self._view_menu
    
    @property
    def search_menu(self) -> SearchEmailMenu:
        """获取搜索邮件菜单实例"""
        if self._search_menu is None:
            self._search_menu = SearchEmailMenu(self.cli)
            logger.debug("创建SearchEmailMenu实例")
        return self._search_menu
    
    @property
    def settings_menu(self) -> ModernSettingsMenu:
        """获取设置菜单实例"""
        if self._settings_menu is None:
            self._settings_menu = ModernSettingsMenu(self.cli)
            logger.debug("创建ModernSettingsMenu实例")
        return self._settings_menu
    
    @property
    def spam_menu(self) -> SpamManagementMenu:
        """获取垃圾邮件管理菜单实例"""
        if self._spam_menu is None:
            self._spam_menu = SpamManagementMenu(self.cli)
            logger.debug("创建SpamManagementMenu实例")
        return self._spam_menu
    
    def get_email_service(self):
        """获取邮件服务实例"""
        return self.cli.get_db()
    
    def get_current_account_info(self) -> Optional[Dict[str, Any]]:
        """获取当前账户信息"""
        try:
            return self.cli.get_current_account_info()
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return None
    
    def get_smtp_config(self) -> Optional[Dict[str, Any]]:
        """获取SMTP配置"""
        try:
            return self.cli.get_smtp_config()
        except Exception as e:
            logger.error(f"获取SMTP配置失败: {e}")
            return None
    
    def get_pop3_config(self) -> Optional[Dict[str, Any]]:
        """获取POP3配置"""
        try:
            return self.cli.get_pop3_config()
        except Exception as e:
            logger.error(f"获取POP3配置失败: {e}")
            return None
    
    def list_accounts(self) -> List[str]:
        """列出所有账户"""
        try:
            return self.settings_menu.account_manager.list_accounts()
        except Exception as e:
            logger.error(f"列出账户失败: {e}")
            return []
    
    def switch_account(self, account_name: str) -> bool:
        """切换账户"""
        try:
            self.settings_menu.account_manager.set_last_used(account_name)
            logger.info(f"切换到账户: {account_name}")
            return True
        except Exception as e:
            logger.error(f"切换账户失败: {e}")
            return False


def get_cli_bridge(user_email: str = None) -> WebCLIBridge:
    """
    获取CLI桥接服务实例
    
    Args:
        user_email: 用户邮箱，如果为None则尝试从current_user获取
    
    Returns:
        WebCLIBridge实例
    """
    if user_email is None and current_user.is_authenticated:
        user_email = getattr(current_user, 'email', None)
    
    return WebCLIBridge(user_email)
