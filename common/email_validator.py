"""
邮件验证规则 - 确保邮件数据的完整性和正确性
"""

import re
import datetime
from typing import Dict, List, Optional, Any


class EmailValidator:
    """邮件验证器"""
    
    @staticmethod
    def validate_email_data(email_data: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        验证邮件数据的完整性
        
        Args:
            email_data: 邮件数据字典
            
        Returns:
            验证结果，包含错误列表
        """
        errors = []
        warnings = []
        
        # 验证必需字段
        required_fields = ["message_id", "from_addr", "to_addrs", "subject", "date"]
        for field in required_fields:
            if not email_data.get(field):
                errors.append(f"缺少必需字段: {field}")
        
        # 验证邮件地址格式
        if email_data.get("from_addr"):
            if not EmailValidator._is_valid_email(email_data["from_addr"]):
                errors.append(f"发件人邮箱格式无效: {email_data['from_addr']}")
        
        # 验证收件人地址
        to_addrs = email_data.get("to_addrs", [])
        if isinstance(to_addrs, list):
            for addr in to_addrs:
                if not EmailValidator._is_valid_email(addr):
                    errors.append(f"收件人邮箱格式无效: {addr}")
        
        # 验证日期格式
        if email_data.get("date"):
            try:
                if isinstance(email_data["date"], str):
                    datetime.datetime.fromisoformat(email_data["date"])
            except ValueError:
                errors.append(f"日期格式无效: {email_data['date']}")
        
        # 验证Message-ID格式
        message_id = email_data.get("message_id")
        if message_id and not EmailValidator._is_valid_message_id(message_id):
            warnings.append(f"Message-ID格式可能无效: {message_id}")
        
        return {
            "errors": errors,
            "warnings": warnings,
            "is_valid": len(errors) == 0
        }
    
    @staticmethod
    def _is_valid_email(email_addr: str) -> bool:
        """验证邮箱地址格式"""
        if not email_addr or not isinstance(email_addr, str):
            return False
        
        # 简单的邮箱格式验证
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email_addr.strip()) is not None
    
    @staticmethod
    def _is_valid_message_id(message_id: str) -> bool:
        """验证Message-ID格式"""
        if not message_id or not isinstance(message_id, str):
            return False
        
        # Message-ID通常包含@符号，可能被尖括号包围
        message_id = message_id.strip()
        if message_id.startswith('<') and message_id.endswith('>'):
            message_id = message_id[1:-1]
        
        return '@' in message_id and len(message_id) > 3
    
    @staticmethod
    def sanitize_email_data(email_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        清理和标准化邮件数据
        
        Args:
            email_data: 原始邮件数据
            
        Returns:
            清理后的邮件数据
        """
        sanitized = email_data.copy()
        
        # 清理Message-ID
        if sanitized.get("message_id"):
            message_id = str(sanitized["message_id"]).strip()
            if not message_id.startswith('<') and '@' in message_id:
                message_id = f"<{message_id}>"
            sanitized["message_id"] = message_id
        
        # 清理邮箱地址
        if sanitized.get("from_addr"):
            sanitized["from_addr"] = str(sanitized["from_addr"]).strip()
        
        # 清理收件人列表
        if sanitized.get("to_addrs"):
            if isinstance(sanitized["to_addrs"], str):
                sanitized["to_addrs"] = [sanitized["to_addrs"].strip()]
            elif isinstance(sanitized["to_addrs"], list):
                sanitized["to_addrs"] = [str(addr).strip() for addr in sanitized["to_addrs"]]
        
        # 确保日期格式
        if sanitized.get("date"):
            if isinstance(sanitized["date"], str):
                try:
                    # 尝试解析并重新格式化
                    date_obj = datetime.datetime.fromisoformat(sanitized["date"])
                    sanitized["date"] = date_obj.isoformat()
                except ValueError:
                    # 如果解析失败，使用当前时间
                    sanitized["date"] = datetime.datetime.now().isoformat()
            elif not isinstance(sanitized["date"], datetime.datetime):
                sanitized["date"] = datetime.datetime.now().isoformat()
        
        # 确保主题不为空
        if not sanitized.get("subject"):
            sanitized["subject"] = "(无主题)"
        
        return sanitized
