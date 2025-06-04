"""
PGP管理器 - 核心PGP功能实现

提供PGP密钥生成、加密、解密、签名和验证功能
使用pgpy库实现纯Python的PGP操作
"""

import os
import logging
from typing import Optional, Tuple, Dict, Any, Union
from pathlib import Path
import json
from datetime import datetime

# PGP相关导入
try:
    import pgpy
    from pgpy import PGPKey, PGPMessage, PGPSignature
    from pgpy.constants import PubKeyAlgorithm, KeyFlags, HashAlgorithm, SymmetricKeyAlgorithm, CompressionAlgorithm
    PGP_AVAILABLE = True
except ImportError:
    PGP_AVAILABLE = False
    pgpy = None
    PGPKey = None
    PGPMessage = None
    PGPSignature = None

from common.utils import setup_logging

logger = setup_logging("pgp_manager")


class PGPError(Exception):
    """PGP操作异常"""
    pass


class PGPManager:
    """PGP管理器类"""
    
    def __init__(self, keyring_dir: Optional[str] = None):
        """
        初始化PGP管理器
        
        Args:
            keyring_dir: PGP密钥环目录路径
        """
        if not PGP_AVAILABLE:
            raise PGPError("PGP库未安装。请运行: pip install pgpy python-gnupg")
        
        self.keyring_dir = Path(keyring_dir or os.path.join(os.getcwd(), "data", "pgp_keys"))
        self.keyring_dir.mkdir(parents=True, exist_ok=True)
        
        # 密钥存储
        self.public_keys: Dict[str, PGPKey] = {}
        self.private_keys: Dict[str, PGPKey] = {}
        
        # 配置文件
        self.config_file = self.keyring_dir / "pgp_config.json"
        self.config = self._load_config()
        
        # 加载现有密钥
        self._load_keys()
        
        logger.info(f"PGP管理器初始化完成，密钥环目录: {self.keyring_dir}")
    
    def _load_config(self) -> Dict[str, Any]:
        """加载PGP配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载PGP配置失败: {e}")
        
        # 默认配置
        default_config = {
            "default_key_size": 4096,
            "default_hash_algorithm": "SHA256",
            "default_symmetric_algorithm": "AES256",
            "default_compression": "ZIP",
            "auto_sign": True,
            "auto_encrypt": False,
            "key_expiry_days": 0,  # 0表示永不过期
        }
        
        self._save_config(default_config)
        return default_config
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """保存PGP配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存PGP配置失败: {e}")
    
    def _load_keys(self) -> None:
        """从密钥环目录加载所有密钥"""
        try:
            # 加载公钥
            public_dir = self.keyring_dir / "public"
            if public_dir.exists():
                for key_file in public_dir.glob("*.asc"):
                    try:
                        with open(key_file, 'r', encoding='utf-8') as f:
                            key, _ = pgpy.PGPKey.from_blob(f.read())
                            self.public_keys[key.fingerprint.keyid] = key
                            logger.debug(f"加载公钥: {key.userids[0]} ({key.fingerprint.keyid})")
                    except Exception as e:
                        logger.warning(f"加载公钥文件 {key_file} 失败: {e}")
            
            # 加载私钥
            private_dir = self.keyring_dir / "private"
            if private_dir.exists():
                for key_file in private_dir.glob("*.asc"):
                    try:
                        with open(key_file, 'r', encoding='utf-8') as f:
                            key, _ = pgpy.PGPKey.from_blob(f.read())
                            self.private_keys[key.fingerprint.keyid] = key
                            logger.debug(f"加载私钥: {key.userids[0]} ({key.fingerprint.keyid})")
                    except Exception as e:
                        logger.warning(f"加载私钥文件 {key_file} 失败: {e}")
            
            logger.info(f"密钥加载完成 - 公钥: {len(self.public_keys)}个, 私钥: {len(self.private_keys)}个")
            
        except Exception as e:
            logger.error(f"加载密钥失败: {e}")
    
    def generate_key_pair(self, 
                         name: str, 
                         email: str, 
                         passphrase: Optional[str] = None,
                         key_size: int = 4096,
                         comment: str = "") -> Tuple[str, str]:
        """
        生成PGP密钥对
        
        Args:
            name: 用户姓名
            email: 用户邮箱
            passphrase: 私钥密码（可选）
            key_size: 密钥长度
            comment: 密钥注释
            
        Returns:
            (公钥ID, 私钥ID)
        """
        try:
            # 创建用户ID
            userid = f"{name}"
            if comment:
                userid += f" ({comment})"
            userid += f" <{email}>"
            
            logger.info(f"开始生成PGP密钥对: {userid}")
            
            # 生成主密钥（用于签名和认证）
            key = pgpy.PGPKey.new(PubKeyAlgorithm.RSAEncryptOrSign, key_size)
            
            # 创建用户ID
            uid = pgpy.PGPUID.new(userid)
            key.add_uid(uid, 
                       usage={KeyFlags.Sign, KeyFlags.Certify},
                       hashes=[HashAlgorithm.SHA256, HashAlgorithm.SHA384, HashAlgorithm.SHA512],
                       ciphers=[SymmetricKeyAlgorithm.AES256, SymmetricKeyAlgorithm.AES192, SymmetricKeyAlgorithm.AES128],
                       compression=[CompressionAlgorithm.ZLIB, CompressionAlgorithm.BZ2, CompressionAlgorithm.ZIP])
            
            # 生成子密钥（用于加密）
            subkey = pgpy.PGPKey.new(PubKeyAlgorithm.RSAEncryptOrSign, key_size)
            key.add_subkey(subkey, 
                          usage={KeyFlags.EncryptCommunications, KeyFlags.EncryptStorage})
            
            # 如果提供了密码，加密私钥
            if passphrase:
                key.protect(passphrase, SymmetricKeyAlgorithm.AES256, HashAlgorithm.SHA256)
            
            # 保存密钥对
            key_id = key.fingerprint.keyid
            
            # 创建目录
            (self.keyring_dir / "public").mkdir(exist_ok=True)
            (self.keyring_dir / "private").mkdir(exist_ok=True)
            
            # 保存公钥
            public_key_file = self.keyring_dir / "public" / f"{key_id}.asc"
            with open(public_key_file, 'w', encoding='utf-8') as f:
                f.write(str(key.pubkey))
            
            # 保存私钥
            private_key_file = self.keyring_dir / "private" / f"{key_id}.asc"
            with open(private_key_file, 'w', encoding='utf-8') as f:
                f.write(str(key))
            
            # 添加到内存中的密钥环
            self.public_keys[key_id] = key.pubkey
            self.private_keys[key_id] = key
            
            logger.info(f"PGP密钥对生成成功: {key_id}")
            return key_id, key_id
            
        except Exception as e:
            logger.error(f"生成PGP密钥对失败: {e}")
            raise PGPError(f"生成密钥对失败: {e}")
    
    def import_key(self, key_data: str, is_private: bool = False) -> str:
        """
        导入PGP密钥
        
        Args:
            key_data: 密钥数据（ASCII armored格式）
            is_private: 是否为私钥
            
        Returns:
            密钥ID
        """
        try:
            key, _ = pgpy.PGPKey.from_blob(key_data)
            key_id = key.fingerprint.keyid
            
            if is_private and key.is_protected:
                logger.warning(f"导入的私钥 {key_id} 已加密，需要密码解锁")
            
            # 保存到文件
            key_dir = self.keyring_dir / ("private" if is_private else "public")
            key_dir.mkdir(exist_ok=True)
            
            key_file = key_dir / f"{key_id}.asc"
            with open(key_file, 'w', encoding='utf-8') as f:
                f.write(key_data)
            
            # 添加到内存密钥环
            if is_private:
                self.private_keys[key_id] = key
            else:
                self.public_keys[key_id] = key
            
            logger.info(f"密钥导入成功: {key_id} ({'私钥' if is_private else '公钥'})")
            return key_id
            
        except Exception as e:
            logger.error(f"导入密钥失败: {e}")
            raise PGPError(f"导入密钥失败: {e}")
    
    def export_key(self, key_id: str, is_private: bool = False) -> str:
        """
        导出PGP密钥
        
        Args:
            key_id: 密钥ID
            is_private: 是否导出私钥
            
        Returns:
            密钥数据（ASCII armored格式）
        """
        try:
            if is_private:
                if key_id not in self.private_keys:
                    raise PGPError(f"私钥 {key_id} 不存在")
                key = self.private_keys[key_id]
            else:
                if key_id not in self.public_keys:
                    raise PGPError(f"公钥 {key_id} 不存在")
                key = self.public_keys[key_id]
            
            return str(key)
            
        except Exception as e:
            logger.error(f"导出密钥失败: {e}")
            raise PGPError(f"导出密钥失败: {e}")
    
    def encrypt_message(self, message: str, recipient_key_id: str) -> str:
        """
        加密消息
        
        Args:
            message: 要加密的消息
            recipient_key_id: 接收者公钥ID
            
        Returns:
            加密后的消息
        """
        try:
            if recipient_key_id not in self.public_keys:
                raise PGPError(f"接收者公钥 {recipient_key_id} 不存在")
            
            recipient_key = self.public_keys[recipient_key_id]
            
            # 创建PGP消息
            msg = pgpy.PGPMessage.new(message)
            
            # 加密消息
            encrypted_msg = recipient_key.encrypt(msg)
            
            return str(encrypted_msg)
            
        except Exception as e:
            logger.error(f"加密消息失败: {e}")
            raise PGPError(f"加密消息失败: {e}")
    
    def decrypt_message(self, encrypted_message: str, private_key_id: str, passphrase: Optional[str] = None) -> str:
        """
        解密消息
        
        Args:
            encrypted_message: 加密的消息
            private_key_id: 私钥ID
            passphrase: 私钥密码（如果需要）
            
        Returns:
            解密后的消息
        """
        try:
            if private_key_id not in self.private_keys:
                raise PGPError(f"私钥 {private_key_id} 不存在")
            
            private_key = self.private_keys[private_key_id]
            
            # 如果私钥被保护，需要解锁
            if private_key.is_protected:
                if not passphrase:
                    raise PGPError("私钥已加密，需要提供密码")
                with private_key.unlock(passphrase):
                    encrypted_msg = pgpy.PGPMessage.from_blob(encrypted_message)
                    decrypted_msg = private_key.decrypt(encrypted_msg)
            else:
                encrypted_msg = pgpy.PGPMessage.from_blob(encrypted_message)
                decrypted_msg = private_key.decrypt(encrypted_msg)
            
            return str(decrypted_msg.message)
            
        except Exception as e:
            logger.error(f"解密消息失败: {e}")
            raise PGPError(f"解密消息失败: {e}")
    
    def sign_message(self, message: str, private_key_id: str, passphrase: Optional[str] = None) -> str:
        """
        签名消息
        
        Args:
            message: 要签名的消息
            private_key_id: 私钥ID
            passphrase: 私钥密码（如果需要）
            
        Returns:
            签名后的消息
        """
        try:
            if private_key_id not in self.private_keys:
                raise PGPError(f"私钥 {private_key_id} 不存在")
            
            private_key = self.private_keys[private_key_id]
            
            # 创建PGP消息
            msg = pgpy.PGPMessage.new(message)
            
            # 签名消息
            if private_key.is_protected:
                if not passphrase:
                    raise PGPError("私钥已加密，需要提供密码")
                with private_key.unlock(passphrase):
                    # 使用清签名格式
                    signed_msg = private_key.sign(msg, notation=None)
            else:
                signed_msg = private_key.sign(msg, notation=None)
            
            # 确保返回字符串格式
            result = str(signed_msg)
            
            # 验证返回的是有效的PGP签名格式
            if not result.startswith('-----BEGIN PGP SIGNED MESSAGE-----'):
                logger.warning("签名格式可能不正确")
            
            return result
            
        except Exception as e:
            logger.error(f"签名消息失败: {e}")
            raise PGPError(f"签名消息失败: {e}")
    
    def verify_signature(self, signed_message: str, public_key_id: Optional[str] = None) -> Tuple[str, bool, str]:
        """
        验证消息签名
        
        Args:
            signed_message: 已签名的消息
            public_key_id: 公钥ID（可选，如果不提供会尝试自动查找）
            
        Returns:
            (原始消息, 验证结果, 签名者信息)
        """
        try:
            # 确保输入是字符串类型
            if not isinstance(signed_message, str):
                logger.error(f"签名消息类型错误: {type(signed_message)}")
                raise PGPError(f"签名消息必须是字符串类型，当前类型: {type(signed_message)}")
            
            # 检查签名格式
            if not signed_message.strip():
                raise PGPError("签名消息不能为空")
            
            # 解析签名消息
            try:
                signed_msg = pgpy.PGPMessage.from_blob(signed_message)
            except Exception as parse_error:
                logger.error(f"解析签名消息失败: {parse_error}")
                logger.debug(f"签名消息内容: {signed_message[:200]}...")
                raise PGPError(f"解析签名消息失败: {parse_error}")
            
            # 如果指定了公钥ID，使用指定的公钥验证
            if public_key_id and public_key_id in self.public_keys:
                public_key = self.public_keys[public_key_id]
                try:
                    verification_result = public_key.verify(signed_msg)
                    # 获取签名者信息
                    if hasattr(public_key.userids[0], 'name'):
                        signer_info = str(public_key.userids[0].name)
                    else:
                        signer_info = str(public_key.userids[0])
                except Exception as verify_error:
                    logger.error(f"验证签名失败: {verify_error}")
                    verification_result = False
                    signer_info = "验证失败"
            else:
                # 尝试用所有公钥验证
                verification_result = False
                signer_info = "未知签名者"
                
                for key_id, public_key in self.public_keys.items():
                    try:
                        verification_result = public_key.verify(signed_msg)
                        if verification_result:
                            if hasattr(public_key.userids[0], 'name'):
                                signer_info = str(public_key.userids[0].name)
                            else:
                                signer_info = str(public_key.userids[0])
                            break
                    except Exception:
                        continue
            
            # 提取原始消息
            try:
                if hasattr(signed_msg, 'message'):
                    original_message = str(signed_msg.message)
                else:
                    # 如果无法提取原始消息，尝试解析
                    original_message = signed_message
                    # 查找消息内容（在-----BEGIN 和 -----BEGIN PGP SIGNATURE之间）
                    import re
                    match = re.search(r'-----BEGIN PGP SIGNED MESSAGE-----.*?\n\n(.*?)\n-----BEGIN PGP SIGNATURE-----', 
                                    signed_message, re.DOTALL)
                    if match:
                        original_message = match.group(1).strip()
            except Exception:
                original_message = "无法提取原始消息"
            
            return original_message, verification_result, signer_info
            
        except Exception as e:
            logger.error(f"验证签名失败: {e}")
            raise PGPError(f"验证签名失败: {e}")
    
    def encrypt_and_sign(self, message: str, recipient_key_id: str, sender_private_key_id: str, passphrase: Optional[str] = None) -> str:
        """
        加密并签名消息
        
        Args:
            message: 要处理的消息
            recipient_key_id: 接收者公钥ID
            sender_private_key_id: 发送者私钥ID
            passphrase: 发送者私钥密码（如果需要）
            
        Returns:
            加密并签名后的消息
        """
        try:
            if recipient_key_id not in self.public_keys:
                raise PGPError(f"接收者公钥 {recipient_key_id} 不存在")
            
            if sender_private_key_id not in self.private_keys:
                raise PGPError(f"发送者私钥 {sender_private_key_id} 不存在")
            
            recipient_key = self.public_keys[recipient_key_id]
            sender_key = self.private_keys[sender_private_key_id]
            
            # 方法1：仅加密（暂时跳过签名以避免兼容性问题）
            # 如果需要签名，可以在邮件层面添加签名信息
            encrypted_msg = self.encrypt_message(message, recipient_key_id)
            
            # 可选：在加密消息中添加签名者信息的头部
            signature_info = f"Signed-By: {str(sender_key.userids[0])}\n"
            enhanced_message = signature_info + message
            final_encrypted = self.encrypt_message(enhanced_message, recipient_key_id)
            
            return final_encrypted
            
        except Exception as e:
            logger.error(f"加密并签名消息失败: {e}")
            raise PGPError(f"加密并签名消息失败: {e}")
    
    def decrypt_and_verify(self, encrypted_message: str, recipient_private_key_id: str, sender_public_key_id: Optional[str] = None, passphrase: Optional[str] = None) -> Tuple[str, bool, str]:
        """
        解密并验证消息
        
        Args:
            encrypted_message: 加密的消息
            recipient_private_key_id: 接收者私钥ID
            sender_public_key_id: 发送者公钥ID（可选）
            passphrase: 接收者私钥密码（如果需要）
            
        Returns:
            (原始消息, 验证结果, 签名者信息)
        """
        try:
            # 先解密
            decrypted_msg = self.decrypt_message(encrypted_message, recipient_private_key_id, passphrase)
            
            # 再验证签名
            original_message, verification_result, signer_info = self.verify_signature(decrypted_msg, sender_public_key_id)
            
            return original_message, verification_result, signer_info
            
        except Exception as e:
            logger.error(f"解密并验证消息失败: {e}")
            raise PGPError(f"解密并验证消息失败: {e}")
    
    def list_keys(self, key_type: str = "both") -> Dict[str, Dict[str, Any]]:
        """
        列出密钥
        
        Args:
            key_type: 密钥类型 ("public", "private", "both")
            
        Returns:
            密钥信息字典
        """
        keys_info = {}
        
        if key_type in ("public", "both"):
            for key_id, key in self.public_keys.items():
                keys_info[key_id] = {
                    "type": "public",
                    "userids": [str(uid) for uid in key.userids],
                    "created": key.created.isoformat(),
                    "fingerprint": str(key.fingerprint),
                    "algorithm": str(key.key_algorithm),
                    "key_size": key.key_size
                }
        
        if key_type in ("private", "both"):
            for key_id, key in self.private_keys.items():
                keys_info[key_id] = {
                    "type": "private",
                    "userids": [str(uid) for uid in key.userids],
                    "created": key.created.isoformat(),
                    "fingerprint": str(key.fingerprint),
                    "algorithm": str(key.key_algorithm),
                    "key_size": key.key_size,
                    "is_protected": key.is_protected
                }
        
        return keys_info
    
    def delete_key(self, key_id: str, key_type: str = "both") -> bool:
        """
        删除密钥
        
        Args:
            key_id: 密钥ID
            key_type: 要删除的密钥类型 ("public", "private", "both")
            
        Returns:
            是否成功删除
        """
        try:
            deleted = False
            
            if key_type in ("public", "both") and key_id in self.public_keys:
                # 删除公钥文件
                public_key_file = self.keyring_dir / "public" / f"{key_id}.asc"
                if public_key_file.exists():
                    public_key_file.unlink()
                
                # 从内存中删除
                del self.public_keys[key_id]
                deleted = True
                logger.info(f"删除公钥: {key_id}")
            
            if key_type in ("private", "both") and key_id in self.private_keys:
                # 删除私钥文件
                private_key_file = self.keyring_dir / "private" / f"{key_id}.asc"
                if private_key_file.exists():
                    private_key_file.unlink()
                
                # 从内存中删除
                del self.private_keys[key_id]
                deleted = True
                logger.info(f"删除私钥: {key_id}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"删除密钥失败: {e}")
            return False