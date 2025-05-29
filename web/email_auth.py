#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮箱认证系统 - 直接使用邮箱和授权码进行认证
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


class EmailUser(UserMixin):
    """邮箱用户类 - 用于Flask-Login"""

    def __init__(self, email: str, config: Dict[str, Any]):
        self.email = email
        self.config = config
        self.provider_name = config.get("provider_name", "未知")
        self.last_login = datetime.now()
        self.needs_reauth = config.get("needs_reauth", False)  # 是否需要重新认证

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

    def get_id(self):
        """返回用户ID"""
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

    def has_mail_config(self) -> bool:
        """检查是否有邮箱配置 - 对于EmailUser总是返回True"""
        return True

    def get_smtp_config(self):
        """获取SMTP配置"""
        return self.config.get("smtp", {})

    def get_pop3_config(self):
        """获取POP3配置"""
        return self.config.get("pop3", {})


class EmailAuthenticator:
    """邮箱认证器"""

    def __init__(self, db_path: str = "data/emails_dev.db"):
        """初始化认证器"""
        self.db_path = db_path
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
        认证邮箱用户

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

            # 2. 测试SMTP连接
            smtp_config = provider_config["smtp"]
            if not self._test_smtp_connection(email, password, smtp_config):
                print(f"❌ SMTP认证失败: {email}")
                return None

            # 3. 测试POP3连接（可选，某些服务商可能不支持）
            pop3_config = provider_config["pop3"]
            pop3_ok = self._test_pop3_connection(email, password, pop3_config)
            if not pop3_ok:
                print(f"⚠️  POP3连接失败，但SMTP成功: {email}")

            # 4. 保存邮箱配置
            self._save_email_account(email, password, provider_config)

            # 5. 创建用户对象
            user_config = {
                "provider_name": provider_config["name"],
                "smtp": {**smtp_config, "username": email, "password": password},
                "pop3": {**pop3_config, "username": email, "password": password},
            }

            return EmailUser(email, user_config)

        except Exception as e:
            print(f"❌ 认证过程出错: {e}")
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
        """保存邮箱账户配置"""
        try:
            from cryptography.fernet import Fernet
            import base64

            # 生成一个密钥（实际应用中应该使用更安全的密钥管理）
            # 这里使用邮箱地址的哈希作为密钥种子
            key_seed = hashlib.sha256(email.encode()).hexdigest()[:32]
            key = base64.urlsafe_b64encode(key_seed.encode().ljust(32, b"0")[:32])
            fernet = Fernet(key)

            # 加密密码
            encrypted_password = fernet.encrypt(password.encode()).decode()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 保存或更新邮箱配置（修改字段名以区分新的加密方式）
            cursor.execute(
                """
                INSERT OR REPLACE INTO email_accounts 
                (email, provider_name, encrypted_password, salt, smtp_config, pop3_config, last_login, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    email,
                    provider_config["name"],
                    encrypted_password,
                    "fernet_encrypted",  # 标记使用新的加密方式
                    str(provider_config["smtp"]),
                    str(provider_config["pop3"]),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )

            conn.commit()
            conn.close()
            print(f"✅ 邮箱配置已保存: {email}")

        except Exception as e:
            print(f"❌ 保存邮箱配置失败: {e}")
            # 如果加密失败，回退到简单方式
            salt = uuid.uuid4().hex
            encrypted_password = hashlib.sha256((password + salt).encode()).hexdigest()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO email_accounts 
                (email, provider_name, encrypted_password, salt, smtp_config, pop3_config, last_login, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    email,
                    provider_config["name"],
                    encrypted_password,
                    salt,
                    str(provider_config["smtp"]),
                    str(provider_config["pop3"]),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )

            conn.commit()
            conn.close()
            print(f"✅ 邮箱配置已保存（使用哈希）: {email}")

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

                decrypted_password = fernet.decrypt(
                    encrypted_password.encode()
                ).decode()
                return decrypted_password
            else:
                # 旧的哈希方式，无法解密
                print(f"⚠️  旧的哈希加密方式，无法解密密码: {email}")
                return None

        except Exception as e:
            print(f"❌ 解密密码失败: {e}")
            return None

    def get_saved_account(self, email: str) -> Optional[Dict]:
        """获取已保存的邮箱账户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT email, provider_name, last_login 
                FROM email_accounts 
                WHERE email = ?
            """,
                (email,),
            )

            row = cursor.fetchone()
            conn.close()

            if row:
                return {"email": row[0], "provider_name": row[1], "last_login": row[2]}
            return None

        except Exception as e:
            print(f"❌ 获取邮箱账户失败: {e}")
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

            accounts = []
            for row in cursor.fetchall():
                accounts.append(
                    {"email": row[0], "provider_name": row[1], "last_login": row[2]}
                )

            conn.close()
            return accounts

        except Exception as e:
            print(f"❌ 获取邮箱账户列表失败: {e}")
            return []


# 用于Flask-Login的用户加载器
def load_user_by_email(email: str) -> Optional[EmailUser]:
    """通过邮箱加载用户"""
    try:
        provider_config = get_provider_config(email)
        if not provider_config:
            return None

        authenticator = EmailAuthenticator()
        saved_account = authenticator.get_saved_account(email)
        if not saved_account:
            return None

        # 从数据库获取加密的密码
        try:
            conn = sqlite3.connect(authenticator.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT encrypted_password, salt 
                FROM email_accounts 
                WHERE email = ?
            """,
                (email,),
            )

            row = cursor.fetchone()
            conn.close()

            if not row:
                print(f"❌ 未找到邮箱账户的密码信息: {email}")
                return None

            encrypted_password, salt = row

            # 解密密码
            decrypted_password = authenticator._decrypt_password(
                email, encrypted_password, salt
            )

            if decrypted_password:
                # 新的加密方式，包含密码
                user_config = {
                    "provider_name": provider_config["name"],
                    "smtp": {
                        **provider_config["smtp"],
                        "username": email,
                        "password": decrypted_password,
                    },
                    "pop3": {
                        **provider_config["pop3"],
                        "username": email,
                        "password": decrypted_password,
                    },
                }

                return EmailUser(email, user_config)
            else:
                # 旧的哈希加密方式，创建一个需要重新认证的用户对象
                print(f"⚠️  旧的哈希加密账户，需要重新登录: {email}")
                user_config = {
                    "provider_name": provider_config["name"],
                    "smtp": {**provider_config["smtp"], "username": email},
                    "pop3": {**provider_config["pop3"], "username": email},
                    "needs_reauth": True,  # 标记需要重新认证
                }

                return EmailUser(email, user_config)

        except Exception as e:
            print(f"❌ 获取密码信息失败: {e}")

            # 创建基本的用户配置（不包含密码）
            user_config = {
                "provider_name": provider_config["name"],
                "smtp": provider_config["smtp"],
                "pop3": provider_config["pop3"],
                "needs_reauth": True,  # 标记需要重新认证
            }

            return EmailUser(email, user_config)

    except Exception as e:
        print(f"❌ 加载用户失败: {e}")
        return None


if __name__ == "__main__":
    # 测试
    authenticator = EmailAuthenticator()

    print("🔍 测试邮箱认证系统")
    print("请输入真实的邮箱和授权码进行测试")

    # 这里可以添加测试代码
