# -*- coding: utf-8 -*-
"""
账户管理器 - 负责用户邮箱账户的管理和持久化存储
"""

import os
import json
import base64
import getpass
from pathlib import Path
from typing import Dict, List, Optional, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# 添加项目根目录到Python路径
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging

# 设置日志
logger = setup_logging("account_manager")


class AccountManager:
    """账户管理器"""

    def __init__(self):
        """初始化账户管理器"""
        self.config_dir = Path.home() / ".email_client"
        self.accounts_file = self.config_dir / "accounts.json"
        self.key_file = self.config_dir / "key.key"

        # 确保配置目录存在
        self.config_dir.mkdir(exist_ok=True)

        # 初始化加密密钥
        self._init_encryption()

        # 加载账户数据
        self.accounts = self._load_accounts()

    def _init_encryption(self):
        """初始化加密密钥"""
        try:
            if self.key_file.exists():
                # 尝试加载现有密钥文件
                try:
                    with open(self.key_file, "r", encoding="utf-8") as f:
                        key_data = json.load(f)
                        if "key" in key_data:
                            # 新格式：JSON格式的密钥文件
                            key_b64 = key_data["key"]
                            self.key = base64.urlsafe_b64decode(key_b64.encode())
                        else:
                            # 处理格式错误，重新生成
                            raise ValueError("Invalid key file format")
                except (json.JSONDecodeError, KeyError, ValueError):
                    # 如果是旧格式或损坏的文件，尝试直接读取
                    try:
                        with open(self.key_file, "rb") as f:
                            self.key = f.read()
                            # 验证密钥长度
                            if len(self.key) != 32:
                                raise ValueError("Invalid key length")
                    except:
                        # 文件损坏，删除并重新生成
                        logger.warning("密钥文件损坏，将重新生成")
                        self.key_file.unlink()
                        return self._init_encryption()
            else:
                # 生成新密钥
                print("🔐 首次使用，需要设置主密码来保护您的账户信息")
                password = getpass.getpass("请设置主密码: ").encode()
                if len(password) == 0:
                    print("⚠️  密码不能为空，使用默认密码")
                    password = b"default_password_please_change"

                salt = os.urandom(16)
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = kdf.derive(password)

                # 保存密钥和盐到JSON格式
                key_data = {
                    "key": base64.urlsafe_b64encode(key).decode(),
                    "salt": base64.urlsafe_b64encode(salt).decode(),
                    "version": "2.0",
                }

                with open(self.key_file, "w", encoding="utf-8") as f:
                    json.dump(key_data, f, indent=2)

                self.key = key

            self.cipher = Fernet(self.key)

        except Exception as e:
            logger.error(f"初始化加密失败: {e}")
            # 使用临时密钥（不安全，仅用于测试）
            logger.warning("使用临时密钥，请重新设置账户")
            self.key = Fernet.generate_key()
            self.cipher = Fernet(self.key)

    def _encrypt_password(self, password: str) -> str:
        """加密密码"""
        try:
            encrypted = self.cipher.encrypt(password.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"密码加密失败: {e}")
            return password  # 返回原密码（不安全）

    def _decrypt_password(self, encrypted_password: str) -> str:
        """解密密码"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_password.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception:
            # 当密码已经是明文时，解密会失败。这是一种预期的兼容行为。
            logger.debug(f"无法解密密码，假定其为明文。")
            return encrypted_password  # 返回原密码

    def _load_accounts(self) -> Dict[str, Any]:
        """加载账户数据"""
        try:
            if self.accounts_file.exists():
                with open(self.accounts_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"加载账户数据失败: {e}")
            return {}

    def _save_accounts(self):
        """保存账户数据"""
        try:
            with open(self.accounts_file, "w", encoding="utf-8") as f:
                json.dump(self.accounts, f, ensure_ascii=False, indent=2)
            logger.info("账户数据保存成功")
        except Exception as e:
            logger.error(f"保存账户数据失败: {e}")

    def add_account(
        self,
        account_name: str,
        email: str,
        password: str,
        smtp_config: Dict,
        pop3_config: Dict,
        display_name: str = "",
        notes: str = "",
    ) -> bool:
        """添加账户"""
        try:
            # 加密密码
            encrypted_password = self._encrypt_password(password)

            account_data = {
                "email": email,
                "password": encrypted_password,
                "display_name": display_name or email.split("@")[0],
                "smtp": smtp_config,
                "pop3": pop3_config,
                "notes": notes,
                "created_at": str(Path().resolve()),
                "last_used": None,
            }

            self.accounts[account_name] = account_data
            self._save_accounts()

            logger.info(f"账户 {account_name} 添加成功")
            return True

        except Exception as e:
            logger.error(f"添加账户失败: {e}")
            return False

    def get_account(self, account_name: str) -> Optional[Dict]:
        """获取账户信息"""
        try:
            if account_name in self.accounts:
                account = self.accounts[account_name].copy()
                # 解密密码
                account["password"] = self._decrypt_password(account["password"])
                return account
            return None
        except Exception as e:
            logger.error(f"获取账户信息失败: {e}")
            return None

    def list_accounts(self) -> List[str]:
        """列出所有账户名"""
        return list(self.accounts.keys())

    def remove_account(self, account_name: str) -> bool:
        """删除账户"""
        try:
            if account_name in self.accounts:
                del self.accounts[account_name]
                self._save_accounts()
                logger.info(f"账户 {account_name} 删除成功")
                return True
            return False
        except Exception as e:
            logger.error(f"删除账户失败: {e}")
            return False

    def update_account(self, account_name: str, **kwargs) -> bool:
        """更新账户信息"""
        try:
            if account_name not in self.accounts:
                return False

            # 如果更新密码，需要加密
            if "password" in kwargs:
                kwargs["password"] = self._encrypt_password(kwargs["password"])

            self.accounts[account_name].update(kwargs)
            self._save_accounts()

            logger.info(f"账户 {account_name} 更新成功")
            return True

        except Exception as e:
            logger.error(f"更新账户失败: {e}")
            return False

    def set_last_used(self, account_name: str):
        """设置最后使用时间"""
        try:
            if account_name in self.accounts:
                import datetime

                self.accounts[account_name][
                    "last_used"
                ] = datetime.datetime.now().isoformat()
                self._save_accounts()
        except Exception as e:
            logger.error(f"设置最后使用时间失败: {e}")

    def get_default_account(self) -> Optional[str]:
        """获取默认账户（最近使用的账户）"""
        try:
            if not self.accounts:
                return None

            # 找到最近使用的账户
            last_used_account = None
            last_used_time = None

            for name, account in self.accounts.items():
                if account.get("last_used"):
                    if last_used_time is None or account["last_used"] > last_used_time:
                        last_used_time = account["last_used"]
                        last_used_account = name

            # 如果没有使用记录，返回第一个账户
            return last_used_account or list(self.accounts.keys())[0]

        except Exception as e:
            logger.error(f"获取默认账户失败: {e}")
            return None

    def export_accounts(
        self, export_path: str, include_passwords: bool = False
    ) -> bool:
        """导出账户配置"""
        try:
            export_data = {}
            for name, account in self.accounts.items():
                account_copy = account.copy()
                if not include_passwords:
                    account_copy["password"] = "***已隐藏***"
                else:
                    # 解密密码用于导出
                    account_copy["password"] = self._decrypt_password(
                        account["password"]
                    )
                export_data[name] = account_copy

            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            logger.info(f"账户配置导出成功: {export_path}")
            return True

        except Exception as e:
            logger.error(f"导出账户配置失败: {e}")
            return False

    def import_accounts(self, import_path: str) -> bool:
        """导入账户配置"""
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                import_data = json.load(f)

            for name, account in import_data.items():
                # 加密密码
                if "password" in account and account["password"] != "***已隐藏***":
                    account["password"] = self._encrypt_password(account["password"])
                    self.accounts[name] = account

            self._save_accounts()
            logger.info(f"账户配置导入成功: {import_path}")
            return True

        except Exception as e:
            logger.error(f"导入账户配置失败: {e}")
            return False
