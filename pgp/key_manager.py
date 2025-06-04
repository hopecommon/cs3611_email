"""
PGP密钥管理模块 - 提供密钥管理的便捷接口

简化PGP密钥的管理操作，包括生成、导入、导出、删除等
"""

import os
import logging
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import json
from datetime import datetime

from .pgp_manager import PGPManager, PGPError
from common.utils import setup_logging

logger = setup_logging("key_manager")


class KeyManager:
    """PGP密钥管理器"""
    
    def __init__(self, pgp_manager: Optional[PGPManager] = None):
        """
        初始化密钥管理器
        
        Args:
            pgp_manager: PGP管理器实例
        """
        self.pgp_manager = pgp_manager or PGPManager()
        self.user_keymap_file = self.pgp_manager.keyring_dir / "user_keymap.json"
        self.user_keymap = self._load_user_keymap()
        
        logger.info("密钥管理器初始化完成")
    
    def _load_user_keymap(self) -> Dict[str, str]:
        """加载用户邮箱到密钥ID的映射"""
        if self.user_keymap_file.exists():
            try:
                with open(self.user_keymap_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载用户密钥映射失败: {e}")
        return {}
    
    def _save_user_keymap(self) -> None:
        """保存用户邮箱到密钥ID的映射"""
        try:
            with open(self.user_keymap_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_keymap, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存用户密钥映射失败: {e}")
    
    def create_user_keypair(self, 
                           name: str, 
                           email: str, 
                           passphrase: Optional[str] = None,
                           comment: str = "",
                           key_size: int = 4096) -> str:
        """
        为用户创建PGP密钥对
        
        Args:
            name: 用户姓名
            email: 用户邮箱
            passphrase: 私钥密码
            comment: 密钥注释
            key_size: 密钥长度
            
        Returns:
            密钥ID
        """
        try:
            logger.info(f"为用户 {name} <{email}> 创建PGP密钥对")
            
            # 检查是否已存在该邮箱的密钥
            if email in self.user_keymap:
                existing_key_id = self.user_keymap[email]
                logger.warning(f"用户 {email} 已有密钥: {existing_key_id}")
                return existing_key_id
            
            # 生成密钥对
            public_key_id, private_key_id = self.pgp_manager.generate_key_pair(
                name, email, passphrase, key_size, comment
            )
            
            # 更新用户密钥映射
            self.user_keymap[email] = private_key_id
            self._save_user_keymap()
            
            logger.info(f"用户 {email} 的PGP密钥对创建成功: {private_key_id}")
            return private_key_id
            
        except Exception as e:
            logger.error(f"创建用户密钥对失败: {e}")
            raise PGPError(f"创建用户密钥对失败: {e}")
    
    def import_user_key(self, 
                       email: str,
                       key_data: str, 
                       is_private: bool = False) -> str:
        """
        为用户导入PGP密钥
        
        Args:
            email: 用户邮箱
            key_data: 密钥数据
            is_private: 是否为私钥
            
        Returns:
            密钥ID
        """
        try:
            logger.info(f"为用户 {email} 导入PGP{'私钥' if is_private else '公钥'}")
            
            key_id = self.pgp_manager.import_key(key_data, is_private)
            
            # 如果是私钥，更新用户密钥映射
            if is_private:
                self.user_keymap[email] = key_id
                self._save_user_keymap()
            
            logger.info(f"用户 {email} 的PGP密钥导入成功: {key_id}")
            return key_id
            
        except Exception as e:
            logger.error(f"导入用户密钥失败: {e}")
            raise PGPError(f"导入用户密钥失败: {e}")
    
    def get_user_private_key_id(self, email: str) -> Optional[str]:
        """
        获取用户的私钥ID
        
        Args:
            email: 用户邮箱
            
        Returns:
            私钥ID（如果存在）
        """
        return self.user_keymap.get(email)
    
    def get_user_public_key_id(self, email: str) -> Optional[str]:
        """
        获取用户的公钥ID
        
        Args:
            email: 用户邮箱
            
        Returns:
            公钥ID（如果存在）
        """
        # 先检查映射表
        if email in self.user_keymap:
            key_id = self.user_keymap[email]
            # 检查是否有对应的公钥
            if key_id in self.pgp_manager.public_keys:
                return key_id
        
        # 搜索所有公钥
        for key_id, key in self.pgp_manager.public_keys.items():
            for userid in key.userids:
                if email.lower() in str(userid).lower():
                    return key_id
        
        return None
    
    def list_user_keys(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有用户的密钥信息
        
        Returns:
            用户密钥信息字典
        """
        user_keys = {}
        
        for email, key_id in self.user_keymap.items():
            key_info = {
                "email": email,
                "key_id": key_id,
                "has_private_key": key_id in self.pgp_manager.private_keys,
                "has_public_key": key_id in self.pgp_manager.public_keys
            }
            
            # 获取密钥详细信息
            if key_id in self.pgp_manager.private_keys:
                private_key = self.pgp_manager.private_keys[key_id]
                key_info.update({
                    "created": private_key.created.isoformat(),
                    "fingerprint": str(private_key.fingerprint),
                    "algorithm": str(private_key.key_algorithm),
                    "key_size": private_key.key_size,
                    "is_protected": private_key.is_protected,
                    "userids": [str(uid) for uid in private_key.userids]
                })
            elif key_id in self.pgp_manager.public_keys:
                public_key = self.pgp_manager.public_keys[key_id]
                key_info.update({
                    "created": public_key.created.isoformat(),
                    "fingerprint": str(public_key.fingerprint),
                    "algorithm": str(public_key.key_algorithm),
                    "key_size": public_key.key_size,
                    "userids": [str(uid) for uid in public_key.userids]
                })
            
            user_keys[email] = key_info
        
        return user_keys
    
    def export_user_public_key(self, email: str) -> Optional[str]:
        """
        导出用户的公钥
        
        Args:
            email: 用户邮箱
            
        Returns:
            公钥数据（ASCII armored格式）
        """
        try:
            key_id = self.get_user_public_key_id(email)
            if not key_id:
                logger.warning(f"用户 {email} 没有公钥")
                return None
            
            return self.pgp_manager.export_key(key_id, is_private=False)
            
        except Exception as e:
            logger.error(f"导出用户公钥失败: {e}")
            return None
    
    def export_user_private_key(self, email: str) -> Optional[str]:
        """
        导出用户的私钥
        
        Args:
            email: 用户邮箱
            
        Returns:
            私钥数据（ASCII armored格式）
        """
        try:
            key_id = self.get_user_private_key_id(email)
            if not key_id:
                logger.warning(f"用户 {email} 没有私钥")
                return None
            
            return self.pgp_manager.export_key(key_id, is_private=True)
            
        except Exception as e:
            logger.error(f"导出用户私钥失败: {e}")
            return None
    
    def delete_user_keys(self, email: str, delete_private: bool = True, delete_public: bool = True) -> bool:
        """
        删除用户的密钥
        
        Args:
            email: 用户邮箱
            delete_private: 是否删除私钥
            delete_public: 是否删除公钥
            
        Returns:
            是否成功删除
        """
        try:
            key_id = self.user_keymap.get(email)
            if not key_id:
                logger.warning(f"用户 {email} 没有密钥记录")
                return False
            
            success = False
            
            if delete_private and key_id in self.pgp_manager.private_keys:
                if self.pgp_manager.delete_key(key_id, "private"):
                    success = True
                    logger.info(f"删除用户 {email} 的私钥: {key_id}")
            
            if delete_public and key_id in self.pgp_manager.public_keys:
                if self.pgp_manager.delete_key(key_id, "public"):
                    success = True
                    logger.info(f"删除用户 {email} 的公钥: {key_id}")
            
            # 如果删除了所有密钥，从映射表中移除
            if delete_private and delete_public:
                if email in self.user_keymap:
                    del self.user_keymap[email]
                    self._save_user_keymap()
            
            return success
            
        except Exception as e:
            logger.error(f"删除用户密钥失败: {e}")
            return False
    
    def validate_user_setup(self, email: str) -> Dict[str, Any]:
        """
        验证用户的PGP设置
        
        Args:
            email: 用户邮箱
            
        Returns:
            验证结果
        """
        result = {
            "email": email,
            "has_keypair": False,
            "has_private_key": False,
            "has_public_key": False,
            "private_key_protected": False,
            "key_id": None,
            "errors": [],
            "warnings": []
        }
        
        try:
            # 检查私钥
            private_key_id = self.get_user_private_key_id(email)
            if private_key_id:
                result["has_private_key"] = True
                result["key_id"] = private_key_id
                
                if private_key_id in self.pgp_manager.private_keys:
                    private_key = self.pgp_manager.private_keys[private_key_id]
                    result["private_key_protected"] = private_key.is_protected
                else:
                    result["errors"].append("私钥ID存在但密钥文件丢失")
            else:
                result["errors"].append("未找到私钥")
            
            # 检查公钥
            public_key_id = self.get_user_public_key_id(email)
            if public_key_id:
                result["has_public_key"] = True
                if not result["key_id"]:
                    result["key_id"] = public_key_id
            else:
                result["errors"].append("未找到公钥")
            
            # 检查密钥对
            if result["has_private_key"] and result["has_public_key"]:
                result["has_keypair"] = True
            
            # 添加警告
            if result["has_private_key"] and not result["private_key_protected"]:
                result["warnings"].append("私钥未设置密码保护，建议添加密码")
            
            if not result["has_keypair"]:
                result["warnings"].append("建议生成完整的PGP密钥对")
            
        except Exception as e:
            result["errors"].append(f"验证过程出错: {e}")
        
        return result
    
    def setup_user_pgp(self, 
                      name: str,
                      email: str, 
                      passphrase: Optional[str] = None,
                      force_recreate: bool = False) -> Dict[str, Any]:
        """
        为用户设置PGP（一站式设置）
        
        Args:
            name: 用户姓名
            email: 用户邮箱
            passphrase: 私钥密码
            force_recreate: 是否强制重新创建（如果已存在）
            
        Returns:
            设置结果
        """
        result = {
            "success": False,
            "key_id": None,
            "message": "",
            "created_new": False
        }
        
        try:
            # 检查现有设置
            validation = self.validate_user_setup(email)
            
            if validation["has_keypair"] and not force_recreate:
                result["success"] = True
                result["key_id"] = validation["key_id"]
                result["message"] = "用户已有完整的PGP密钥对"
                return result
            
            # 如果强制重新创建，先删除现有密钥
            if force_recreate and validation["has_keypair"]:
                logger.info(f"强制重新创建用户 {email} 的PGP密钥对")
                self.delete_user_keys(email)
            
            # 创建新的密钥对
            key_id = self.create_user_keypair(name, email, passphrase)
            
            result["success"] = True
            result["key_id"] = key_id
            result["created_new"] = True
            result["message"] = "PGP密钥对创建成功"
            
            logger.info(f"用户 {email} 的PGP设置完成: {key_id}")
            
        except Exception as e:
            result["message"] = f"PGP设置失败: {e}"
            logger.error(f"用户PGP设置失败: {e}")
        
        return result
    
    def import_contact_public_key(self, contact_email: str, public_key_data: str) -> str:
        """
        导入联系人的公钥
        
        Args:
            contact_email: 联系人邮箱
            public_key_data: 公钥数据
            
        Returns:
            密钥ID
        """
        try:
            logger.info(f"导入联系人 {contact_email} 的公钥")
            
            key_id = self.pgp_manager.import_key(public_key_data, is_private=False)
            
            # 不需要添加到用户映射表，因为这是联系人的公钥
            logger.info(f"联系人 {contact_email} 的公钥导入成功: {key_id}")
            return key_id
            
        except Exception as e:
            logger.error(f"导入联系人公钥失败: {e}")
            raise PGPError(f"导入联系人公钥失败: {e}")
    
    def get_available_recipients(self) -> List[Dict[str, Any]]:
        """
        获取可以发送加密邮件的收件人列表
        
        Returns:
            收件人信息列表
        """
        recipients = []
        
        for key_id, key in self.pgp_manager.public_keys.items():
            for userid in key.userids:
                userid_str = str(userid)
                # 提取邮箱地址
                import re
                email_match = re.search(r'<([^>]+)>', userid_str)
                if email_match:
                    email = email_match.group(1)
                    recipients.append({
                        "email": email,
                        "name": userid_str.split('<')[0].strip(),
                        "key_id": key_id,
                        "fingerprint": str(key.fingerprint),
                        "created": key.created.isoformat()
                    })
        
        return recipients 