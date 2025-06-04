"""
支持PGP加密的SMTP客户端扩展

扩展原有的SMTP客户端，添加PGP端到端加密功能
"""

import logging
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

from .smtp_client import SMTPClient
from common.models import Email
from common.utils import setup_logging
from pgp import PGPManager, KeyManager, EmailCrypto, PGPError

logger = setup_logging("smtp_client_pgp")


class SMTPClientPGP(SMTPClient):
    """支持PGP加密的SMTP客户端"""
    
    def __init__(self, 
                 pgp_keyring_dir: Optional[str] = None,
                 auto_encrypt: bool = False,
                 auto_sign: bool = True,
                 user_passphrase: Optional[str] = None,
                 **kwargs):
        """
        初始化支持PGP的SMTP客户端
        
        Args:
            pgp_keyring_dir: PGP密钥环目录
            auto_encrypt: 是否自动加密邮件
            auto_sign: 是否自动签名邮件
            user_passphrase: 用户私钥密码
            **kwargs: 传递给父类的其他参数
        """
        super().__init__(**kwargs)
        
        # 初始化PGP组件
        try:
            self.pgp_manager = PGPManager(pgp_keyring_dir)
            self.key_manager = KeyManager(self.pgp_manager)
            self.email_crypto = EmailCrypto(self.pgp_manager)
            
            self.pgp_enabled = True
            logger.info("PGP支持已启用")
            
        except Exception as e:
            logger.warning(f"PGP初始化失败，将禁用PGP功能: {e}")
            self.pgp_enabled = False
            self.pgp_manager = None
            self.key_manager = None
            self.email_crypto = None
        
        # PGP设置
        self.auto_encrypt = auto_encrypt and self.pgp_enabled
        self.auto_sign = auto_sign and self.pgp_enabled
        self.user_passphrase = user_passphrase
        
        logger.info(f"PGP SMTP客户端初始化完成 - 自动加密: {self.auto_encrypt}, 自动签名: {self.auto_sign}")
    
    def setup_user_pgp(self, 
                      name: str,
                      email: str, 
                      passphrase: Optional[str] = None,
                      force_recreate: bool = False) -> Dict[str, Any]:
        """
        为用户设置PGP密钥对
        
        Args:
            name: 用户姓名
            email: 用户邮箱
            passphrase: 私钥密码
            force_recreate: 是否强制重新创建
            
        Returns:
            设置结果
        """
        if not self.pgp_enabled:
            return {"success": False, "message": "PGP功能未启用"}
        
        try:
            result = self.key_manager.setup_user_pgp(name, email, passphrase, force_recreate)
            
            # 如果设置了密码，更新用户密码
            if passphrase and result["success"]:
                self.user_passphrase = passphrase
            
            return result
            
        except Exception as e:
            logger.error(f"设置用户PGP失败: {e}")
            return {"success": False, "message": f"设置失败: {e}"}
    
    def import_contact_key(self, contact_email: str, public_key_data: str) -> bool:
        """
        导入联系人的公钥
        
        Args:
            contact_email: 联系人邮箱
            public_key_data: 公钥数据
            
        Returns:
            是否成功导入
        """
        if not self.pgp_enabled:
            logger.warning("PGP功能未启用，无法导入密钥")
            return False
        
        try:
            self.key_manager.import_contact_public_key(contact_email, public_key_data)
            logger.info(f"成功导入联系人 {contact_email} 的公钥")
            return True
            
        except Exception as e:
            logger.error(f"导入联系人公钥失败: {e}")
            return False
    
    def send_email_with_pgp(self, 
                           email: Email,
                           encrypt: bool = False,
                           sign: bool = False,
                           recipient_key_id: Optional[str] = None,
                           sender_passphrase: Optional[str] = None) -> bool:
        """
        发送带有PGP加密/签名的邮件
        
        Args:
            email: 邮件对象
            encrypt: 是否加密
            sign: 是否签名
            recipient_key_id: 接收者密钥ID（可选，自动查找）
            sender_passphrase: 发送者私钥密码
            
        Returns:
            是否发送成功
        """
        if not self.pgp_enabled:
            logger.warning("PGP功能未启用，发送普通邮件")
            return self.send_email(email)
        
        try:
            processed_email = email
            
            # 使用提供的密码或默认密码
            passphrase = sender_passphrase or self.user_passphrase
            
            # 如果需要加密或签名
            if encrypt or sign:
                if sign and not encrypt:
                    # 仅签名
                    processed_email = self.email_crypto.auto_encrypt_email(
                        email, passphrase, sign_only=True
                    )
                elif encrypt:
                    # 加密（可能同时签名）
                    if recipient_key_id:
                        # 使用指定的接收者密钥
                        sender_key_id = None
                        if sign:
                            sender_key_id = self.key_manager.get_user_private_key_id(email.from_addr.address)
                        
                        processed_email = self.email_crypto.encrypt_email(
                            email, recipient_key_id, sender_key_id, passphrase
                        )
                    else:
                        # 自动查找密钥
                        processed_email = self.email_crypto.auto_encrypt_email(
                            email, passphrase, sign_only=False
                        )
                
                if processed_email is None:
                    logger.error("PGP处理失败，发送原始邮件")
                    processed_email = email
                else:
                    logger.info(f"邮件PGP处理成功 - 加密: {encrypt}, 签名: {sign}")
            
            # 发送处理后的邮件
            return self.send_email(processed_email)
            
        except Exception as e:
            logger.error(f"发送PGP邮件失败: {e}")
            return False
    
    def send_email(self, email: Email) -> bool:
        """
        重写发送邮件方法，支持自动PGP处理
        
        Args:
            email: 邮件对象
            
        Returns:
            是否发送成功
        """
        if not self.pgp_enabled or (not self.auto_encrypt and not self.auto_sign):
            # 没有启用PGP或自动处理，使用原始方法
            return super().send_email(email)
        
        try:
            # 自动PGP处理
            processed_email = email
            
            if self.auto_encrypt or self.auto_sign:
                if self.auto_sign and not self.auto_encrypt:
                    # 仅自动签名
                    processed_email = self.email_crypto.auto_encrypt_email(
                        email, self.user_passphrase, sign_only=True
                    )
                elif self.auto_encrypt:
                    # 自动加密（可能同时签名）
                    processed_email = self.email_crypto.auto_encrypt_email(
                        email, self.user_passphrase, sign_only=False
                    )
                
                if processed_email is not None:
                    logger.info(f"自动PGP处理成功 - 加密: {self.auto_encrypt}, 签名: {self.auto_sign}")
                else:
                    logger.warning("自动PGP处理失败，发送原始邮件")
                    processed_email = email
            
            # 发送处理后的邮件
            return super().send_email(processed_email)
            
        except Exception as e:
            logger.error(f"自动PGP处理失败: {e}")
            # 发送原始邮件作为备用
            return super().send_email(email)
    
    def get_pgp_status(self) -> Dict[str, Any]:
        """
        获取PGP状态信息
        
        Returns:
            PGP状态字典
        """
        if not self.pgp_enabled:
            return {
                "enabled": False,
                "reason": "PGP组件初始化失败"
            }
        
        try:
            public_keys = len(self.pgp_manager.public_keys)
            private_keys = len(self.pgp_manager.private_keys)
            
            return {
                "enabled": True,
                "auto_encrypt": self.auto_encrypt,
                "auto_sign": self.auto_sign,
                "has_passphrase": bool(self.user_passphrase),
                "public_keys_count": public_keys,
                "private_keys_count": private_keys,
                "keyring_dir": str(self.pgp_manager.keyring_dir)
            }
            
        except Exception as e:
            return {
                "enabled": False,
                "reason": f"获取状态失败: {e}"
            }
    
    def list_available_recipients(self) -> list:
        """
        列出可以发送加密邮件的收件人
        
        Returns:
            收件人列表
        """
        if not self.pgp_enabled:
            return []
        
        try:
            return self.key_manager.get_available_recipients()
        except Exception as e:
            logger.error(f"获取收件人列表失败: {e}")
            return []
    
    def export_public_key(self, email: str) -> Optional[str]:
        """
        导出用户的公钥
        
        Args:
            email: 用户邮箱
            
        Returns:
            公钥数据
        """
        if not self.pgp_enabled:
            return None
        
        try:
            return self.key_manager.export_user_public_key(email)
        except Exception as e:
            logger.error(f"导出公钥失败: {e}")
            return None
    
    def validate_pgp_setup(self, email: str) -> Dict[str, Any]:
        """
        验证用户的PGP设置
        
        Args:
            email: 用户邮箱
            
        Returns:
            验证结果
        """
        if not self.pgp_enabled:
            return {
                "valid": False,
                "reason": "PGP功能未启用"
            }
        
        try:
            validation = self.key_manager.validate_user_setup(email)
            validation["valid"] = validation["has_keypair"] and len(validation["errors"]) == 0
            return validation
            
        except Exception as e:
            return {
                "valid": False,
                "reason": f"验证失败: {e}"
            }