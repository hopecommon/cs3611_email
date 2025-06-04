"""
邮件加密模块 - 专门处理邮件的PGP加密和解密

集成PGP功能到邮件系统中，提供简化的邮件加密接口
"""

import logging
from typing import Optional, Tuple, Dict, Any, List
import re
from datetime import datetime

from .pgp_manager import PGPManager, PGPError
from common.models import Email, EmailAddress, Attachment
from common.utils import setup_logging

logger = setup_logging("email_crypto")


class EmailCrypto:
    """邮件加密类 - 处理邮件的PGP加密和解密"""
    
    def __init__(self, pgp_manager: Optional[PGPManager] = None):
        """
        初始化邮件加密器
        
        Args:
            pgp_manager: PGP管理器实例
        """
        self.pgp_manager = pgp_manager or PGPManager()
        
        # PGP邮件标识
        self.PGP_MESSAGE_BEGIN = "-----BEGIN PGP MESSAGE-----"
        self.PGP_MESSAGE_END = "-----END PGP MESSAGE-----"
        self.PGP_SIGNED_MESSAGE_BEGIN = "-----BEGIN PGP SIGNED MESSAGE-----"
        self.PGP_SIGNATURE_BEGIN = "-----BEGIN PGP SIGNATURE-----"
        self.PGP_SIGNATURE_END = "-----END PGP SIGNATURE-----"
        
        logger.info("邮件加密器初始化完成")
    
    def is_pgp_encrypted(self, content: str) -> bool:
        """
        检查内容是否为PGP加密
        
        Args:
            content: 邮件内容
            
        Returns:
            是否为PGP加密内容
        """
        return (self.PGP_MESSAGE_BEGIN in content and 
                self.PGP_MESSAGE_END in content)
    
    def is_pgp_signed(self, content: str) -> bool:
        """
        检查内容是否为PGP签名
        
        Args:
            content: 邮件内容
            
        Returns:
            是否为PGP签名内容
        """
        return (self.PGP_SIGNED_MESSAGE_BEGIN in content and 
                self.PGP_SIGNATURE_BEGIN in content and
                self.PGP_SIGNATURE_END in content)
    
    def encrypt_email(self, email: Email, recipient_key_id: str, sender_private_key_id: Optional[str] = None, passphrase: Optional[str] = None) -> Email:
        """
        加密邮件
        
        Args:
            email: 要加密的邮件对象
            recipient_key_id: 接收者公钥ID
            sender_private_key_id: 发送者私钥ID（可选，用于签名）
            passphrase: 发送者私钥密码（如果需要）
            
        Returns:
            加密后的邮件对象
        """
        try:
            # 准备要加密的内容
            content_to_encrypt = email.text_content or ""
            
            # 暂时仅使用加密功能，避免签名兼容性问题
            if sender_private_key_id:
                logger.info(f"暂时跳过签名功能，仅使用加密")
                encrypted_content = self.pgp_manager.encrypt_message(content_to_encrypt, recipient_key_id)
                is_signed = False
            else:
                encrypted_content = self.pgp_manager.encrypt_message(content_to_encrypt, recipient_key_id)
                is_signed = False
            
            # 创建加密后的邮件副本
            encrypted_email = Email(
                message_id=email.message_id,
                subject=f"[PGP加密] {email.subject}",
                from_addr=email.from_addr,
                to_addrs=email.to_addrs,
                cc_addrs=email.cc_addrs,
                bcc_addrs=email.bcc_addrs,
                text_content=encrypted_content,
                html_content=None,  # 加密邮件通常只用文本
                date=email.date,
                headers=email.headers.copy() if email.headers else {}
            )
            
            # 添加PGP标识头部
            encrypted_email.headers["X-PGP-Encrypted"] = "true"
            if is_signed:
                encrypted_email.headers["X-PGP-Signed"] = "true"
            encrypted_email.headers["X-PGP-Version"] = "1.0"
            
            logger.info(f"邮件加密成功: {email.message_id}")
            return encrypted_email
            
        except Exception as e:
            logger.error(f"加密邮件失败: {e}")
            raise PGPError(f"加密邮件失败: {e}")
    
    def decrypt_email(self, 
                     email: Email,
                     private_key_id: str,
                     passphrase: Optional[str] = None,
                     sender_public_key_id: Optional[str] = None) -> Tuple[Email, Dict[str, Any]]:
        """
        解密邮件
        
        Args:
            email: 加密的邮件对象
            private_key_id: 私钥ID
            passphrase: 私钥密码
            sender_public_key_id: 发送者公钥ID（用于验证签名）
            
        Returns:
            (解密后的邮件对象, 验证信息)
        """
        try:
            # 创建新的邮件对象
            decrypted_email = Email(
                message_id=email.message_id,
                subject=email.subject,
                from_addr=email.from_addr,
                to_addrs=email.to_addrs,
                cc_addrs=email.cc_addrs,
                bcc_addrs=email.bcc_addrs,
                text_content=email.text_content,
                html_content=email.html_content,
                attachments=email.attachments.copy(),
                date=email.date,
                status=email.status,
                priority=email.priority,
                is_read=email.is_read,
                spam_score=email.spam_score,
                server_id=email.server_id,
                in_reply_to=email.in_reply_to,
                references=email.references.copy(),
                headers=email.headers.copy()
            )
            
            verification_info = {
                "encrypted": False,
                "signed": False,
                "signature_valid": False,
                "signer_info": "",
                "decryption_successful": False,
                "verification_successful": False
            }
            
            # 处理文本内容
            if email.text_content:
                if self.is_pgp_encrypted(email.text_content):
                    # 解密（可能包含签名）
                    try:
                        if sender_public_key_id:
                            # 解密并验证签名
                            decrypted_text, sig_valid, signer_info = self.pgp_manager.decrypt_and_verify(
                                email.text_content, private_key_id, sender_public_key_id, passphrase
                            )
                            verification_info["signature_valid"] = sig_valid
                            verification_info["signer_info"] = signer_info
                            verification_info["signed"] = True
                            verification_info["verification_successful"] = True
                        else:
                            # 仅解密
                            decrypted_text = self.pgp_manager.decrypt_message(
                                email.text_content, private_key_id, passphrase
                            )
                        
                        decrypted_email.text_content = decrypted_text
                        verification_info["encrypted"] = True
                        verification_info["decryption_successful"] = True
                        
                    except Exception as e:
                        logger.error(f"解密文本内容失败: {e}")
                        verification_info["decryption_successful"] = False
                        
                elif self.is_pgp_signed(email.text_content):
                    # 仅验证签名
                    try:
                        original_text, sig_valid, signer_info = self.pgp_manager.verify_signature(
                            email.text_content, sender_public_key_id
                        )
                        decrypted_email.text_content = original_text
                        verification_info["signed"] = True
                        verification_info["signature_valid"] = sig_valid
                        verification_info["signer_info"] = signer_info
                        verification_info["verification_successful"] = True
                        
                    except Exception as e:
                        logger.error(f"验证文本签名失败: {e}")
                        verification_info["verification_successful"] = False
            
            # 处理HTML内容
            if email.html_content:
                if self.is_pgp_encrypted(email.html_content):
                    # 解密（可能包含签名）
                    try:
                        if sender_public_key_id:
                            # 解密并验证签名
                            decrypted_html, sig_valid, signer_info = self.pgp_manager.decrypt_and_verify(
                                email.html_content, private_key_id, sender_public_key_id, passphrase
                            )
                            verification_info["signature_valid"] = sig_valid
                            verification_info["signer_info"] = signer_info
                            verification_info["signed"] = True
                            verification_info["verification_successful"] = True
                        else:
                            # 仅解密
                            decrypted_html = self.pgp_manager.decrypt_message(
                                email.html_content, private_key_id, passphrase
                            )
                        
                        decrypted_email.html_content = decrypted_html
                        verification_info["encrypted"] = True
                        verification_info["decryption_successful"] = True
                        
                    except Exception as e:
                        logger.error(f"解密HTML内容失败: {e}")
                        verification_info["decryption_successful"] = False
                        
                elif self.is_pgp_signed(email.html_content):
                    # 仅验证签名
                    try:
                        original_html, sig_valid, signer_info = self.pgp_manager.verify_signature(
                            email.html_content, sender_public_key_id
                        )
                        decrypted_email.html_content = original_html
                        verification_info["signed"] = True
                        verification_info["signature_valid"] = sig_valid
                        verification_info["signer_info"] = signer_info
                        verification_info["verification_successful"] = True
                        
                    except Exception as e:
                        logger.error(f"验证HTML签名失败: {e}")
                        verification_info["verification_successful"] = False
            
            # 移除PGP标头
            if "X-PGP-Encrypted" in decrypted_email.headers:
                del decrypted_email.headers["X-PGP-Encrypted"]
            if "X-PGP-Signed" in decrypted_email.headers:
                del decrypted_email.headers["X-PGP-Signed"]
            if "X-PGP-Key-ID" in decrypted_email.headers:
                del decrypted_email.headers["X-PGP-Key-ID"]
            if "X-PGP-Signer-Key-ID" in decrypted_email.headers:
                del decrypted_email.headers["X-PGP-Signer-Key-ID"]
            
            # 还原主题行
            subject = decrypted_email.subject
            if subject.startswith("[PGP加密] "):
                decrypted_email.subject = subject[7:]
            elif subject.startswith("[PGP签名] "):
                decrypted_email.subject = subject[7:]
            
            logger.info(f"邮件解密成功: {email.message_id}")
            return decrypted_email, verification_info
            
        except Exception as e:
            logger.error(f"解密邮件失败: {e}")
            raise PGPError(f"解密邮件失败: {e}")
    
    def get_key_info_for_email(self, email_address: str) -> Optional[str]:
        """
        根据邮箱地址查找对应的PGP密钥ID
        
        Args:
            email_address: 邮箱地址
            
        Returns:
            密钥ID（如果找到）
        """
        try:
            logger.debug(f"查找邮箱 {email_address} 对应的密钥")
            
            # 搜索所有公钥（优先）
            for key_id, key in self.pgp_manager.public_keys.items():
                for userid in key.userids:
                    # 正确获取UserID的内容
                    try:
                        userid_str = str(userid).lower()
                        # 尝试获取UserID的name属性
                        if hasattr(userid, 'name'):
                            userid_str = str(userid.name).lower()
                        elif hasattr(userid, 'userid'):
                            userid_str = str(userid.userid).lower()
                        
                        logger.debug(f"检查公钥 {key_id} 的UserID: {userid_str}")
                        
                        if email_address.lower() in userid_str:
                            logger.debug(f"在公钥中找到匹配: {key_id} - {userid_str}")
                            return key_id
                    except Exception as e:
                        logger.debug(f"处理UserID时出错: {e}")
                        continue
            
            # 搜索所有私钥
            for key_id, key in self.pgp_manager.private_keys.items():
                for userid in key.userids:
                    try:
                        userid_str = str(userid).lower()
                        # 尝试获取UserID的name属性
                        if hasattr(userid, 'name'):
                            userid_str = str(userid.name).lower()
                        elif hasattr(userid, 'userid'):
                            userid_str = str(userid.userid).lower()
                        
                        logger.debug(f"检查私钥 {key_id} 的UserID: {userid_str}")
                        
                        if email_address.lower() in userid_str:
                            logger.debug(f"在私钥中找到匹配: {key_id} - {userid_str}")
                            return key_id
                    except Exception as e:
                        logger.debug(f"处理UserID时出错: {e}")
                        continue
            
            logger.warning(f"未找到邮箱 {email_address} 对应的密钥")
            logger.debug(f"当前公钥数量: {len(self.pgp_manager.public_keys)}")
            logger.debug(f"当前私钥数量: {len(self.pgp_manager.private_keys)}")
            return None
            
        except Exception as e:
            logger.error(f"查找邮箱对应密钥失败: {e}")
            return None
    
    def auto_encrypt_email(self, 
                          email: Email,
                          sender_passphrase: Optional[str] = None,
                          sign_only: bool = False) -> Optional[Email]:
        """
        自动加密邮件（根据发送者和接收者的密钥）
        
        Args:
            email: 原始邮件
            sender_passphrase: 发送者私钥密码
            sign_only: 仅签名不加密
            
        Returns:
            加密后的邮件（如果可以加密）
        """
        try:
            # 查找发送者私钥
            sender_key_id = self.get_key_info_for_email(email.from_addr.address)
            
            # 查找接收者公钥（取第一个接收者）
            recipient_key_id = None
            if email.to_addrs:
                recipient_key_id = self.get_key_info_for_email(email.to_addrs[0].address)
            
            # 如果找不到必要的密钥，返回None
            if not recipient_key_id and not sign_only:
                logger.warning(f"未找到接收者 {email.to_addrs[0].address if email.to_addrs else '未知'} 的公钥")
                return None
            
            if not sender_key_id:
                logger.warning(f"未找到发送者 {email.from_addr.address} 的私钥")
                if not sign_only:
                    # 如果只是加密不签名，还是可以处理的
                    return self.encrypt_email(email, recipient_key_id)
                else:
                    return None
            
            # 执行加密/签名
            if sign_only:
                return self.encrypt_email(email, recipient_key_id, sender_key_id, sender_passphrase, sign_only=True)
            else:
                return self.encrypt_email(email, recipient_key_id, sender_key_id, sender_passphrase)
            
        except Exception as e:
            logger.error(f"自动加密邮件失败: {e}")
            return None
    
    def auto_decrypt_email(self, 
                          email: Email,
                          recipient_passphrase: Optional[str] = None) -> Tuple[Optional[Email], Dict[str, Any]]:
        """
        自动解密邮件
        
        Args:
            email: 加密的邮件
            recipient_passphrase: 接收者私钥密码
            
        Returns:
            (解密后的邮件（如果可以解密）, 验证信息)
        """
        try:
            verification_info = {
                "encrypted": False,
                "signed": False,
                "signature_valid": False,
                "signer_info": "",
                "decryption_successful": False,
                "verification_successful": False,
                "error": ""
            }
            
            # 检查是否为PGP邮件
            is_encrypted = (email.text_content and self.is_pgp_encrypted(email.text_content)) or \
                          (email.html_content and self.is_pgp_encrypted(email.html_content))
            
            is_signed = (email.text_content and self.is_pgp_signed(email.text_content)) or \
                       (email.html_content and self.is_pgp_signed(email.html_content))
            
            if not is_encrypted and not is_signed:
                return email, verification_info
            
            # 查找接收者私钥（这里假设接收者是当前用户）
            recipient_key_id = None
            for to_addr in email.to_addrs:
                key_id = self.get_key_info_for_email(to_addr.address)
                if key_id and key_id in self.pgp_manager.private_keys:
                    recipient_key_id = key_id
                    break
            
            if not recipient_key_id:
                verification_info["error"] = "未找到匹配的私钥"
                return None, verification_info
            
            # 查找发送者公钥
            sender_key_id = self.get_key_info_for_email(email.from_addr.address)
            
            # 执行解密/验证
            return self.decrypt_email(email, recipient_key_id, recipient_passphrase, sender_key_id)
            
        except Exception as e:
            verification_info = {
                "encrypted": False,
                "signed": False,
                "signature_valid": False,
                "signer_info": "",
                "decryption_successful": False,
                "verification_successful": False,
                "error": str(e)
            }
            logger.error(f"自动解密邮件失败: {e}")
            return None, verification_info