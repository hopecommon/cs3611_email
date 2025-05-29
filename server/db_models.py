"""
数据库模型定义 - 定义邮件和用户相关的数据模型
"""

import datetime
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field


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
    matched_keywords: List[str] = field(default_factory=list)
    content_path: Optional[str] = None
    # 撤回相关字段
    is_recalled: bool = False
    recalled_at: Optional[datetime.datetime] = None
    recalled_by: Optional[str] = None

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
                # 尝试其他日期格式
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        date = datetime.datetime.strptime(date, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    date = datetime.datetime.now()
        elif not isinstance(date, datetime.datetime):
            date = datetime.datetime.now()

        # 处理撤回时间字段
        recalled_at = data.get("recalled_at")
        if recalled_at and isinstance(recalled_at, str):
            try:
                recalled_at = datetime.datetime.fromisoformat(recalled_at)
            except ValueError:
                recalled_at = None

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
            # 撤回字段
            is_recalled=bool(data.get("is_recalled", False)),
            recalled_at=recalled_at,
            recalled_by=data.get("recalled_by"),
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
            # 撤回字段
            "is_recalled": self.is_recalled,
            "recalled_at": self.recalled_at.isoformat() if self.recalled_at else None,
            "recalled_by": self.recalled_by,
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
    is_read: bool = False
    is_spam: bool = False
    spam_score: float = 0.0
    # 撤回相关字段
    is_recalled: bool = False
    recalled_at: Optional[datetime.datetime] = None
    recalled_by: Optional[str] = None

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

        to_addrs = parse_addrs(data["to_addrs"])
        cc_addrs = parse_addrs(data.get("cc_addrs")) if data.get("cc_addrs") else None
        bcc_addrs = (
            parse_addrs(data.get("bcc_addrs")) if data.get("bcc_addrs") else None
        )

        # 处理日期字段
        date = data["date"]
        if isinstance(date, str):
            try:
                date = datetime.datetime.fromisoformat(date)
            except ValueError:
                # 尝试其他日期格式
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        date = datetime.datetime.strptime(date, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    date = datetime.datetime.now()

        # 处理撤回时间字段
        recalled_at = data.get("recalled_at")
        if recalled_at and isinstance(recalled_at, str):
            try:
                recalled_at = datetime.datetime.fromisoformat(recalled_at)
            except ValueError:
                recalled_at = None

        return cls(
            message_id=data["message_id"],
            from_addr=data["from_addr"],
            to_addrs=to_addrs,
            cc_addrs=cc_addrs,
            bcc_addrs=bcc_addrs,
            subject=data.get("subject", ""),
            date=date,
            size=data.get("size", 0),
            has_attachments=bool(data.get("has_attachments", False)),
            content_path=data.get("content_path"),
            status=data.get("status", "sent"),
            is_read=bool(data.get("is_read", False)),
            is_spam=bool(data.get("is_spam", False)),
            spam_score=float(data.get("spam_score", 0.0)),
            # 撤回字段
            is_recalled=bool(data.get("is_recalled", False)),
            recalled_at=recalled_at,
            recalled_by=data.get("recalled_by"),
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
            "is_read": self.is_read,
            "is_spam": self.is_spam,
            "spam_score": self.spam_score,
            # 撤回字段
            "is_recalled": self.is_recalled,
            "recalled_at": self.recalled_at.isoformat() if self.recalled_at else None,
            "recalled_by": self.recalled_by,
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

    # 邮箱配置字段
    mail_display_name: str = ""
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_use_tls: bool = True
    smtp_username: str = ""
    encrypted_smtp_password: str = ""
    pop3_server: str = ""
    pop3_port: int = 995
    pop3_use_ssl: bool = True
    pop3_username: str = ""
    encrypted_pop3_password: str = ""
    smtp_configured: bool = False
    pop3_configured: bool = False

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
            # 邮箱配置字段
            mail_display_name=data.get("mail_display_name", ""),
            smtp_server=data.get("smtp_server", ""),
            smtp_port=int(data.get("smtp_port", 587)),
            smtp_use_tls=bool(data.get("smtp_use_tls", True)),
            smtp_username=data.get("smtp_username", ""),
            encrypted_smtp_password=data.get("encrypted_smtp_password", ""),
            pop3_server=data.get("pop3_server", ""),
            pop3_port=int(data.get("pop3_port", 995)),
            pop3_use_ssl=bool(data.get("pop3_use_ssl", True)),
            pop3_username=data.get("pop3_username", ""),
            encrypted_pop3_password=data.get("encrypted_pop3_password", ""),
            smtp_configured=bool(data.get("smtp_configured", False)),
            pop3_configured=bool(data.get("pop3_configured", False)),
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
            # 邮箱配置字段
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
