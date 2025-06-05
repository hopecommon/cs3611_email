"""
Web应用用户模型 - 适配Flask-Login
"""

from flask_login import UserMixin
from flask import g
from werkzeug.security import check_password_hash, generate_password_hash
import json
import base64
from cryptography.fernet import Fernet
import os


class WebUser(UserMixin):
    """Web用户类，适配Flask-Login"""

    def __init__(self, user_record):
        """
        初始化Web用户

        Args:
            user_record: server.db_models.UserRecord实例
        """
        self.user_record = user_record

        # 基本字段
        self.id = user_record.username
        self.username = user_record.username
        self.email = user_record.email
        self.full_name = user_record.full_name
        # 不直接设置 is_active，通过 user_record 访问
        self.created_at = user_record.created_at
        self.last_login = user_record.last_login

        # 邮箱配置相关字段
        self.mail_display_name = user_record.mail_display_name or ""
        self.smtp_server = user_record.smtp_server or ""
        self.smtp_port = user_record.smtp_port or 587
        self.smtp_use_tls = user_record.smtp_use_tls or True
        self.smtp_username = user_record.smtp_username or ""
        self.encrypted_smtp_password = user_record.encrypted_smtp_password or ""

        self.pop3_server = user_record.pop3_server or ""
        self.pop3_port = user_record.pop3_port or 995
        self.pop3_use_ssl = user_record.pop3_use_ssl or True
        self.pop3_username = user_record.pop3_username or ""
        self.encrypted_pop3_password = user_record.encrypted_pop3_password or ""

        # 邮箱配置状态
        self.smtp_configured = user_record.smtp_configured or False
        self.pop3_configured = user_record.pop3_configured or False

    def get_id(self):
        """返回用户唯一标识"""
        return self.username

    def has_mail_config(self):
        """检查是否已配置邮箱"""
        return self.smtp_configured and self.pop3_configured

    def get_smtp_config(self):
        """获取解密后的SMTP配置"""
        if not self.smtp_configured:
            return None

        try:
            password = self._decrypt_password(self.encrypted_smtp_password)
            return {
                "host": self.smtp_server,
                "port": self.smtp_port,
                "use_tls": self.smtp_use_tls,
                "username": self.smtp_username,
                "password": password,
            }
        except Exception:
            return None

    def get_pop3_config(self):
        """获取解密后的POP3配置"""
        if not self.pop3_configured:
            return None

        try:
            password = self._decrypt_password(self.encrypted_pop3_password)
            return {
                "host": self.pop3_server,
                "port": self.pop3_port,
                "use_ssl": self.pop3_use_ssl,
                "username": self.pop3_username,
                "password": password,
            }
        except Exception:
            return None

    def _get_encryption_key(self):
        """获取或生成加密密钥"""
        # 基于用户名生成一致的密钥
        key_material = f"{self.username}_mail_config_key".encode()
        # 使用更安全的方式生成密钥
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

        salt = b"cs3611_email_client_salt"  # 固定salt，确保密钥一致性
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(key_material))
        return Fernet(key)

    def _encrypt_password(self, password):
        """加密密码"""
        try:
            f = self._get_encryption_key()
            encrypted = f.encrypt(password.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception:
            return ""

    def _decrypt_password(self, encrypted_password):
        """解密密码"""
        try:
            f = self._get_encryption_key()
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_password.encode())
            decrypted = f.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception:
            return ""

    def update_pop3_password(self, new_password):
        """更新POP3密码"""
        try:
            # 加密新密码
            encrypted_password = self._encrypt_password(new_password)

            # 更新用户记录
            self.user_record.encrypted_pop3_password = encrypted_password

            # 如果还没有配置POP3，设置为已配置
            if not self.user_record.pop3_configured:
                self.user_record.pop3_configured = True

            # 这里应该保存到数据库，但由于当前架构限制，我们暂时只更新内存中的对象
            # TODO: 实现数据库更新逻辑

            return True
        except Exception as e:
            print(f"更新POP3密码失败: {e}")
            return False

    @staticmethod
    def authenticate(username, password):
        """
        用户认证

        Args:
            username: 用户名
            password: 密码

        Returns:
            WebUser实例或None
        """
        try:
            # 使用Flask的g对象获取用户认证服务
            user_auth = g.get("user_auth")
            if not user_auth:
                from server.user_auth import UserAuth
                from flask import current_app

                user_auth = UserAuth(current_app.config["DB_PATH"])

            user_record = user_auth.authenticate(username, password)
            if user_record:
                # user_record 是 common.models.User 对象
                # 需要转换为 server.db_models.UserRecord 对象
                from server.db_models import UserRecord

                # 将 User 对象转换为 UserRecord 对象
                user_record_data = UserRecord(
                    username=user_record.username,
                    email=user_record.email,
                    password_hash=user_record.password_hash,
                    salt=user_record.salt,
                    full_name=user_record.full_name,
                    is_active=user_record.is_active,
                    created_at=user_record.created_at,
                    last_login=user_record.last_login,
                    # 邮箱配置字段设为默认值
                    mail_display_name="",
                    smtp_server="",
                    smtp_port=587,
                    smtp_use_tls=True,
                    smtp_username="",
                    encrypted_smtp_password="",
                    pop3_server="",
                    pop3_port=995,
                    pop3_use_ssl=True,
                    pop3_username="",
                    encrypted_pop3_password="",
                    smtp_configured=False,
                    pop3_configured=False,
                )

                return WebUser(user_record_data)
            return None
        except Exception as e:
            # 记录详细错误信息用于调试
            print(f"WebUser.authenticate 错误: {e}")
            import traceback

            traceback.print_exc()
            return None

    @staticmethod
    def create(username, email, password, full_name=""):
        """
        创建新用户

        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            full_name: 全名

        Returns:
            WebUser实例或None
        """
        try:
            from server.user_auth import UserAuth
            from flask import current_app

            user_auth = UserAuth(current_app.config["DB_PATH"])
            user_record = user_auth.create_user(username, email, password, full_name)
            if user_record:
                return WebUser(user_record)
            return None
        except Exception:
            return None

    @staticmethod
    def get_by_username(username):
        """
        通过用户名获取用户

        Args:
            username: 用户名

        Returns:
            WebUser实例或None
        """
        try:
            from server.user_auth import UserAuth
            from flask import current_app

            user_auth = UserAuth(current_app.config["DB_PATH"])
            user_record = user_auth.get_user_by_username(username)
            if user_record:
                # user_record 是 common.models.User 对象
                # 需要转换为 server.db_models.UserRecord 对象
                from server.db_models import UserRecord

                # 将 User 对象转换为 UserRecord 对象
                user_record_data = UserRecord(
                    username=user_record.username,
                    email=user_record.email,
                    password_hash=user_record.password_hash,
                    salt=user_record.salt,
                    full_name=user_record.full_name,
                    is_active=user_record.is_active,
                    created_at=user_record.created_at,
                    last_login=user_record.last_login,
                    # 邮箱配置字段设为默认值
                    mail_display_name="",
                    smtp_server="",
                    smtp_port=587,
                    smtp_use_tls=True,
                    smtp_username="",
                    encrypted_smtp_password="",
                    pop3_server="",
                    pop3_port=995,
                    pop3_use_ssl=True,
                    pop3_username="",
                    encrypted_pop3_password="",
                    smtp_configured=False,
                    pop3_configured=False,
                )

                return WebUser(user_record_data)
            return None
        except Exception as e:
            print(f"WebUser.get_by_username 错误: {e}")
            import traceback

            traceback.print_exc()
            return None

    def __repr__(self):
        return f"<WebUser {self.username}>"

    @property
    def is_active(self):
        """是否活跃用户 (Flask-Login需要)"""
        return self.user_record.is_active

    @property
    def is_authenticated(self):
        """是否已认证 (Flask-Login需要)"""
        return True

    @property
    def is_anonymous(self):
        """是否匿名用户 (Flask-Login需要)"""
        return False

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": self.user_record.id,
            "username": self.user_record.username,
            "email": self.user_record.email,
            "full_name": self.user_record.full_name,
            "is_active": self.user_record.is_active,
            "created_at": self.user_record.created_at,
            "last_login": self.user_record.last_login,
            "mail_display_name": self.mail_display_name,
            "smtp_server": self.smtp_server,
            "smtp_port": self.smtp_port,
            "smtp_use_tls": self.smtp_use_tls,
            "smtp_username": self.smtp_username,
            "encrypted_smtp_password": self.encrypted_smtp_password,
            "pop3_server": self.pop3_server,
            "pop3_port": self.pop3_port,
            "pop3_use_ssl": self.pop3_use_ssl,
            "pop3_username": self.pop3_username,
            "encrypted_pop3_password": self.encrypted_pop3_password,
            "smtp_configured": self.smtp_configured,
            "pop3_configured": self.pop3_configured,
        }
