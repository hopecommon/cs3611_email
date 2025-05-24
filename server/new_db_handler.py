"""
新的数据库处理器 - 重构版本，使用模块化设计
提供统一简洁的API，解决原有代码的复杂性问题
"""

import os
import datetime
import json
from typing import List, Dict, Optional, Any, Union

from common.utils import setup_logging
from common.config import DB_PATH, EMAIL_STORAGE_DIR
from .db_connection import DatabaseConnection
from .email_repository import EmailRepository
from .email_content_manager import EmailContentManager
from .db_models import EmailRecord, SentEmailRecord

# 设置日志
logger = setup_logging("new_db_handler")


class EmailService:
    """
    邮件服务类 - 重构版本的数据库处理器

    提供简洁统一的API，内部使用模块化组件
    解决原有DatabaseHandler的复杂性和易错性问题
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        """
        初始化邮件服务

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path

        # 初始化组件
        self.db_connection = DatabaseConnection(db_path)
        self.email_repo = EmailRepository(self.db_connection)
        self.content_manager = EmailContentManager()

        # 初始化数据库
        self.db_connection.init_database()

        logger.info(f"邮件服务已初始化: {db_path}")

    # ==================== 邮件基本操作 ====================

    def save_email(
        self,
        message_id: str,
        from_addr: str,
        to_addrs: Union[List[str], str],
        subject: str = "",
        content: str = "",
        date: Optional[datetime.datetime] = None,
        **kwargs,
    ) -> bool:
        """
        保存邮件（统一接口）

        Args:
            message_id: 邮件ID
            from_addr: 发件人地址
            to_addrs: 收件人地址（可以是字符串或列表）
            subject: 邮件主题
            content: 邮件内容
            date: 邮件日期
            **kwargs: 其他选项（is_spam, spam_score等）

        Returns:
            bool: 操作是否成功
        """
        try:
            # 标准化收件人地址
            if isinstance(to_addrs, str):
                to_addrs = [to_addrs]

            # 使用当前时间作为默认日期
            if not date:
                date = datetime.datetime.now()

            # 保存邮件内容（如果提供）
            content_path = None
            if content:
                content_path = self.content_manager.save_content(message_id, content)

            # 创建邮件记录
            email_record = EmailRecord(
                message_id=message_id,
                from_addr=from_addr,
                to_addrs=to_addrs,
                subject=subject,
                date=date,
                size=len(content) if content else 0,
                is_spam=kwargs.get("is_spam", False),
                spam_score=kwargs.get("spam_score", 0.0),
                content_path=content_path,
            )

            # 保存到数据库
            success = self.email_repo.create_email(email_record)

            if success:
                logger.info(f"邮件保存成功: {message_id}")

            return success
        except Exception as e:
            logger.error(f"保存邮件时出错: {e}")
            return False

    def get_email(
        self, message_id: str, include_content: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        获取邮件（统一接口）

        Args:
            message_id: 邮件ID
            include_content: 是否包含邮件内容

        Returns:
            邮件字典或None
        """
        try:
            # 获取邮件记录
            email_record = self.email_repo.get_email_by_id(message_id)
            if not email_record:
                return None

            # 转换为字典
            email_dict = email_record.to_dict()

            # 如果需要，获取邮件内容
            if include_content:
                content = self.content_manager.get_content(message_id, email_dict)
                email_dict["content"] = content

            return email_dict
        except Exception as e:
            logger.error(f"获取邮件时出错: {e}")
            return None

    def list_emails(
        self,
        user_email: Optional[str] = None,
        include_deleted: bool = False,
        include_spam: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        获取邮件列表（统一接口）

        Args:
            user_email: 用户邮箱过滤
            include_deleted: 是否包含已删除邮件
            include_spam: 是否包含垃圾邮件
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            邮件字典列表
        """
        try:
            email_records = self.email_repo.list_emails(
                user_email=user_email,
                include_deleted=include_deleted,
                include_spam=include_spam,
                limit=limit,
                offset=offset,
            )

            # 转换为字典列表
            return [record.to_dict() for record in email_records]
        except Exception as e:
            logger.error(f"获取邮件列表时出错: {e}")
            return []

    def update_email(self, message_id: str, **updates) -> bool:
        """
        更新邮件状态（统一接口）

        Args:
            message_id: 邮件ID
            **updates: 更新字段（is_read, is_deleted, is_spam等）

        Returns:
            bool: 操作是否成功
        """
        try:
            return self.email_repo.update_email_status(message_id, **updates)
        except Exception as e:
            logger.error(f"更新邮件时出错: {e}")
            return False

    def delete_email(self, message_id: str, permanent: bool = False) -> bool:
        """
        删除邮件（统一接口）

        Args:
            message_id: 邮件ID
            permanent: 是否永久删除（True）或标记删除（False）

        Returns:
            bool: 操作是否成功
        """
        try:
            if permanent:
                return self.email_repo.delete_email(message_id)
            else:
                return self.email_repo.update_email_status(message_id, is_deleted=True)
        except Exception as e:
            logger.error(f"删除邮件时出错: {e}")
            return False

    # ==================== 已发送邮件操作 ====================

    def save_sent_email(
        self,
        message_id: str,
        from_addr: str,
        to_addrs: Union[List[str], str],
        subject: str = "",
        content: str = "",
        date: Optional[datetime.datetime] = None,
        cc_addrs: Optional[List[str]] = None,
        bcc_addrs: Optional[List[str]] = None,
        **kwargs,
    ) -> bool:
        """
        保存已发送邮件

        Args:
            message_id: 邮件ID
            from_addr: 发件人地址
            to_addrs: 收件人地址
            subject: 邮件主题
            content: 邮件内容
            date: 邮件日期
            cc_addrs: 抄送地址
            bcc_addrs: 密送地址
            **kwargs: 其他选项

        Returns:
            bool: 操作是否成功
        """
        try:
            # 标准化地址列表
            if isinstance(to_addrs, str):
                to_addrs = [to_addrs]

            if not date:
                date = datetime.datetime.now()

            # 保存邮件内容
            content_path = None
            if content:
                content_path = self.content_manager.save_content(message_id, content)

            # 创建已发送邮件记录
            sent_record = SentEmailRecord(
                message_id=message_id,
                from_addr=from_addr,
                to_addrs=to_addrs,
                cc_addrs=cc_addrs,
                bcc_addrs=bcc_addrs,
                subject=subject,
                date=date,
                size=len(content) if content else 0,
                has_attachments=kwargs.get("has_attachments", False),
                content_path=content_path,
                status=kwargs.get("status", "sent"),
            )

            return self.email_repo.create_sent_email(sent_record)
        except Exception as e:
            logger.error(f"保存已发送邮件时出错: {e}")
            return False

    def get_sent_email(
        self, message_id: str, include_content: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        获取已发送邮件

        Args:
            message_id: 邮件ID
            include_content: 是否包含邮件内容

        Returns:
            已发送邮件字典或None
        """
        try:
            sent_record = self.email_repo.get_sent_email_by_id(message_id)
            if not sent_record:
                return None

            sent_dict = sent_record.to_dict()

            if include_content:
                content = self.content_manager.get_content(message_id, sent_dict)
                sent_dict["content"] = content

            return sent_dict
        except Exception as e:
            logger.error(f"获取已发送邮件时出错: {e}")
            return None

    def list_sent_emails(
        self, from_addr: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取已发送邮件列表

        Args:
            from_addr: 发件人地址过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            已发送邮件字典列表
        """
        try:
            sent_records = self.email_repo.list_sent_emails(
                from_addr=from_addr, limit=limit, offset=offset
            )

            return [record.to_dict() for record in sent_records]
        except Exception as e:
            logger.error(f"获取已发送邮件列表时出错: {e}")
            return []

    # ==================== 搜索功能 ====================

    def search_emails(
        self,
        query: str,
        search_fields: Optional[List[str]] = None,
        include_sent: bool = True,
        include_received: bool = True,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        搜索邮件（统一接口）

        Args:
            query: 搜索关键词
            search_fields: 搜索字段列表
            include_sent: 是否包含已发送邮件
            include_received: 是否包含接收邮件
            **kwargs: 其他搜索选项

        Returns:
            搜索结果列表
        """
        try:
            return self.email_repo.search_emails(
                query=query,
                search_fields=search_fields,
                include_sent=include_sent,
                include_received=include_received,
                **kwargs,
            )
        except Exception as e:
            logger.error(f"搜索邮件时出错: {e}")
            return []

    # ==================== 兼容性方法 ====================
    # 为了保持向后兼容，提供原有方法的别名

    def get_email_content(self, message_id: str) -> Optional[str]:
        """获取邮件内容（兼容性方法）"""
        email_data = self.get_email(message_id)
        if email_data:
            return self.content_manager.get_content(message_id, email_data)
        return None

    def get_email_metadata(self, message_id: str) -> Optional[Dict[str, Any]]:
        """获取邮件元数据（兼容性方法）"""
        return self.get_email(message_id, include_content=False)

    def save_email_content(self, message_id: str, content: str) -> None:
        """保存邮件内容（兼容性方法）"""
        self.content_manager.save_content(message_id, content)

    def save_email_metadata(
        self,
        message_id: str,
        from_addr: str,
        to_addrs: List[str],
        subject: str,
        date: datetime.datetime,
        size: int,
        is_spam: bool = False,
        spam_score: float = 0.0,
    ) -> None:
        """保存邮件元数据（兼容性方法）"""
        content_path = None
        # 尝试生成内容路径（用于兼容性）
        safe_id = message_id.strip().strip("<>").replace("@", "_at_")
        import re

        safe_id = re.sub(r'[\\/*?:"<>|]', "_", safe_id).strip()
        potential_path = os.path.join(EMAIL_STORAGE_DIR, f"{safe_id}.eml")
        if os.path.exists(potential_path):
            content_path = potential_path

        email_record = EmailRecord(
            message_id=message_id,
            from_addr=from_addr,
            to_addrs=to_addrs,
            subject=subject,
            date=date,
            size=size,
            is_spam=is_spam,
            spam_score=spam_score,
            content_path=content_path,
        )

        self.email_repo.create_email(email_record)

    def mark_email_as_read(self, message_id: str) -> bool:
        """标记邮件为已读（兼容性方法）"""
        return self.update_email(message_id, is_read=True)

    def mark_email_as_deleted(self, message_id: str) -> bool:
        """标记邮件为已删除（兼容性方法）"""
        return self.update_email(message_id, is_deleted=True)

    def mark_email_as_spam(self, message_id: str, spam_score: float = 1.0) -> bool:
        """标记邮件为垃圾邮件（兼容性方法）"""
        return self.update_email(message_id, is_spam=True, spam_score=spam_score)

    def delete_email_metadata(self, message_id: str) -> bool:
        """删除邮件元数据（兼容性方法）"""
        return self.delete_email(message_id, permanent=True)

    def get_sent_email_metadata(self, message_id: str) -> Optional[Dict[str, Any]]:
        """获取已发送邮件元数据（兼容性方法）"""
        return self.get_sent_email(message_id, include_content=False)

    def get_sent_email_content(self, message_id: str) -> Optional[str]:
        """获取已发送邮件内容（兼容性方法）"""
        sent_data = self.get_sent_email(message_id)
        if sent_data:
            return self.content_manager.get_content(message_id, sent_data)
        return None

    def delete_sent_email_metadata(self, message_id: str) -> bool:
        """删除已发送邮件元数据（兼容性方法）"""
        return self.email_repo.delete_sent_email(message_id)

    # ==================== 向后兼容的API ====================
    # 这些方法是为了修复CLI等代码中的错误调用

    def get_emails(
        self, folder: str = "inbox", limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取邮件列表（修复CLI错误调用）"""
        if folder == "sent":
            return self.list_sent_emails(limit=limit, offset=offset)
        else:
            return self.list_emails(limit=limit, offset=offset)

    def get_sent_emails(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取已发送邮件列表（修复CLI错误调用）"""
        return self.list_sent_emails(limit=limit, offset=offset)

    # ==================== 高级功能 ====================

    def get_email_count(self, user_email: Optional[str] = None, **filters) -> int:
        """
        获取邮件数量

        Args:
            user_email: 用户邮箱过滤
            **filters: 其他过滤条件

        Returns:
            邮件数量
        """
        try:
            emails = self.list_emails(
                user_email=user_email,
                include_deleted=filters.get("include_deleted", False),
                include_spam=filters.get("include_spam", False),
                limit=10000,  # 获取大量数据来计数
            )
            return len(emails)
        except Exception as e:
            logger.error(f"获取邮件数量时出错: {e}")
            return 0

    def get_unread_count(self, user_email: Optional[str] = None) -> int:
        """
        获取未读邮件数量

        Args:
            user_email: 用户邮箱过滤

        Returns:
            未读邮件数量
        """
        try:
            emails = self.list_emails(user_email=user_email, limit=10000)
            return len([email for email in emails if not email.get("is_read", False)])
        except Exception as e:
            logger.error(f"获取未读邮件数量时出错: {e}")
            return 0

    # ==================== 数据库维护 ====================

    def init_db(self) -> None:
        """初始化数据库（兼容性方法）"""
        self.db_connection.init_database()

    def vacuum_database(self) -> bool:
        """压缩数据库"""
        try:
            self.db_connection.execute_query("VACUUM")
            logger.info("数据库压缩完成")
            return True
        except Exception as e:
            logger.error(f"压缩数据库时出错: {e}")
            return False


# 为了保持向后兼容，创建原名称的别名
DatabaseHandler = EmailService
