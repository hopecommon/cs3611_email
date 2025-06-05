#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的邮箱认证模块 - 直接使用SMTP/POP3验证
"""

import sys
import datetime
from pathlib import Path
import hashlib

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask_login import UserMixin
from email_providers_config import get_provider_config, is_supported_provider
from client.smtp_client import SMTPClient
from client.pop3_client_refactored import POP3ClientRefactored
from common.utils import setup_logging

# 设置日志
logger = setup_logging("simple_email_auth")


class SimpleEmailUser(UserMixin):
    """简化的邮箱用户类"""

    def __init__(self, email, password, provider_config):
        self.email = email
        self.password = password
        self.provider_config = provider_config
        self.provider_name = provider_config["name"]
        self.last_login = datetime.datetime.now()

        # 直接使用邮箱地址作为ID，方便Flask-Login会话管理
        self.id = email

    def get_id(self):
        """Flask-Login要求的方法"""
        return self.id

    def is_authenticated(self):
        """用户是否已认证"""
        return True

    def is_active(self):
        """用户是否激活"""
        return True

    def is_anonymous(self):
        """用户是否匿名"""
        return False

    def get_smtp_config(self):
        """获取SMTP配置"""
        if not self.provider_config:
            return None

        smtp_config = self.provider_config.get("smtp", {})
        return {
            "host": smtp_config["host"],
            "port": smtp_config["port"],
            "use_ssl": smtp_config.get("use_ssl", smtp_config.get("use_tls", False)),
            "username": self.email,
            "password": self.password,
            "auth_method": "AUTO",
        }

    def get_pop3_config(self):
        """获取POP3配置"""
        if not self.provider_config:
            return None

        pop3_config = self.provider_config.get("pop3", {})
        return {
            "host": pop3_config["host"],
            "port": pop3_config["port"],
            "use_ssl": pop3_config.get("use_ssl", True),
            "username": self.email,
            "password": self.password,
            "auth_method": "AUTO",
        }


def authenticate_simple_email_user(email, password):
    """
    简化的邮箱用户认证 - 直接通过SMTP/POP3连接验证

    Args:
        email: 邮箱地址
        password: 密码或授权码

    Returns:
        SimpleEmailUser对象或None
    """
    try:
        # 检查是否支持该邮箱服务商
        if not is_supported_provider(email):
            logger.warning(f"不支持的邮箱服务商: {email}")
            return None

        # 获取邮箱服务商配置
        provider_config = get_provider_config(email)
        if not provider_config:
            logger.error(f"无法获取邮箱服务商配置: {email}")
            return None

        logger.info(f"开始认证邮箱用户: {email} ({provider_config['name']})")

        # 尝试SMTP连接验证（优先，因为大多数邮箱都支持）
        smtp_success = False
        try:
            smtp_config = provider_config.get("smtp", {})
            if smtp_config:
                logger.debug(
                    f"尝试SMTP连接: {smtp_config['host']}:{smtp_config['port']}"
                )

                smtp_client = SMTPClient(
                    host=smtp_config["host"],
                    port=smtp_config["port"],
                    use_ssl=smtp_config.get(
                        "use_ssl", smtp_config.get("use_tls", False)
                    ),
                    username=email,
                    password=password,
                    auth_method="AUTO",
                    timeout=10,
                )

                # 连接并认证
                smtp_client.connect()
                smtp_client.disconnect()
                smtp_success = True
                logger.info(f"SMTP认证成功: {email}")

        except Exception as smtp_e:
            logger.debug(f"SMTP认证失败: {smtp_e}")
            smtp_success = False

        # 如果SMTP失败，尝试POP3连接验证
        pop3_success = False
        if not smtp_success:
            try:
                pop3_config = provider_config.get("pop3", {})
                if pop3_config:
                    logger.debug(
                        f"尝试POP3连接: {pop3_config['host']}:{pop3_config['port']}"
                    )

                    pop3_client = POP3ClientRefactored(
                        host=pop3_config["host"],
                        port=pop3_config["port"],
                        use_ssl=pop3_config.get("use_ssl", True),
                        username=email,
                        password=password,
                        auth_method="AUTO",
                        timeout=10,
                    )

                    # 连接并认证
                    pop3_client.connect()
                    pop3_client.disconnect()
                    pop3_success = True
                    logger.info(f"POP3认证成功: {email}")

            except Exception as pop3_e:
                logger.debug(f"POP3认证失败: {pop3_e}")
                pop3_success = False

        # 如果任一认证成功，创建用户对象
        if smtp_success or pop3_success:
            user = SimpleEmailUser(email, password, provider_config)
            logger.info(f"用户认证成功: {email}")
            return user
        else:
            logger.warning(f"所有认证方式都失败: {email}")
            return None

    except Exception as e:
        logger.error(f"认证过程异常: {email} - {e}")
        return None


def load_user_by_email(email):
    """
    Flask-Login用户加载器 - 简化版本

    Args:
        email: 邮箱地址

    Returns:
        SimpleEmailUser对象或None
    """
    # 注意：这里不进行实际的密码验证，只是为了Flask-Login会话管理
    # 实际的认证在登录时进行
    if not email or not is_supported_provider(email):
        return None

    provider_config = get_provider_config(email)
    if not provider_config:
        return None

    # 创建一个临时用户对象（密码为空，仅用于会话管理）
    user = SimpleEmailUser(email, "", provider_config)
    return user


def get_user_by_id(user_id):
    """
    通过用户ID获取用户（Flask-Login需要）

    Args:
        user_id: 用户ID（邮箱地址）

    Returns:
        SimpleEmailUser对象或None
    """
    # 由于用户ID就是邮箱地址，直接调用load_user_by_email
    return load_user_by_email(user_id)
