"""
新的数据库处理器 - 重构版本，使用模块化设计
提供统一简洁的API，解决原有代码的复杂性问题
集成数据库连接池以提高并发性能
"""

import os
import datetime
import json
from typing import List, Dict, Optional, Any, Union

from common.utils import setup_logging
from common.config import DB_PATH, EMAIL_STORAGE_DIR
from common.email_validator import EmailValidator
from .db_connection import DatabaseConnection
from .db_connection_pool import get_connection_pool
from .email_repository import EmailRepository
from .email_content_manager import EmailContentManager
from .db_models import EmailRecord, SentEmailRecord
from spam_filter.spam_filter import KeywordSpamFilter

# 设置日志
logger = setup_logging("new_db_handler")


class EmailService:
    """
    邮件服务类 - 重构版本的数据库处理器

    提供简洁统一的API，内部使用模块化组件
    解决原有DatabaseHandler的复杂性和易错性问题
    集成连接池以提高并发性能
    """

    def __init__(
        self, db_path: str = DB_PATH, use_connection_pool: bool = True
    ) -> None:
        """
        初始化邮件服务

        Args:
            db_path: 数据库文件路径
            use_connection_pool: 是否使用连接池
        """
        self.db_path = db_path
        self.use_connection_pool = use_connection_pool

        # 初始化连接池或单连接
        if use_connection_pool:
            self.connection_pool = get_connection_pool(db_path)
            # 为了兼容性，也创建一个DatabaseConnection实例
            self.db_connection = DatabaseConnection(db_path)
        else:
            self.connection_pool = None
            self.db_connection = DatabaseConnection(db_path)

        # 初始化组件
        self.email_repo = EmailRepository(self.db_connection)
        self.content_manager = EmailContentManager()
        self.spam_filter = KeywordSpamFilter()
        self.email_validator = EmailValidator()

        # 初始化数据库
        self.db_connection.init_database()

        logger.info(
            f"邮件服务已初始化: {db_path}, 连接池: {'启用' if use_connection_pool else '禁用'}"
        )

    def _execute_with_pool(self, operation_func, *args, **kwargs):
        """
        使用连接池执行数据库操作

        Args:
            operation_func: 要执行的操作函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            操作结果
        """
        if self.use_connection_pool and self.connection_pool:
            try:
                return operation_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"使用连接池执行操作时出错: {e}")
                # 回退到普通连接
                return operation_func(*args, **kwargs)
        else:
            return operation_func(*args, **kwargs)

    def get_pool_status(self) -> Optional[Dict[str, Any]]:
        """
        获取连接池状态

        Returns:
            连接池状态信息，如果未使用连接池则返回None
        """
        if self.use_connection_pool and self.connection_pool:
            return self.connection_pool.get_pool_status()
        return None

    def optimize_database(self) -> bool:
        """
        优化数据库性能

        Returns:
            bool: 操作是否成功
        """
        try:
            if self.use_connection_pool and self.connection_pool:
                # 使用连接池执行优化
                self.connection_pool.execute_script(
                    """
                    PRAGMA optimize;
                    PRAGMA wal_checkpoint(TRUNCATE);
                """
                )
            else:
                # 使用普通连接执行优化
                self.db_connection.execute_script(
                    """
                    PRAGMA optimize;
                    PRAGMA wal_checkpoint(TRUNCATE);
                """
                )

            logger.info("数据库优化完成")
            return True
        except Exception as e:
            logger.error(f"数据库优化失败: {e}")
            return False

    # ==================== 邮件基本操作 ====================

    def save_email(
        self,
        message_id: str,
        from_addr: str,
        to_addrs: Union[List[str], str],
        subject: str = "",
        content: str = "",  # 这是纯文本内容，用于分析
        date: Optional[datetime.datetime] = None,
        full_content_for_storage: Optional[
            str
        ] = None,  # 这是完整的.eml格式内容，用于存储
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
            full_content_for_storage: 完整的.eml格式内容，用于存储
            **kwargs: 其他选项（is_spam, spam_score等）

        Returns:
            bool: 操作是否成功
        """
        try:
            # 如果没有提供完整的存储内容，则使用纯文本内容
            if full_content_for_storage is None:
                full_content_for_storage = content

            # 准备邮件数据进行验证
            email_data = {
                "message_id": message_id,
                "from_addr": from_addr,
                "to_addrs": to_addrs,
                "subject": subject,
                "date": (
                    date.isoformat() if date else datetime.datetime.now().isoformat()
                ),
                "content": full_content_for_storage,  # 验证完整内容
            }

            # 验证邮件数据
            validation_result = self.email_validator.validate_email_data(email_data)

            if not validation_result["is_valid"]:
                logger.error(f"邮件数据验证失败: {validation_result['errors']}")
                return False

            if validation_result["warnings"]:
                logger.warning(f"邮件数据警告: {validation_result['warnings']}")

            # 清理和标准化邮件数据
            sanitized_data = self.email_validator.sanitize_email_data(email_data)

            # 使用清理后的数据
            message_id = sanitized_data["message_id"]
            from_addr = sanitized_data["from_addr"]
            to_addrs = sanitized_data["to_addrs"]
            subject = sanitized_data["subject"]
            date = datetime.datetime.fromisoformat(sanitized_data["date"])

            # 标准化收件人地址
            if isinstance(to_addrs, str):
                to_addrs = [to_addrs]

            # 🔙 检查邮件是否已被撤回
            # 在保存到收件箱之前，检查该邮件是否在已发送邮件中被标记为撤回
            # 由于邮件服务器可能重新生成Message ID，我们需要多种方式匹配
            try:
                # 方法1：直接通过Message ID匹配
                sent_email = self.email_repo.get_sent_email_by_id(message_id)
                if sent_email and sent_email.is_recalled:
                    logger.info(
                        f"邮件已被撤回(Message ID匹配)，跳过保存到收件箱: {message_id}"
                    )
                    return True  # 返回成功，但实际上不保存撤回的邮件

                # 方法2：通过主题+发件人+时间范围匹配（用于Message ID不一致的情况）
                # 查找最近发送的同主题同发件人的已撤回邮件
                try:
                    # 查找24小时内的已撤回邮件
                    time_limit = datetime.datetime.now() - datetime.timedelta(hours=24)

                    # 查询已撤回的已发送邮件
                    recent_recalled_emails = self.email_repo.list_sent_emails(
                        from_addr=from_addr, include_recalled=True, limit=50
                    )

                    for recalled_email in recent_recalled_emails:
                        if (
                            recalled_email.is_recalled
                            and recalled_email.subject == subject
                            and recalled_email.from_addr == from_addr
                            and recalled_email.date >= time_limit
                        ):
                            logger.info(
                                f"邮件已被撤回(主题+发件人匹配)，跳过保存到收件箱: 主题={subject}, 发件人={from_addr}"
                            )
                            return True  # 返回成功，但实际上不保存撤回的邮件

                except Exception as match_error:
                    logger.warning(f"主题匹配检查失败: {match_error}")

            except Exception as e:
                logger.warning(f"检查邮件撤回状态失败，继续保存: {e}")

            # 在保存前进行垃圾邮件检测，使用纯文本content进行分析
            spam_result = self.spam_filter.analyze_email(
                {"from_addr": from_addr, "subject": subject, "content": content}
            )

            # 保存邮件内容（如果提供）
            content_path = None
            if full_content_for_storage:
                # 传递元数据给内容管理器，确保正确的头部格式
                metadata = {
                    "message_id": message_id,
                    "from_addr": from_addr,
                    "to_addrs": to_addrs,
                    "subject": subject,
                    "date": date.isoformat(),
                }
                content_path = self.content_manager.save_content(
                    message_id, full_content_for_storage, metadata
                )

            # 创建邮件记录，直接使用spam_result的结果
            email_record = EmailRecord(
                message_id=message_id,
                from_addr=from_addr,
                to_addrs=to_addrs,
                subject=subject,
                date=date,
                size=len(full_content_for_storage) if full_content_for_storage else 0,
                is_spam=spam_result["is_spam"],
                spam_score=spam_result["score"],
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
                full_eml_content = self.content_manager.get_content(
                    message_id, email_dict
                )
                if full_eml_content:
                    try:
                        from common.email_format_handler import EmailFormatHandler

                        # 解析邮件内容，提取纯文本或HTML正文
                        parsed_email_obj = EmailFormatHandler.parse_mime_message(
                            full_eml_content
                        )
                        # 优先使用 html_content，其次 text_content
                        email_dict["content"] = (
                            parsed_email_obj.html_content
                            or parsed_email_obj.text_content
                            or ""
                        )

                        # 添加附件信息
                        if parsed_email_obj.attachments:
                            email_dict["has_attachments"] = True
                            email_dict["attachments"] = []
                            for attachment in parsed_email_obj.attachments:
                                # 计算附件大小
                                attachment_size = 0
                                if (
                                    hasattr(attachment, "content")
                                    and attachment.content
                                ):
                                    attachment_size = len(attachment.content)
                                elif hasattr(attachment, "size") and attachment.size:
                                    attachment_size = attachment.size

                                email_dict["attachments"].append(
                                    {
                                        "filename": attachment.filename,
                                        "content_type": attachment.content_type,
                                        "size": attachment_size,
                                    }
                                )
                        else:
                            email_dict["has_attachments"] = False
                            email_dict["attachments"] = []

                    except Exception as e:
                        logger.error(f"解析接收邮件内容失败 for {message_id}: {e}")
                        # 解析失败时尝试简单提取文本内容
                        try:
                            import email

                            msg = email.message_from_string(full_eml_content)

                            # 尝试提取纯文本内容
                            simple_content = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        payload = part.get_payload(decode=True)
                                        if payload:
                                            simple_content = payload.decode(
                                                part.get_content_charset() or "utf-8",
                                                errors="ignore",
                                            )
                                            break
                            else:
                                if msg.get_content_type() == "text/plain":
                                    payload = msg.get_payload(decode=True)
                                    if payload:
                                        simple_content = payload.decode(
                                            msg.get_content_charset() or "utf-8",
                                            errors="ignore",
                                        )

                            email_dict["content"] = simple_content or "邮件内容解析失败"

                        except Exception as simple_e:
                            logger.error(f"简单解析也失败 for {message_id}: {simple_e}")
                            email_dict["content"] = "邮件内容解析失败，请联系管理员"

                        email_dict["has_attachments"] = False
                        email_dict["attachments"] = []
                else:
                    email_dict["content"] = ""
                    email_dict["has_attachments"] = False
                    email_dict["attachments"] = []

            return email_dict
        except Exception as e:
            logger.error(f"获取邮件时出错: {e}")
            return None

    def list_emails(
        self,
        user_email: Optional[str] = None,
        include_deleted: bool = False,
        include_spam: bool = True,
        include_recalled: bool = False,  # 新增参数
        is_spam: Optional[bool] = None,  # 新增过滤参数
        limit: int = 500,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        获取邮件列表（统一接口）

        Args:
            user_email: 用户邮箱过滤
            include_deleted: 是否包含已删除邮件
            include_spam: 是否包含垃圾邮件
            include_recalled: 是否包含已撤回邮件
            is_spam: 垃圾邮件过滤参数
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
                include_recalled=include_recalled,  # 传递参数
                is_spam=is_spam,
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
            # 初始化success变量
            success = False

            # 检查邮件是否存在于接收邮件表
            received_email = self.email_repo.get_email_by_id(message_id)

            if received_email:
                # 邮件在接收邮件表中，更新接收邮件状态
                success = self.email_repo.update_email_status(message_id, **updates)
                logger.debug(f"更新接收邮件状态: {message_id}, 结果: {success}")
            else:
                # 邮件不在接收邮件表中，尝试更新已发送邮件
                # 对于已发送邮件，只支持部分字段更新
                sent_updates = {}
                if "is_read" in updates:
                    sent_updates["is_read"] = updates["is_read"]
                if "status" in updates:
                    sent_updates["status"] = updates["status"]

                if sent_updates:
                    success = self.email_repo.update_sent_email_status(
                        message_id, **sent_updates
                    )
                    logger.debug(f"更新已发送邮件状态: {message_id}, 结果: {success}")
                else:
                    # 特殊处理：如果是标记删除操作，对于不存在的邮件我们认为操作成功
                    # 因为邮件可能只是从POP3服务器获取但没有保存到数据库
                    if "is_deleted" in updates and updates["is_deleted"]:
                        logger.info(
                            f"邮件 {message_id} 不在数据库中，标记删除操作视为成功"
                        )
                        success = True
                    else:
                        # 其他情况记录警告
                        logger.warning(
                            f"邮件 {message_id} 不在接收邮件表中，且没有可更新的已发送邮件字段"
                        )
                        success = False

            return success
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
                # 永久删除：先尝试删除接收邮件，如果失败则尝试删除已发送邮件
                success = self.email_repo.delete_email(message_id)
                if not success:
                    success = self.email_repo.delete_sent_email(message_id)
                # 如果都没有找到，对于永久删除我们也认为成功
                if not success:
                    logger.info(f"邮件 {message_id} 不在数据库中，永久删除操作视为成功")
                    success = True
                return success
            else:
                # 标记删除：使用 update_email 方法（已经处理了不存在的情况）
                return self.update_email(message_id, is_deleted=True)
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
        保存已发送邮件（统一接口）

        Args:
            message_id: 邮件ID
            from_addr: 发件人地址
            to_addrs: 收件人地址
            subject: 邮件主题
            content: 邮件内容
            date: 发送日期
            cc_addrs: 抄送地址
            bcc_addrs: 密送地址
            **kwargs: 其他选项

        Returns:
            bool: 操作是否成功
        """
        try:
            # 准备邮件数据进行验证
            email_data = {
                "message_id": message_id,
                "from_addr": from_addr,
                "to_addrs": to_addrs,
                "subject": subject,
                "date": (
                    date.isoformat() if date else datetime.datetime.now().isoformat()
                ),
                "content": content,
            }

            # 验证邮件数据
            validation_result = self.email_validator.validate_email_data(email_data)

            if not validation_result["is_valid"]:
                logger.error(f"已发送邮件数据验证失败: {validation_result['errors']}")
                return False

            if validation_result["warnings"]:
                logger.warning(f"已发送邮件数据警告: {validation_result['warnings']}")

            # 清理和标准化邮件数据
            sanitized_data = self.email_validator.sanitize_email_data(email_data)

            # 使用清理后的数据
            message_id = sanitized_data["message_id"]
            from_addr = sanitized_data["from_addr"]
            to_addrs = sanitized_data["to_addrs"]
            subject = sanitized_data["subject"]
            date = datetime.datetime.fromisoformat(sanitized_data["date"])

            # 标准化地址列表
            if isinstance(to_addrs, str):
                to_addrs = [to_addrs]
            if cc_addrs and isinstance(cc_addrs, str):
                cc_addrs = [cc_addrs]
            if bcc_addrs and isinstance(bcc_addrs, str):
                bcc_addrs = [bcc_addrs]

            # 保存邮件内容（如果提供）
            content_path = None
            if content:
                # 传递元数据给内容管理器，确保正确的头部格式
                metadata = {
                    "message_id": message_id,
                    "from_addr": from_addr,
                    "to_addrs": to_addrs,
                    "subject": subject,
                    "date": date.isoformat(),
                    "cc_addrs": cc_addrs,
                    "bcc_addrs": bcc_addrs,
                }
                content_path = self.content_manager.save_content(
                    message_id, content, metadata
                )

            # 创建已发送邮件记录
            sent_email_record = SentEmailRecord(
                message_id=message_id,
                from_addr=from_addr,
                to_addrs=to_addrs,
                cc_addrs=cc_addrs or [],
                bcc_addrs=bcc_addrs or [],
                subject=subject,
                date=date,
                size=len(content) if content else 0,
                has_attachments=kwargs.get("has_attachments", False),
                content_path=content_path,
                status=kwargs.get("status", "sent"),
                is_read=kwargs.get("is_read", True),
                is_spam=kwargs.get("is_spam", False),
                spam_score=kwargs.get("spam_score", 0.0),
            )

            # 保存到数据库
            logger.debug(f"准备保存已发送邮件记录: {sent_email_record.to_dict()}")
            success = self.email_repo.create_sent_email(sent_email_record)
            logger.debug(f"数据库保存结果: {success}")

            if success:
                logger.info(f"已发送邮件保存成功: {message_id}")
            else:
                logger.error(f"已发送邮件数据库保存失败: {message_id}")

            return success
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
                full_eml_content = self.content_manager.get_content(
                    message_id, sent_dict
                )
                if full_eml_content:
                    try:
                        from common.email_format_handler import EmailFormatHandler

                        parsed_email_obj = EmailFormatHandler.parse_mime_message(
                            full_eml_content
                        )
                        # 优先使用 html_content，其次 text_content
                        sent_dict["content"] = (
                            parsed_email_obj.html_content
                            or parsed_email_obj.text_content
                            or ""
                        )
                    except Exception as e:
                        logger.error(f"解析已发送邮件内容失败 for {message_id}: {e}")
                        # 解析失败时尝试简单提取文本内容
                        try:
                            import email

                            msg = email.message_from_string(full_eml_content)

                            # 尝试提取纯文本内容
                            simple_content = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        payload = part.get_payload(decode=True)
                                        if payload:
                                            simple_content = payload.decode(
                                                part.get_content_charset() or "utf-8",
                                                errors="ignore",
                                            )
                                            break
                            else:
                                if msg.get_content_type() == "text/plain":
                                    payload = msg.get_payload(decode=True)
                                    if payload:
                                        simple_content = payload.decode(
                                            msg.get_content_charset() or "utf-8",
                                            errors="ignore",
                                        )

                            sent_dict["content"] = simple_content or "邮件内容解析失败"

                        except Exception as simple_e:
                            logger.error(f"简单解析也失败 for {message_id}: {simple_e}")
                            sent_dict["content"] = "邮件内容解析失败，请联系管理员"
                else:
                    sent_dict["content"] = ""
            else:
                sent_dict["content"] = ""  # 确保即使不include_content也有这个key

            return sent_dict
        except Exception as e:
            logger.error(f"获取已发送邮件时出错: {e}")
            return None

    def list_sent_emails(
        self,
        from_addr: Optional[str] = None,
        include_spam: bool = True,
        is_spam: Optional[bool] = None,
        include_recalled: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        获取已发送邮件列表

        Args:
            from_addr: 发件人地址过滤
            include_spam: 是否包含垃圾邮件
            is_spam: 垃圾邮件过滤（None=全部，True=仅垃圾邮件，False=仅正常邮件）
            include_recalled: 是否包含已撤回邮件
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            已发送邮件字典列表
        """
        try:
            sent_records = self.email_repo.list_sent_emails(
                from_addr=from_addr,
                include_spam=include_spam,
                is_spam=is_spam,
                include_recalled=include_recalled,
                limit=limit,
                offset=offset,
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
        """获取邮件内容（兼容性方法）- 学习CLI的做法，直接返回原始邮件内容"""
        try:
            # 方法1: 直接从文件读取（学习CLI的简单直接方式）
            safe_id = message_id.strip().strip("<>").replace("@", "_at_")
            import re

            safe_id = re.sub(r'[\\/*?:"<>|]', "_", safe_id).strip()

            # 尝试多个可能的文件路径
            potential_paths = [
                os.path.join(EMAIL_STORAGE_DIR, f"{safe_id}.eml"),
                os.path.join(EMAIL_STORAGE_DIR, "inbox", f"{safe_id}.eml"),
                os.path.join(EMAIL_STORAGE_DIR, "sent", f"{safe_id}.eml"),
            ]

            for filepath in potential_paths:
                if os.path.exists(filepath):
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    logger.debug(f"直接从文件读取邮件内容: {filepath}")
                    return content

            # 方法2: 如果直接读取失败，尝试在邮件目录中搜索
            try:
                for filename in os.listdir(EMAIL_STORAGE_DIR):
                    if filename.endswith(".eml") and safe_id in filename:
                        filepath = os.path.join(EMAIL_STORAGE_DIR, filename)
                        with open(filepath, "r", encoding="utf-8") as f:
                            content = f.read()
                        logger.debug(f"通过搜索找到邮件文件: {filepath}")
                        return content
            except Exception as e:
                logger.debug(f"搜索邮件文件时出错: {e}")

            # 方法3: 最后才尝试数据库记录（但不进行复杂的格式化处理）
            email_data = self.get_email(message_id)
            if email_data and email_data.get("content_path"):
                try:
                    with open(email_data["content_path"], "r", encoding="utf-8") as f:
                        content = f.read()
                    logger.debug(
                        f"从数据库记录的路径读取: {email_data['content_path']}"
                    )
                    return content
                except Exception as e:
                    logger.warning(
                        f"无法从数据库记录路径读取: {email_data['content_path']}, {e}"
                    )

            logger.warning(f"无法找到邮件内容文件: {message_id}")
            return None

        except Exception as e:
            logger.error(f"获取邮件内容时出错: {e}")
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

    # ==================== 邮件撤回功能 ====================

    def recall_email(self, message_id: str, user_email: str) -> Dict[str, Any]:
        """
        撤回邮件（统一接口）

        Args:
            message_id: 邮件ID
            user_email: 操作用户邮箱

        Returns:
            Dict包含success(bool)、message(str)等信息
        """
        try:
            # 检查是否可以撤回
            permission_check = self.email_repo.can_recall_email(message_id, user_email)

            if not permission_check["can_recall"]:
                return {
                    "success": False,
                    "message": permission_check["reason"],
                    "recalled": False,
                }

            # 执行撤回操作
            success = self.email_repo.recall_email(message_id, user_email)

            if success:
                return {"success": True, "message": "邮件撤回成功", "recalled": True}
            else:
                return {
                    "success": False,
                    "message": "邮件撤回失败，请重试",
                    "recalled": False,
                }

        except Exception as e:
            logger.error(f"撤回邮件时出错: {e}")
            return {
                "success": False,
                "message": f"撤回邮件时出错: {e}",
                "recalled": False,
            }

    def get_recallable_emails(
        self, user_email: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取可撤回的邮件列表

        Args:
            user_email: 用户邮箱
            limit: 返回数量限制

        Returns:
            可撤回的邮件列表
        """
        try:
            # 获取用户的已发送邮件（24小时内，未撤回）
            import datetime

            # 计算24小时前的时间
            time_limit = datetime.datetime.now() - datetime.timedelta(hours=24)

            sent_emails = self.list_sent_emails(from_addr=user_email, limit=limit)

            recallable_emails = []
            for email in sent_emails:
                # 检查是否可以撤回
                permission_check = self.email_repo.can_recall_email(
                    email["message_id"], user_email
                )

                if permission_check["can_recall"]:
                    email["can_recall"] = True
                    email["recall_reason"] = permission_check["reason"]
                    recallable_emails.append(email)

            return recallable_emails

        except Exception as e:
            logger.error(f"获取可撤回邮件列表时出错: {e}")
            return []


# 为了保持向后兼容，创建原名称的别名
DatabaseHandler = EmailService
