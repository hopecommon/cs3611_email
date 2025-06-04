"""
支持PGP解密的POP3客户端扩展

扩展原有的POP3客户端，添加PGP端到端解密功能
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

from .pop3_client_refactored import POP3Client
from common.models import Email
from common.utils import setup_logging
from pgp import PGPManager, KeyManager, EmailCrypto, PGPError

logger = setup_logging("pop3_client_pgp")


class POP3ClientPGP(POP3Client):
    """支持PGP解密的POP3客户端"""
    
    def __init__(self, 
                 pgp_keyring_dir: Optional[str] = None,
                 auto_decrypt: bool = True,
                 user_passphrase: Optional[str] = None,
                 **kwargs):
        """
        初始化支持PGP的POP3客户端
        
        Args:
            pgp_keyring_dir: PGP密钥环目录
            auto_decrypt: 是否自动解密邮件
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
        self.auto_decrypt = auto_decrypt and self.pgp_enabled
        self.user_passphrase = user_passphrase
        
        logger.info(f"PGP POP3客户端初始化完成 - 自动解密: {self.auto_decrypt}")
    
    def decrypt_email(self, 
                     email: Email,
                     recipient_passphrase: Optional[str] = None) -> Tuple[Optional[Email], Dict[str, Any]]:
        """
        解密邮件
        
        Args:
            email: 加密的邮件对象
            recipient_passphrase: 接收者私钥密码
            
        Returns:
            (解密后的邮件对象, 验证信息)
        """
        if not self.pgp_enabled:
            logger.warning("PGP功能未启用，无法解密邮件")
            return email, {"error": "PGP功能未启用"}
        
        try:
            # 使用提供的密码或默认密码
            passphrase = recipient_passphrase or self.user_passphrase
            
            # 尝试自动解密
            decrypted_email, verification_info = self.email_crypto.auto_decrypt_email(
                email, passphrase
            )
            
            if decrypted_email is not None:
                logger.info(f"邮件解密成功: {email.message_id}")
                return decrypted_email, verification_info
            else:
                logger.warning(f"邮件解密失败: {verification_info.get('error', '未知错误')}")
                return email, verification_info
                
        except Exception as e:
            logger.error(f"解密邮件失败: {e}")
            return email, {"error": f"解密失败: {e}"}
    
    def retrieve_email(self, 
                      message_number: int,
                      auto_decrypt: Optional[bool] = None,
                      recipient_passphrase: Optional[str] = None) -> Tuple[Optional[Email], Dict[str, Any]]:
        """
        获取并可能解密邮件
        
        Args:
            message_number: 邮件编号
            auto_decrypt: 是否自动解密（覆盖默认设置）
            recipient_passphrase: 接收者私钥密码
            
        Returns:
            (邮件对象, PGP验证信息)
        """
        try:
            # 先获取原始邮件
            email = super().retrieve_email(message_number)
            if email is None:
                return None, {"error": "获取邮件失败"}
            
            # 确定是否需要解密
            should_decrypt = auto_decrypt if auto_decrypt is not None else self.auto_decrypt
            
            if should_decrypt and self.pgp_enabled:
                # 检查是否为PGP邮件
                is_pgp_mail = (
                    (email.text_content and self.email_crypto.is_pgp_encrypted(email.text_content)) or
                    (email.html_content and self.email_crypto.is_pgp_encrypted(email.html_content)) or
                    (email.text_content and self.email_crypto.is_pgp_signed(email.text_content)) or
                    (email.html_content and self.email_crypto.is_pgp_signed(email.html_content))
                )
                
                if is_pgp_mail:
                    logger.info(f"检测到PGP邮件，开始解密: {email.message_id}")
                    return self.decrypt_email(email, recipient_passphrase)
                else:
                    logger.debug(f"普通邮件，无需解密: {email.message_id}")
                    return email, {"encrypted": False, "signed": False}
            else:
                return email, {"encrypted": False, "signed": False}
                
        except Exception as e:
            logger.error(f"获取/解密邮件失败: {e}")
            return None, {"error": f"处理失败: {e}"}
    
    def retrieve_all_emails(self, 
                           auto_decrypt: Optional[bool] = None,
                           recipient_passphrase: Optional[str] = None) -> List[Tuple[Email, Dict[str, Any]]]:
        """
        获取所有邮件并可能解密
        
        Args:
            auto_decrypt: 是否自动解密
            recipient_passphrase: 接收者私钥密码
            
        Returns:
            (邮件对象, PGP验证信息) 的列表
        """
        try:
            # 获取邮件数量
            email_count = self.get_email_count()
            if email_count == 0:
                return []
            
            emails_with_verification = []
            
            for i in range(1, email_count + 1):
                try:
                    email, verification_info = self.retrieve_email(
                        i, auto_decrypt, recipient_passphrase
                    )
                    
                    if email is not None:
                        emails_with_verification.append((email, verification_info))
                        
                        # 记录PGP状态
                        if verification_info.get("encrypted"):
                            logger.info(f"解密邮件 {i}: {email.subject}")
                        elif verification_info.get("signed"):
                            logger.info(f"验证签名邮件 {i}: {email.subject}")
                    
                except Exception as e:
                    logger.error(f"处理邮件 {i} 失败: {e}")
                    continue
            
            return emails_with_verification
            
        except Exception as e:
            logger.error(f"获取所有邮件失败: {e}")
            return []
    
    def get_pgp_summary(self) -> Dict[str, Any]:
        """
        获取PGP状态摘要
        
        Returns:
            PGP状态摘要
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
                "auto_decrypt": self.auto_decrypt,
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
    
    def import_sender_key(self, sender_email: str, public_key_data: str) -> bool:
        """
        导入发送者的公钥
        
        Args:
            sender_email: 发送者邮箱
            public_key_data: 公钥数据
            
        Returns:
            是否成功导入
        """
        if not self.pgp_enabled:
            logger.warning("PGP功能未启用，无法导入密钥")
            return False
        
        try:
            self.key_manager.import_contact_public_key(sender_email, public_key_data)
            logger.info(f"成功导入发送者 {sender_email} 的公钥")
            return True
            
        except Exception as e:
            logger.error(f"导入发送者公钥失败: {e}")
            return False
    
    def verify_email_signature(self, 
                              email: Email,
                              sender_key_id: Optional[str] = None) -> Dict[str, Any]:
        """
        验证邮件签名
        
        Args:
            email: 邮件对象
            sender_key_id: 发送者密钥ID（可选）
            
        Returns:
            验证结果
        """
        if not self.pgp_enabled:
            return {"valid": False, "reason": "PGP功能未启用"}
        
        try:
            verification_info = {
                "signed": False,
                "signature_valid": False,
                "signer_info": "",
                "verification_successful": False
            }
            
            # 检查文本内容签名
            if email.text_content and self.email_crypto.is_pgp_signed(email.text_content):
                try:
                    original_text, sig_valid, signer_info = self.pgp_manager.verify_signature(
                        email.text_content, sender_key_id
                    )
                    verification_info.update({
                        "signed": True,
                        "signature_valid": sig_valid,
                        "signer_info": signer_info,
                        "verification_successful": True
                    })
                except Exception as e:
                    verification_info["verification_successful"] = False
                    verification_info["error"] = str(e)
            
            # 检查HTML内容签名
            elif email.html_content and self.email_crypto.is_pgp_signed(email.html_content):
                try:
                    original_html, sig_valid, signer_info = self.pgp_manager.verify_signature(
                        email.html_content, sender_key_id
                    )
                    verification_info.update({
                        "signed": True,
                        "signature_valid": sig_valid,
                        "signer_info": signer_info,
                        "verification_successful": True
                    })
                except Exception as e:
                    verification_info["verification_successful"] = False
                    verification_info["error"] = str(e)
            
            return verification_info
            
        except Exception as e:
            logger.error(f"验证邮件签名失败: {e}")
            return {"valid": False, "reason": f"验证失败: {e}"}
    
    def set_user_passphrase(self, passphrase: str) -> None:
        """
        设置用户私钥密码
        
        Args:
            passphrase: 密码
        """
        self.user_passphrase = passphrase
        logger.info("用户私钥密码已更新")
    
    def test_decryption(self, email_address: str) -> Dict[str, Any]:
        """
        测试解密功能
        
        Args:
            email_address: 用户邮箱地址
            
        Returns:
            测试结果
        """
        if not self.pgp_enabled:
            return {"success": False, "reason": "PGP功能未启用"}
        
        try:
            # 验证用户设置
            validation = self.key_manager.validate_user_setup(email_address)
            
            if not validation["has_private_key"]:
                return {"success": False, "reason": "未找到私钥"}
            
            if validation["private_key_protected"] and not self.user_passphrase:
                return {"success": False, "reason": "私钥已加密但未提供密码"}
            
            # 尝试创建测试消息
            test_message = "PGP解密测试消息"
            
            # 获取密钥
            key_id = validation["key_id"]
            
            # 加密测试消息
            encrypted_msg = self.pgp_manager.encrypt_message(test_message, key_id)
            
            # 解密测试消息
            decrypted_msg = self.pgp_manager.decrypt_message(
                encrypted_msg, key_id, self.user_passphrase
            )
            
            success = decrypted_msg == test_message
            
            return {
                "success": success,
                "message": "解密测试成功" if success else "解密测试失败",
                "key_id": key_id
            }
            
        except Exception as e:
            logger.error(f"解密测试失败: {e}")
            return {"success": False, "reason": f"测试失败: {e}"}