#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮箱认证系统 - 支持第三方邮箱登录
"""

import smtplib
import poplib
import sqlite3
import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import sys

from flask_login import UserMixin

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 导入邮箱服务商配置
try:
    from email_providers_config import get_provider_config, is_supported_provider
except ImportError:
    # 使用绝对路径导入
    import importlib.util

    config_path = project_root / "email_providers_config.py"
    spec = importlib.util.spec_from_file_location("email_providers_config", config_path)
    email_providers_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(email_providers_config)
    get_provider_config = email_providers_config.get_provider_config
    is_supported_provider = email_providers_config.is_supported_provider

# 导入统一配置
from common.config import DB_PATH as MAIN_DB_PATH

# 支持的邮箱服务商配置
EMAIL_PROVIDERS = {
    "qq.com": {
        "name": "QQ邮箱",
        "smtp": {"host": "smtp.qq.com", "port": 587, "use_tls": True},
        "pop3": {"host": "pop.qq.com", "port": 995, "use_ssl": True},
    },
    "163.com": {
        "name": "网易163邮箱",
        "smtp": {"host": "smtp.163.com", "port": 994, "use_ssl": True},
        "pop3": {"host": "pop.163.com", "port": 995, "use_ssl": True},
    },
    "126.com": {
        "name": "网易126邮箱",
        "smtp": {"host": "smtp.126.com", "port": 994, "use_ssl": True},
        "pop3": {"host": "pop.126.com", "port": 995, "use_ssl": True},
    },
    "gmail.com": {
        "name": "Gmail",
        "smtp": {"host": "smtp.gmail.com", "port": 587, "use_tls": True},
        "pop3": {"host": "pop.gmail.com", "port": 995, "use_ssl": True},
    },
    "outlook.com": {
        "name": "Outlook",
        "smtp": {"host": "smtp-mail.outlook.com", "port": 587, "use_tls": True},
        "pop3": {"host": "outlook.office365.com", "port": 995, "use_ssl": True},
    },
    "hotmail.com": {
        "name": "Hotmail",
        "smtp": {"host": "smtp-mail.outlook.com", "port": 587, "use_tls": True},
        "pop3": {"host": "outlook.office365.com", "port": 995, "use_ssl": True},
    },
}


def get_provider_config(email: str) -> Optional[Dict]:
    """根据邮箱地址获取服务商配置"""
    domain = email.split("@")[-1].lower()
    return EMAIL_PROVIDERS.get(domain)


class EmailUser(UserMixin):
    """邮箱用户类，用于Flask-Login"""

    def __init__(self, email: str, config: Dict[str, Any]):
        self.email = email
        self.config = config
        self.provider_name = config.get("provider_name", "未知邮箱")
        self.last_login = datetime.now()

        # 兼容性：为了与WebUser保持接口一致
        self.username = email  # 用邮箱作为用户名
        self.mail_display_name = email

        # SMTP配置
        smtp_config = config.get("smtp", {})
        self.smtp_server = smtp_config.get("host", "")
        self.smtp_port = smtp_config.get("port", 587)
        self.smtp_use_tls = smtp_config.get("use_tls", True)
        self.smtp_username = email

        # POP3配置
        pop3_config = config.get("pop3", {})
        self.pop3_server = pop3_config.get("host", "")
        self.pop3_port = pop3_config.get("port", 995)
        self.pop3_use_ssl = pop3_config.get("use_ssl", True)
        self.pop3_username = email

    def __repr__(self):
        return f"<EmailUser {self.email}>"

    def get_id(self):
        """返回用户唯一标识 - Flask-Login要求的方法"""
        return self.email

    @property
    def is_authenticated(self):
        """用户是否已认证"""
        return True

    @property
    def is_active(self):
        """用户是否激活"""
        return True

    @property
    def is_anonymous(self):
        """用户是否匿名"""
        return False

    @property
    def needs_reauth(self) -> bool:
        """检查是否需要重新认证"""
        return self.config.get("needs_reauth", False)

    def has_mail_config(self) -> bool:
        """检查是否有邮箱配置 - 对于EmailUser总是返回True"""
        return True

    def get_smtp_config(self):
        """获取SMTP配置 - 简化版本"""
        return self.config.get("smtp", {}).copy()

    def get_pop3_config(self):
        """获取POP3配置 - 简化版本"""
        return self.config.get("pop3", {}).copy()

    def update_pop3_password(self, new_password: str) -> bool:
        """
        更新POP3密码 - 简化版本

        Args:
            new_password: 新密码/授权码

        Returns:
            bool: 更新成功返回True，失败返回False
        """
        try:
            # 1. 验证新密码是否有效
            pop3_config = self.config.get("pop3", {})
            if not self._test_pop3_connection_with_password(new_password, pop3_config):
                print(f"❌ POP3密码验证失败: {self.email}")
                return False

            # 2. 更新配置中的密码
            self.config["pop3"]["password"] = new_password
            self.config["smtp"]["password"] = new_password  # 通常SMTP和POP3使用相同密码

            # 3. 清除需要重新认证的标记
            if "needs_reauth" in self.config:
                del self.config["needs_reauth"]

            print(f"✅ POP3密码更新成功: {self.email}")
            return True

        except Exception as e:
            print(f"❌ 更新POP3密码失败: {e}")
            return False

    def _test_pop3_connection_with_password(
        self, password: str, pop3_config: Dict
    ) -> bool:
        """使用指定密码测试POP3连接"""
        try:
            import poplib

            if pop3_config.get("use_ssl"):
                server = poplib.POP3_SSL(pop3_config["host"], pop3_config["port"])
            else:
                server = poplib.POP3(pop3_config["host"], pop3_config["port"])

            server.user(self.email)
            server.pass_(password)
            server.quit()
            print(f"✅ POP3密码验证成功: {self.email}")
            return True
        except Exception as e:
            print(f"❌ POP3密码验证失败: {e}")
            return False


class EmailAuthenticator:
    """邮箱认证器"""

    def __init__(self, db_path: str = None):
        """初始化认证器"""
        # 使用统一配置中的数据库路径，除非明确指定
        if db_path is None:
            self.db_path = MAIN_DB_PATH
        else:
            self.db_path = db_path

        print(f"📊 邮箱认证系统使用数据库: {self.db_path}")
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建邮箱账户表
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS email_accounts (
                email TEXT PRIMARY KEY,
                provider_name TEXT NOT NULL,
                encrypted_password TEXT NOT NULL,
                salt TEXT NOT NULL,
                smtp_config TEXT NOT NULL,
                pop3_config TEXT NOT NULL,
                last_login TEXT,
                created_at TEXT NOT NULL
            )
        """
        )

        conn.commit()
        conn.close()

    def authenticate(self, email: str, password: str) -> Optional[EmailUser]:
        """
        认证邮箱用户 - 简化版本，参考CLI实现

        Args:
            email: 邮箱地址
            password: 密码/授权码

        Returns:
            成功返回EmailUser，失败返回None
        """
        try:
            # 1. 检查是否支持该邮箱服务商
            provider_config = get_provider_config(email)
            if not provider_config:
                print(f"❌ 不支持的邮箱服务商: {email}")
                return None

            # 2. 简化认证：只测试SMTP连接（参考CLI实现）
            smtp_config = provider_config["smtp"]
            if not self._test_smtp_connection(email, password, smtp_config):
                print(f"❌ SMTP认证失败: {email}")
                return None

            print(f"✅ SMTP认证成功: {email}")

            # 3. 创建用户对象（直接使用密码，不保存到数据库）
            user_config = {
                "provider_name": provider_config["name"],
                "smtp": {**smtp_config, "username": email, "password": password},
                "pop3": {
                    **provider_config["pop3"],
                    "username": email,
                    "password": password,
                },
            }

            return EmailUser(email, user_config)

        except Exception as e:
            print(f"❌ 认证过程出错: {e}")
            import traceback

            traceback.print_exc()
            return None

    def _test_smtp_connection(
        self, email: str, password: str, smtp_config: Dict
    ) -> bool:
        """测试SMTP连接"""
        try:
            server = smtplib.SMTP(smtp_config["host"], smtp_config["port"])
            if smtp_config.get("use_tls"):
                server.starttls()
            server.login(email, password)
            server.quit()
            print(f"✅ SMTP连接测试成功: {email}")
            return True
        except Exception as e:
            print(f"❌ SMTP连接测试失败: {e}")
            return False

    def _test_pop3_connection(
        self, email: str, password: str, pop3_config: Dict
    ) -> bool:
        """测试POP3连接"""
        try:
            if pop3_config.get("use_ssl"):
                server = poplib.POP3_SSL(pop3_config["host"], pop3_config["port"])
            else:
                server = poplib.POP3(pop3_config["host"], pop3_config["port"])

            server.user(email)
            server.pass_(password)
            server.quit()
            print(f"✅ POP3连接测试成功: {email}")
            return True
        except Exception as e:
            print(f"❌ POP3连接测试失败: {e}")
            return False

    def _save_email_account(self, email: str, password: str, provider_config: Dict):
        """保存邮箱账户配置（只保存邮箱地址和配置，不保存密码）"""
        try:
            import json

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 只保存邮箱配置，不保存密码（为了安全和用户体验）
            cursor.execute(
                """
                INSERT OR REPLACE INTO email_accounts
                (email, provider_name, encrypted_password, salt, smtp_config, pop3_config, last_login, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    email,
                    provider_config["name"],
                    "",  # 不保存密码
                    "no_password_saved",  # 标记不保存密码
                    json.dumps(provider_config["smtp"]),  # 使用JSON格式
                    json.dumps(provider_config["pop3"]),  # 使用JSON格式
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )

            conn.commit()
            conn.close()
            print(f"✅ 邮箱配置已保存（不含密码）: {email}")

        except Exception as e:
            print(f"❌ 保存邮箱配置失败: {e}")
            import traceback

            traceback.print_exc()

    def _decrypt_password(
        self, email: str, encrypted_password: str, salt: str
    ) -> Optional[str]:
        """解密密码"""
        try:
            if salt == "fernet_encrypted":
                # 使用Fernet解密
                from cryptography.fernet import Fernet
                import base64

                key_seed = hashlib.sha256(email.encode()).hexdigest()[:32]
                key = base64.urlsafe_b64encode(key_seed.encode().ljust(32, b"0")[:32])
                fernet = Fernet(key)

                return fernet.decrypt(encrypted_password.encode()).decode()
            else:
                # 旧的哈希方式无法解密，返回None
                return None

        except Exception as e:
            print(f"❌ 解密密码失败: {e}")
            return None

    def get_saved_account(self, email: str) -> Optional[Dict]:
        """获取已保存的邮箱账户"""
        try:
            import json

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT provider_name, smtp_config, pop3_config
                FROM email_accounts WHERE email = ?
            """,
                (email,),
            )

            result = cursor.fetchone()
            conn.close()

            if not result:
                return None

            provider_name, smtp_config, pop3_config = result

            try:
                # 尝试JSON解析
                smtp_config_dict = json.loads(smtp_config)
                pop3_config_dict = json.loads(pop3_config)
            except json.JSONDecodeError:
                # 如果JSON解析失败，尝试eval（向后兼容）
                try:
                    smtp_config_dict = eval(smtp_config)
                    pop3_config_dict = eval(pop3_config)
                except Exception as eval_e:
                    print(f"❌ 配置解析失败: {eval_e}")
                    return None

            return {
                "email": email,
                "provider_name": provider_name,
                "smtp_config": smtp_config_dict,
                "pop3_config": pop3_config_dict,
                # 不返回密码，需要用户重新输入
            }

        except Exception as e:
            print(f"❌ 获取保存的账户失败: {e}")
            import traceback

            traceback.print_exc()
            return None

    def list_saved_accounts(self) -> list:
        """列出所有已保存的邮箱账户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT email, provider_name, last_login
                FROM email_accounts
                ORDER BY last_login DESC
            """
            )

            results = cursor.fetchall()
            conn.close()

            return [
                {"email": email, "provider_name": provider, "last_login": last_login}
                for email, provider, last_login in results
            ]

        except Exception as e:
            print(f"❌ 获取账户列表失败: {e}")
            return []


# 用于Flask-Login的用户加载器
def load_user_by_email(email: str) -> Optional[EmailUser]:
    """通过邮箱加载用户 - 简化版本，需要重新登录"""
    # 简化：不支持会话恢复，用户需要重新登录
    return None


# 创建全局认证器实例
email_authenticator = EmailAuthenticator()


def authenticate_email_user(email: str, password: str) -> Optional[EmailUser]:
    """
    认证邮箱用户（全局函数接口）

    Args:
        email: 邮箱地址
        password: 密码/授权码

    Returns:
        成功返回EmailUser，失败返回None
    """
    return email_authenticator.authenticate(email, password)


def get_email_user(email: str) -> Optional[EmailUser]:
    """
    获取已保存的邮箱用户（全局函数接口）

    Args:
        email: 邮箱地址

    Returns:
        如果有保存的配置返回EmailUser，否则返回None
    """
    return load_user_by_email(email)


def list_email_accounts() -> list:
    """列出所有保存的邮箱账户"""
    return email_authenticator.list_saved_accounts()


if __name__ == "__main__":
    # 测试
    authenticator = EmailAuthenticator()

    print("🔍 测试邮箱认证系统")
    print("请输入真实的邮箱和授权码进行测试")

    # 这里可以添加测试代码
