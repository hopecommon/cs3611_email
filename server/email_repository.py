"""
邮件仓储 - 专门负责邮件相关的数据库操作
"""

import os
import json
import datetime
import re
from typing import List, Dict, Optional, Any

from common.utils import setup_logging
from common.config import EMAIL_STORAGE_DIR
from .db_connection import DatabaseConnection
from .db_models import EmailRecord, SentEmailRecord

# 设置日志
logger = setup_logging("email_repository")


class EmailRepository:
    """邮件数据仓储类"""

    def __init__(self, db_connection: DatabaseConnection):
        """
        初始化邮件仓储

        Args:
            db_connection: 数据库连接管理器
        """
        self.db = db_connection
        logger.info("邮件仓储已初始化")

    def create_email(self, email_record: EmailRecord) -> bool:
        """
        创建新邮件记录

        Args:
            email_record: 邮件记录对象

        Returns:
            bool: 操作是否成功
        """
        try:
            # 转换地址列表为JSON
            data = email_record.to_dict()
            data["to_addrs"] = json.dumps(data["to_addrs"])

            # 转换布尔值为整数
            data["is_read"] = 1 if data["is_read"] else 0
            data["is_deleted"] = 1 if data["is_deleted"] else 0
            data["is_spam"] = 1 if data["is_spam"] else 0

            # 插入数据
            success = self.db.execute_insert("emails", data)

            if success:
                logger.info(f"已创建邮件记录: {email_record.message_id}")

            return success
        except Exception as e:
            logger.error(f"创建邮件记录时出错: {e}")
            return False

    def get_email_by_id(self, message_id: str) -> Optional[EmailRecord]:
        """
        根据邮件ID获取邮件记录

        Args:
            message_id: 邮件ID

        Returns:
            EmailRecord或None
        """
        try:
            result = self.db.execute_query(
                "SELECT * FROM emails WHERE message_id = ?",
                (message_id,),
                fetch_one=True,
            )

            if result:
                return EmailRecord.from_dict(result)
            return None
        except Exception as e:
            logger.error(f"获取邮件记录时出错: {e}")
            return None

    def list_emails(
        self,
        user_email: Optional[str] = None,
        include_deleted: bool = False,
        include_spam: bool = False,
        is_spam: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EmailRecord]:
        """
        获取邮件列表

        Args:
            user_email: 用户邮箱（如果指定，只返回发给该用户的邮件）
            include_deleted: 是否包含已删除的邮件
            include_spam: 是否包含垃圾邮件
            limit: 返回的最大数量
            offset: 偏移量

        Returns:
            邮件记录列表
        """
        try:
            # 构建查询
            query = "SELECT * FROM emails WHERE 1=1"
            params = []

            # 用户过滤
            if user_email:
                query += """ AND (
                    to_addrs LIKE ? OR
                    to_addrs LIKE ? OR
                    to_addrs LIKE ? OR
                    to_addrs LIKE ? OR
                    to_addrs LIKE ? OR
                    from_addr = ? OR
                    from_addr LIKE ?
                )"""
                params.extend(
                    [
                        f'%"address":"{user_email}"%',
                        f'%"{user_email}"%',
                        f"%<{user_email}>%",
                        f"%{user_email}%",
                        f'%"email":"{user_email}"%',
                        user_email,
                        f"%{user_email}%",
                    ]
                )

            # 删除状态过滤
            if not include_deleted:
                query += " AND is_deleted = 0"

            # 垃圾邮件过滤
            if not include_spam:
                query += " AND is_spam = 0"

            # is_spam 过滤条件
            if is_spam is not None:
                query += " AND is_spam = ?"
                params.append(1 if is_spam else 0)  # SQLite用1/0表示布尔

            # 排序和分页
            query += " ORDER BY date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            # 执行查询
            results = self.db.execute_query(query, tuple(params), fetch_all=True)

            # 转换为EmailRecord对象
            email_records = []
            for result in results:
                try:
                    email_record = EmailRecord.from_dict(result)
                    email_records.append(email_record)
                except Exception as e:
                    logger.warning(f"解析邮件记录时出错: {e}")
                    continue

            return email_records
        except Exception as e:
            logger.error(f"获取邮件列表时出错: {e}")
            return []

    def update_email_status(self, message_id: str, **status_updates) -> bool:
        """
        更新邮件状态

        Args:
            message_id: 邮件ID
            **status_updates: 状态更新字典（is_read, is_deleted, is_spam等）

        Returns:
            bool: 操作是否成功
        """
        try:
            # 过滤有效的状态字段
            valid_fields = {"is_read", "is_deleted", "is_spam", "spam_score"}
            data = {}

            for key, value in status_updates.items():
                if key in valid_fields:
                    if key in ["is_read", "is_deleted", "is_spam"]:
                        data[key] = 1 if value else 0
                    else:
                        data[key] = value

            if not data:
                logger.warning("没有有效的状态更新字段")
                return False

            success = self.db.execute_update(
                "emails", data, "message_id = ?", (message_id,)
            )

            if success:
                logger.info(f"已更新邮件状态: {message_id}")

            return success
        except Exception as e:
            logger.error(f"更新邮件状态时出错: {e}")
            return False

    def delete_email(self, message_id: str) -> bool:
        """
        删除邮件记录

        Args:
            message_id: 邮件ID

        Returns:
            bool: 操作是否成功
        """
        try:
            success = self.db.execute_delete("emails", "message_id = ?", (message_id,))

            if success:
                logger.info(f"已删除邮件记录: {message_id}")

            return success
        except Exception as e:
            logger.error(f"删除邮件记录时出错: {e}")
            return False

    def create_sent_email(self, sent_email_record: SentEmailRecord) -> bool:
        """
        创建已发送邮件记录

        Args:
            sent_email_record: 已发送邮件记录对象

        Returns:
            bool: 操作是否成功
        """
        try:
            # 转换地址列表为JSON
            data = sent_email_record.to_dict()
            data["to_addrs"] = json.dumps(data["to_addrs"])

            # 处理可选的地址字段，确保None和空列表都正确处理
            if data["cc_addrs"] is not None:
                data["cc_addrs"] = json.dumps(data["cc_addrs"])
            else:
                data["cc_addrs"] = None

            if data["bcc_addrs"] is not None:
                data["bcc_addrs"] = json.dumps(data["bcc_addrs"])
            else:
                data["bcc_addrs"] = None

            # 转换布尔值为整数
            data["has_attachments"] = 1 if data["has_attachments"] else 0
            data["is_read"] = 1 if data["is_read"] else 0

            # 插入数据
            success = self.db.execute_insert("sent_emails", data)

            if success:
                logger.info(f"已创建已发送邮件记录: {sent_email_record.message_id}")

            return success
        except Exception as e:
            logger.error(f"创建已发送邮件记录时出错: {e}")
            return False

    def get_sent_email_by_id(self, message_id: str) -> Optional[SentEmailRecord]:
        """
        根据邮件ID获取已发送邮件记录

        Args:
            message_id: 邮件ID

        Returns:
            SentEmailRecord或None
        """
        try:
            result = self.db.execute_query(
                "SELECT * FROM sent_emails WHERE message_id = ?",
                (message_id,),
                fetch_one=True,
            )

            if result:
                return SentEmailRecord.from_dict(result)
            return None
        except Exception as e:
            logger.error(f"获取已发送邮件记录时出错: {e}")
            return None

    def list_sent_emails(
        self,
        from_addr: Optional[str] = None,
        include_spam: bool = True,
        is_spam: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SentEmailRecord]:
        """
        获取已发送邮件列表

        Args:
            from_addr: 发件人地址
            include_spam: 是否包含垃圾邮件
            is_spam: 垃圾邮件过滤（None=全部，True=仅垃圾邮件，False=仅正常邮件）
            limit: 返回的最大数量
            offset: 偏移量

        Returns:
            已发送邮件记录列表
        """
        try:
            # 构建查询
            query = "SELECT * FROM sent_emails WHERE 1=1"
            params = []

            # 发件人过滤
            if from_addr:
                query += " AND from_addr = ?"
                params.append(from_addr)

            # 垃圾邮件过滤
            if not include_spam:
                query += " AND (is_spam = 0 OR is_spam IS NULL)"
            elif is_spam is not None:
                if is_spam:
                    query += " AND is_spam = 1"
                else:
                    query += " AND (is_spam = 0 OR is_spam IS NULL)"

            # 排序和分页
            query += " ORDER BY date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            # 执行查询
            results = self.db.execute_query(query, tuple(params), fetch_all=True)

            # 转换为SentEmailRecord对象
            sent_email_records = []
            for result in results:
                try:
                    sent_email_record = SentEmailRecord.from_dict(result)
                    sent_email_records.append(sent_email_record)
                except Exception as e:
                    logger.warning(f"解析已发送邮件记录时出错: {e}")
                    continue

            return sent_email_records
        except Exception as e:
            logger.error(f"获取已发送邮件列表时出错: {e}")
            return []

    def delete_sent_email(self, message_id: str) -> bool:
        """
        删除已发送邮件记录

        Args:
            message_id: 邮件ID

        Returns:
            bool: 操作是否成功
        """
        try:
            success = self.db.execute_delete(
                "sent_emails", "message_id = ?", (message_id,)
            )

            if success:
                logger.info(f"已删除已发送邮件记录: {message_id}")

            return success
        except Exception as e:
            logger.error(f"删除已发送邮件记录时出错: {e}")
            return False

    def search_emails(
        self,
        query: str,
        search_fields: List[str] = None,
        include_sent: bool = True,
        include_received: bool = True,
        include_deleted: bool = False,
        include_spam: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        搜索邮件

        Args:
            query: 搜索关键词
            search_fields: 要搜索的字段列表
            include_sent: 是否包含已发送邮件
            include_received: 是否包含接收邮件
            include_deleted: 是否包含已删除邮件
            include_spam: 是否包含垃圾邮件
            limit: 返回的最大数量

        Returns:
            搜索结果列表
        """
        if not query:
            return []

        # 默认搜索字段
        if not search_fields:
            search_fields = ["subject", "from_addr", "to_addrs"]

        results = []

        try:
            # 搜索已接收邮件
            if include_received:
                query_parts = []
                params = []

                # 添加搜索条件
                for field in search_fields:
                    if field in ["subject", "from_addr", "to_addrs"]:
                        query_parts.append(f"{field} LIKE ?")
                        params.append(f"%{query}%")

                if query_parts:
                    sql_query = f"""
                        SELECT *, 'received' as type FROM emails
                        WHERE ({' OR '.join(query_parts)})
                    """

                    # 添加删除和垃圾邮件过滤
                    if not include_deleted:
                        sql_query += " AND is_deleted = 0"
                    if not include_spam:
                        sql_query += " AND is_spam = 0"

                    # 添加排序和限制
                    sql_query += " ORDER BY date DESC LIMIT ?"
                    params.append(limit)

                    # 执行查询
                    received_results = self.db.execute_query(
                        sql_query, tuple(params), fetch_all=True
                    )
                    results.extend(received_results)

            # 搜索已发送邮件
            if include_sent:
                query_parts = []
                params = []

                # 添加搜索条件
                for field in search_fields:
                    if field in ["subject", "from_addr", "to_addrs"]:
                        query_parts.append(f"{field} LIKE ?")
                        params.append(f"%{query}%")

                if query_parts:
                    sql_query = f"""
                        SELECT *, 'sent' as type FROM sent_emails
                        WHERE ({' OR '.join(query_parts)})
                    """

                    # 添加排序和限制
                    sql_query += " ORDER BY date DESC LIMIT ?"
                    params.append(limit)

                    # 执行查询
                    sent_results = self.db.execute_query(
                        sql_query, tuple(params), fetch_all=True
                    )
                    results.extend(sent_results)

            # 按日期排序并限制结果数量
            results.sort(key=lambda x: x.get("date", ""), reverse=True)
            if len(results) > limit:
                results = results[:limit]

            return results
        except Exception as e:
            logger.error(f"搜索邮件时出错: {e}")
            return []

    def update_sent_email_status(self, message_id: str, **status_updates) -> bool:
        """
        更新已发送邮件状态

        Args:
            message_id: 邮件ID
            **status_updates: 状态更新字典（is_read等）

        Returns:
            bool: 操作是否成功
        """
        try:
            # 过滤有效的状态字段
            valid_fields = {"is_read", "status"}
            data = {}

            for key, value in status_updates.items():
                if key in valid_fields:
                    if key == "is_read":
                        data[key] = 1 if value else 0
                    else:
                        data[key] = value

            if not data:
                logger.warning("没有有效的状态更新字段")
                return False

            success = self.db.execute_update(
                "sent_emails", data, "message_id = ?", (message_id,)
            )

            if success:
                logger.info(f"已更新已发送邮件状态: {message_id}")

            return success
        except Exception as e:
            logger.error(f"更新已发送邮件状态时出错: {e}")
            return False
