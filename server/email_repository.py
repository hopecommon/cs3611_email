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
        include_recalled: bool = False,
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
            include_recalled: 是否包含已撤回的邮件
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
                query += " AND (is_deleted = 0 OR is_deleted IS NULL)"

            # 撤回状态过滤 - 默认隐藏已撤回邮件
            if not include_recalled:
                query += " AND (is_recalled = 0 OR is_recalled IS NULL)"

            # 垃圾邮件过滤
            if not include_spam:
                query += " AND (is_spam = 0 OR is_spam IS NULL)"

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
            valid_fields = {
                "is_read",
                "is_deleted",
                "is_spam",
                "spam_score",
                "is_recalled",
                "recalled_at",
                "recalled_by",
            }
            data = {}

            for key, value in status_updates.items():
                if key in valid_fields:
                    if key in ["is_read", "is_deleted", "is_spam", "is_recalled"]:
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
            data["is_spam"] = 1 if data["is_spam"] else 0

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
        include_recalled: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SentEmailRecord]:
        """
        获取已发送邮件列表

        Args:
            from_addr: 发件人地址
            include_spam: 是否包含垃圾邮件
            is_spam: 垃圾邮件过滤（None=全部，True=仅垃圾邮件，False=仅正常邮件）
            include_recalled: 是否包含已撤回邮件
            limit: 返回的最大数量
            offset: 偏移量

        Returns:
            已发送邮件记录列表
        """
        try:
            # 构建查询
            query = "SELECT * FROM sent_emails WHERE 1=1"
            params = []

            # 发件人过滤 - 支持模糊匹配，以处理"显示名 <邮箱>"格式
            if from_addr:
                logger.debug(f"LIST_SENT_EMAILS: Filtering by from_addr: '{from_addr}'")
                # 同时支持精确匹配和包含匹配
                query += " AND (from_addr = ? OR from_addr LIKE ?)"
                params.extend([from_addr, f"%{from_addr}%"])

            # 垃圾邮件过滤
            if not include_spam:
                query += " AND (is_spam = 0 OR is_spam IS NULL)"
            elif is_spam is not None:
                if is_spam:
                    query += " AND is_spam = 1"
                else:
                    query += " AND (is_spam = 0 OR is_spam IS NULL)"

            # 撤回状态过滤 - 默认隐藏已撤回邮件
            if not include_recalled:
                query += " AND (is_recalled = 0 OR is_recalled IS NULL)"

            # 排序和分页
            query += " ORDER BY date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            # 执行查询
            results = self.db.execute_query(query, tuple(params), fetch_all=True)

            # 转换为SentEmailRecord对象
            sent_email_records = []
            logger.debug(
                f"LIST_SENT_EMAILS: Found {len(results) if results else 0} records from DB for query: {query} with params: {params}"
            )
            if results:
                for result_dict in results:
                    try:
                        logger.debug(
                            f"LIST_SENT_EMAILS: DB row from_addr: '{result_dict.get('from_addr')}', date: '{result_dict.get('date')}'"
                        )
                        sent_email_record = SentEmailRecord.from_dict(result_dict)
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
                        sql_query += " AND (is_deleted = 0 OR is_deleted IS NULL)"
                    if not include_spam:
                        sql_query += " AND (is_spam = 0 OR is_spam IS NULL)"

                    # 添加排序和限制
                    sql_query += " ORDER BY date DESC LIMIT ?"
                    params.append(limit)

                    # 执行查询
                    received_results = self.db.execute_query(
                        sql_query, tuple(params), fetch_all=True
                    )
                    if received_results:
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

                    # 垃圾邮件过滤
                    if not include_spam:
                        sql_query += " AND (is_spam = 0 OR is_spam IS NULL)"

                    # 添加排序和限制
                    sql_query += " ORDER BY date DESC LIMIT ?"
                    params.append(limit)

                    # 执行查询
                    sent_results = self.db.execute_query(
                        sql_query, tuple(params), fetch_all=True
                    )
                    if sent_results:
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
            valid_fields = {
                "is_read",
                "status",
                "is_recalled",
                "recalled_at",
                "recalled_by",
            }
            data = {}

            for key, value in status_updates.items():
                if key in valid_fields:
                    if key in ["is_read", "is_recalled"]:
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

    def recall_email(self, message_id: str, recalled_by: str) -> bool:
        """
        撤回邮件（服务器端操作）

        Args:
            message_id: 邮件ID
            recalled_by: 撤回操作者

        Returns:
            bool: 操作是否成功
        """
        try:
            import datetime

            recalled_at = datetime.datetime.now().isoformat()

            # 同时更新收件箱和已发送邮件的撤回状态
            updates = {
                "is_recalled": 1,
                "recalled_at": recalled_at,
                "recalled_by": recalled_by,
            }

            # 更新收件箱中的邮件（对收件人隐藏）
            emails_success = self.db.execute_update(
                "emails", updates, "message_id = ?", (message_id,)
            )

            # 更新已发送邮件的状态（显示撤回状态）
            sent_emails_success = self.db.execute_update(
                "sent_emails", updates, "message_id = ?", (message_id,)
            )

            # 只要有一个更新成功就算成功（邮件可能只在一个表中）
            success = emails_success or sent_emails_success

            if success:
                logger.info(f"邮件已撤回: {message_id} by {recalled_by}")
            else:
                logger.warning(f"邮件撤回失败，可能邮件不存在: {message_id}")

            return success

        except Exception as e:
            logger.error(f"撤回邮件时出错: {e}")
            return False

    def can_recall_email(self, message_id: str, user_email: str) -> Dict[str, Any]:
        """
        检查邮件是否可以撤回

        Args:
            message_id: 邮件ID
            user_email: 用户邮箱

        Returns:
            Dict包含can_recall(bool)和reason(str)
        """
        try:
            import datetime

            # 首先检查已发送邮件表
            sent_email = self.get_sent_email_by_id(message_id)

            if sent_email:
                # 检查发件人是否匹配
                from_addr = sent_email.from_addr
                if not self._is_user_email_match(from_addr, user_email):
                    return {"can_recall": False, "reason": "只能撤回自己发送的邮件"}

                # 检查是否已经撤回
                if sent_email.is_recalled:
                    return {"can_recall": False, "reason": "邮件已经撤回过了"}

                # 检查邮件发送时间
                now = datetime.datetime.now()
                email_date = sent_email.date
                time_limit = datetime.timedelta(hours=24)
                if now - email_date > time_limit:
                    return {
                        "can_recall": False,
                        "reason": "邮件发送超过24小时，无法撤回",
                    }

                return {"can_recall": True, "reason": "可以撤回"}

            # 如果已发送邮件表中没有，检查收件箱中是否有自己发送给自己的邮件
            try:
                result = self.db.execute_query(
                    "SELECT * FROM emails WHERE message_id = ?",
                    (message_id,),
                    fetch_one=True,
                )

                if result:
                    from_addr = result.get("from_addr", "")

                    # 检查是否是自己发送给自己的邮件
                    if self._is_user_email_match(from_addr, user_email):
                        # 检查是否已经撤回
                        if result.get("is_recalled", 0) == 1:
                            return {"can_recall": False, "reason": "邮件已经撤回过了"}

                        # 检查邮件时间
                        date_str = result.get("date", "")
                        if date_str:
                            try:
                                email_date = datetime.datetime.fromisoformat(date_str)
                                now = datetime.datetime.now()
                                time_limit = datetime.timedelta(hours=24)
                                if now - email_date > time_limit:
                                    return {
                                        "can_recall": False,
                                        "reason": "邮件发送超过24小时，无法撤回",
                                    }
                            except:
                                pass  # 如果日期解析失败，继续允许撤回

                        return {"can_recall": True, "reason": "可以撤回"}
                    else:
                        return {"can_recall": False, "reason": "只能撤回自己发送的邮件"}

            except Exception as e:
                logger.error(f"查询收件箱邮件时出错: {e}")

            return {"can_recall": False, "reason": "邮件不存在或不是您发送的邮件"}

        except Exception as e:
            logger.error(f"检查邮件撤回权限时出错: {e}")
            return {"can_recall": False, "reason": f"检查失败: {e}"}

    def _is_user_email_match(self, email_field, user_email):
        """检查邮件地址字段是否匹配用户邮箱"""
        if not email_field or not user_email:
            return False

        # 转换为字符串进行比较
        email_str = str(email_field).lower()
        user_email_lower = user_email.lower()

        # 支持多种格式：
        # 1. 直接匹配: user@domain.com
        # 2. 显示名格式: Name <user@domain.com>
        # 3. JSON格式中的部分匹配
        return (
            user_email_lower in email_str
            or email_str == user_email_lower
            or f"<{user_email_lower}>" in email_str
        )
