"""
数据模型模块 - 定义应用程序的数据结构
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import os
from enum import Enum

class EmailStatus(Enum):
    """邮件状态枚举"""
    DRAFT = "draft"        # 草稿
    SENT = "sent"          # 已发送
    RECEIVED = "received"  # 已接收
    DELETED = "deleted"    # 已删除
    SPAM = "spam"          # 垃圾邮件

class EmailPriority(Enum):
    """邮件优先级枚举"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"

@dataclass
class Attachment:
    """附件数据模型"""
    filename: str
    content_type: str
    content: bytes
    size: int = 0
    
    def __post_init__(self):
        if self.size == 0 and self.content:
            self.size = len(self.content)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "filename": self.filename,
            "content_type": self.content_type,
            "size": self.size,
            # 二进制内容需要特殊处理
            "content_b64": None  # 实际使用时需要进行base64编码
        }

@dataclass
class EmailAddress:
    """邮件地址数据模型"""
    name: str
    address: str
    
    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.address}>"
        return self.address
    
    def to_dict(self) -> Dict[str, str]:
        """转换为字典"""
        return {
            "name": self.name,
            "address": self.address
        }

@dataclass
class Email:
    """邮件数据模型"""
    # 基本信息
    message_id: str
    subject: str
    from_addr: EmailAddress
    to_addrs: List[EmailAddress]
    cc_addrs: List[EmailAddress] = field(default_factory=list)
    bcc_addrs: List[EmailAddress] = field(default_factory=list)
    
    # 内容
    text_content: str = ""
    html_content: str = ""
    attachments: List[Attachment] = field(default_factory=list)
    
    # 元数据
    date: datetime = field(default_factory=datetime.now)
    status: EmailStatus = EmailStatus.DRAFT
    priority: EmailPriority = EmailPriority.NORMAL
    is_read: bool = False
    spam_score: float = 0.0
    
    # 服务器信息
    server_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: List[str] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "message_id": self.message_id,
            "subject": self.subject,
            "from_addr": self.from_addr.to_dict(),
            "to_addrs": [addr.to_dict() for addr in self.to_addrs],
            "cc_addrs": [addr.to_dict() for addr in self.cc_addrs],
            "bcc_addrs": [addr.to_dict() for addr in self.bcc_addrs],
            "text_content": self.text_content,
            "html_content": self.html_content,
            "attachments": [att.to_dict() for att in self.attachments],
            "date": self.date.isoformat(),
            "status": self.status.value,
            "priority": self.priority.value,
            "is_read": self.is_read,
            "spam_score": self.spam_score,
            "server_id": self.server_id,
            "in_reply_to": self.in_reply_to,
            "references": self.references,
            "headers": self.headers
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Email':
        """从字典创建Email对象"""
        # 处理嵌套对象
        from_addr = EmailAddress(**data["from_addr"])
        to_addrs = [EmailAddress(**addr) for addr in data["to_addrs"]]
        cc_addrs = [EmailAddress(**addr) for addr in data.get("cc_addrs", [])]
        bcc_addrs = [EmailAddress(**addr) for addr in data.get("bcc_addrs", [])]
        
        # 处理日期
        date = datetime.fromisoformat(data["date"])
        
        # 处理枚举
        status = EmailStatus(data["status"])
        priority = EmailPriority(data["priority"])
        
        # 创建Email对象
        return cls(
            message_id=data["message_id"],
            subject=data["subject"],
            from_addr=from_addr,
            to_addrs=to_addrs,
            cc_addrs=cc_addrs,
            bcc_addrs=bcc_addrs,
            text_content=data.get("text_content", ""),
            html_content=data.get("html_content", ""),
            date=date,
            status=status,
            priority=priority,
            is_read=data.get("is_read", False),
            spam_score=data.get("spam_score", 0.0),
            server_id=data.get("server_id"),
            in_reply_to=data.get("in_reply_to"),
            references=data.get("references", []),
            headers=data.get("headers", {})
        )

@dataclass
class User:
    """用户数据模型"""
    username: str
    email: str
    password_hash: str
    salt: str
    full_name: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "salt": self.salt,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """从字典创建User对象"""
        created_at = datetime.fromisoformat(data["created_at"])
        last_login = datetime.fromisoformat(data["last_login"]) if data.get("last_login") else None
        
        return cls(
            username=data["username"],
            email=data["email"],
            password_hash=data["password_hash"],
            salt=data["salt"],
            full_name=data.get("full_name", ""),
            is_active=data.get("is_active", True),
            created_at=created_at,
            last_login=last_login
        )
