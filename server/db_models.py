"""
数据库模型定义 - 定义邮件和用户相关的数据模型
"""

import datetime
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class EmailRecord:
    """邮件记录数据模型"""

    message_id: str
    from_addr: str
    to_addrs: List[str]
    subject: str
    date: datetime.datetime
    size: int
    is_read: bool = False
    is_deleted: bool = False
    is_spam: bool = False
    spam_score: float = 0.0
    content_path: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmailRecord":
        """从字典创建邮件记录"""
        # 处理to_addrs字段的JSON解析
        to_addrs = data.get("to_addrs", [])
        if isinstance(to_addrs, str):
            try:
                to_addrs = json.loads(to_addrs)
            except json.JSONDecodeError:
                to_addrs = [to_addrs]

        # 处理日期字段
        date = data.get("date")
        if isinstance(date, str):
            try:
                date = datetime.datetime.fromisoformat(date)
            except ValueError:
                date = datetime.datetime.now()
        elif not isinstance(date, datetime.datetime):
            date = datetime.datetime.now()

        return cls(
            message_id=data.get("message_id", ""),
            from_addr=data.get("from_addr", ""),
            to_addrs=to_addrs if isinstance(to_addrs, list) else [str(to_addrs)],
            subject=data.get("subject", ""),
            date=date,
            size=data.get("size", 0),
            is_read=bool(data.get("is_read", False)),
            is_deleted=bool(data.get("is_deleted", False)),
            is_spam=bool(data.get("is_spam", False)),
            spam_score=float(data.get("spam_score", 0.0)),
            content_path=data.get("content_path"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "from_addr": self.from_addr,
            "to_addrs": self.to_addrs,
            "subject": self.subject,
            "date": self.date.isoformat() if self.date else None,
            "size": self.size,
            "is_read": self.is_read,
            "is_deleted": self.is_deleted,
            "is_spam": self.is_spam,
            "spam_score": self.spam_score,
            "content_path": self.content_path,
        }


@dataclass
class SentEmailRecord:
    """已发送邮件记录数据模型"""

    message_id: str
    from_addr: str
    to_addrs: List[str]
    cc_addrs: Optional[List[str]]
    bcc_addrs: Optional[List[str]]
    subject: str
    date: datetime.datetime
    size: int
    has_attachments: bool = False
    content_path: Optional[str] = None
    status: str = "sent"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SentEmailRecord":
        """从字典创建已发送邮件记录"""

        # 处理地址字段的JSON解析
        def parse_addrs(addrs):
            if isinstance(addrs, str):
                try:
                    return json.loads(addrs)
                except json.JSONDecodeError:
                    return [addrs]
            return addrs if isinstance(addrs, list) else []

        # 处理日期字段
        date = data.get("date")
        if isinstance(date, str):
            try:
                date = datetime.datetime.fromisoformat(date)
            except ValueError:
                date = datetime.datetime.now()
        elif not isinstance(date, datetime.datetime):
            date = datetime.datetime.now()

        return cls(
            message_id=data.get("message_id", ""),
            from_addr=data.get("from_addr", ""),
            to_addrs=parse_addrs(data.get("to_addrs", [])),
            cc_addrs=(
                parse_addrs(data.get("cc_addrs")) if data.get("cc_addrs") else None
            ),
            bcc_addrs=(
                parse_addrs(data.get("bcc_addrs")) if data.get("bcc_addrs") else None
            ),
            subject=data.get("subject", ""),
            date=date,
            size=data.get("size", 0),
            has_attachments=bool(data.get("has_attachments", False)),
            content_path=data.get("content_path"),
            status=data.get("status", "sent"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "from_addr": self.from_addr,
            "to_addrs": self.to_addrs,
            "cc_addrs": self.cc_addrs,
            "bcc_addrs": self.bcc_addrs,
            "subject": self.subject,
            "date": self.date.isoformat() if self.date else None,
            "size": self.size,
            "has_attachments": self.has_attachments,
            "content_path": self.content_path,
            "status": self.status,
        }


@dataclass
class UserRecord:
    """用户记录数据模型"""

    username: str
    email: str
    password_hash: str
    salt: str
    full_name: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime.datetime] = None
    last_login: Optional[datetime.datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserRecord":
        """从字典创建用户记录"""
        # 处理日期字段
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            try:
                created_at = datetime.datetime.fromisoformat(created_at)
            except ValueError:
                created_at = None

        last_login = data.get("last_login")
        if isinstance(last_login, str):
            try:
                last_login = datetime.datetime.fromisoformat(last_login)
            except ValueError:
                last_login = None

        return cls(
            username=data.get("username", ""),
            email=data.get("email", ""),
            password_hash=data.get("password_hash", ""),
            salt=data.get("salt", ""),
            full_name=data.get("full_name"),
            is_active=bool(data.get("is_active", True)),
            created_at=created_at,
            last_login=last_login,
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "salt": self.salt,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }
