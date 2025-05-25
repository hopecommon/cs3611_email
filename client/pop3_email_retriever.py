# -*- coding: utf-8 -*-
"""
POP3邮件检索器
负责从POP3服务器检索邮件内容
"""

import poplib
import ssl
import socket
import time
from email import policy
from email.parser import BytesParser
from typing import List, Tuple, Optional
import datetime

from common.utils import setup_logging
from common.models import Email
from common.email_format_handler import EmailFormatHandler

# 设置日志
logger = setup_logging("pop3_email_retriever")


class POP3EmailRetriever:
    """POP3邮件检索器"""

    def __init__(self, connection_manager):
        """
        初始化邮件检索器

        Args:
            connection_manager: POP3连接管理器实例
        """
        self.connection_manager = connection_manager

    def get_mailbox_status(self) -> Tuple[int, int]:
        """
        获取邮箱状态

        Returns:
            (邮件数量, 邮箱大小(字节))元组
        """
        connection = self.connection_manager.get_connection()

        try:
            status = connection.stat()
            logger.info(f"邮箱状态: {status[0]}封邮件, {status[1]}字节")
            return status
        except Exception as e:
            logger.error(f"获取邮箱状态失败: {e}")
            raise

    def list_emails(self) -> List[Tuple[int, int]]:
        """
        列出所有邮件

        Returns:
            [(邮件索引, 邮件大小), ...]列表
        """
        connection = self.connection_manager.get_connection()

        try:
            _, listings, _ = connection.list()  # 忽略响应码
            result = []

            for item in listings:
                parts = item.decode("ascii").split()
                if len(parts) >= 2:
                    msg_num = int(parts[0])
                    msg_size = int(parts[1])
                    result.append((msg_num, msg_size))

            logger.info(f"列出了{len(result)}封邮件")
            return result
        except Exception as e:
            logger.error(f"列出邮件失败: {e}")
            raise

    def retrieve_email(self, msg_num: int, delete: bool = False) -> Optional[Email]:
        """
        获取指定邮件 - 统一使用EmailFormatHandler

        Args:
            msg_num: 邮件索引
            delete: 获取后是否删除

        Returns:
            Email对象，如果获取失败则返回None
        """
        connection = self.connection_manager.get_connection()
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                # 获取邮件内容
                _, lines, _ = connection.retr(msg_num)  # 忽略响应码和字节数

                # 解析邮件
                msg_content = b"\r\n".join(lines)

                # 使用统一的邮件格式处理器解析邮件
                try:
                    # 直接使用EmailFormatHandler进行解析
                    email_obj = EmailFormatHandler.parse_email_content(
                        msg_content.decode("utf-8", errors="ignore")
                    )

                    # 简单验证解析结果
                    if (
                        not email_obj.message_id
                        or email_obj.message_id == "unknown@localhost"
                    ):
                        # 生成一个基于邮件编号的临时ID
                        email_obj.message_id = f"msg_{msg_num}@pop3.localhost"
                        logger.info(
                            f"为邮件 {msg_num} 生成临时Message-ID: {email_obj.message_id}"
                        )

                    # 如果没有主题，使用默认主题
                    if not email_obj.subject or email_obj.subject == "解析失败的邮件":
                        email_obj.subject = f"邮件 {msg_num}"

                except Exception as parse_e:
                    logger.error(f"邮件解析失败: {parse_e}")
                    # 创建一个基本的邮件对象作为回退
                    from common.models import Email, EmailAddress
                    import datetime

                    email_obj = Email(
                        message_id=f"msg_{msg_num}@pop3.localhost",
                        subject=f"邮件 {msg_num}",
                        from_addr=EmailAddress("", "unknown@localhost"),
                        to_addrs=[EmailAddress("", "unknown@localhost")],
                        cc_addrs=[],
                        bcc_addrs=[],
                        date=datetime.datetime.now(),
                        text_content="邮件解析失败",
                        html_content="",
                        attachments=[],
                    )

                # 如果需要，标记邮件为删除
                if delete:
                    connection.dele(msg_num)
                    logger.info(f"邮件已标记为删除: {msg_num}")

                logger.info(f"已获取邮件: {msg_num}")
                return email_obj

            except (socket.timeout, ssl.SSLError, ConnectionError, OSError) as e:
                retry_count += 1
                error_msg = str(e).lower()

                if (
                    "timed out" in error_msg
                    or "cannot read from timed out object" in error_msg
                    or "eof occurred in violation of protocol" in error_msg
                ):
                    logger.warning(
                        f"获取邮件 {msg_num} 连接问题，尝试重新连接 ({retry_count}/{max_retries}): {e}"
                    )
                    # 强制断开连接
                    try:
                        self.connection_manager.connection = None
                    except:
                        pass

                    # 等待后重新连接
                    time.sleep(2)  # 增加等待时间
                    try:
                        self.connection_manager.connect()
                        connection = self.connection_manager.get_connection()
                        logger.info(f"重新连接成功，继续获取邮件 {msg_num}")
                    except Exception as conn_err:
                        logger.error(f"重新连接失败: {conn_err}")
                        time.sleep(3)  # 等待更长时间
                        continue
                else:
                    logger.error(f"获取邮件 {msg_num} 失败: {e}")
                    return None

            except poplib.error_proto as e:
                # 处理POP3协议错误
                logger.error(f"POP3协议错误: {e}")
                if "message content not found" in str(e).lower():
                    # 如果是邮件内容找不到的错误，直接返回None
                    return None

                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"尝试重试 ({retry_count}/{max_retries})")
                    time.sleep(1)
                else:
                    return None

            except Exception as e:
                logger.error(f"获取邮件 {msg_num} 失败: {e}")
                import traceback

                logger.error(f"异常详情: {traceback.format_exc()}")
                return None

        logger.error(f"获取邮件 {msg_num} 失败，已达到最大重试次数")
        return None

    def retrieve_all_emails(
        self,
        delete: bool = False,
        limit: int = None,
        since_date: datetime.datetime = None,
        only_unread: bool = False,
        from_addr: str = None,
        subject_contains: str = None,
    ) -> List[Email]:
        """
        获取所有邮件，支持过滤条件

        Args:
            delete: 获取后是否删除
            limit: 最大获取数量
            since_date: 只获取此日期之后的邮件
            only_unread: 只获取未读邮件
            from_addr: 只获取来自指定发件人的邮件
            subject_contains: 只获取主题包含指定文字的邮件

        Returns:
            邮件列表
        """
        connection = self.connection_manager.get_connection()

        try:
            # 获取邮件列表
            email_list = self.list_emails()
            total_emails = len(email_list)

            logger.info(f"邮箱中共有 {total_emails} 封邮件")

            if limit and limit < total_emails:
                # 如果有限制，从最新的邮件开始
                email_list = email_list[-limit:]
                logger.info(f"根据限制，只获取最新的 {len(email_list)} 封邮件")

            emails = []
            for i, (msg_num, msg_size) in enumerate(email_list, 1):
                try:
                    logger.info(f"正在获取邮件 {i}/{len(email_list)}: 编号 {msg_num}")

                    email_obj = self.retrieve_email(msg_num, delete=False)
                    if email_obj:
                        # 应用过滤条件
                        if self._should_include_email(
                            email_obj, since_date, from_addr, subject_contains
                        ):
                            emails.append(email_obj)

                            # 如果设置了删除，在确认邮件符合条件后删除
                            if delete:
                                connection.dele(msg_num)
                                logger.info(f"邮件 {msg_num} 已标记为删除")
                        else:
                            logger.debug(f"邮件 {msg_num} 不符合过滤条件，跳过")
                    else:
                        logger.warning(f"无法获取邮件 {msg_num}")

                except Exception as e:
                    logger.error(f"获取邮件 {msg_num} 时出错: {e}")
                    continue

            logger.info(f"成功获取了 {len(emails)} 封符合条件的邮件")
            return emails

        except Exception as e:
            logger.error(f"获取所有邮件失败: {e}")
            return []

    def _should_include_email(
        self,
        email_obj: Email,
        since_date: datetime.datetime = None,
        from_addr: str = None,
        subject_contains: str = None,
    ) -> bool:
        """
        检查邮件是否符合过滤条件

        Args:
            email_obj: 邮件对象
            since_date: 日期过滤
            from_addr: 发件人过滤
            subject_contains: 主题关键词过滤

        Returns:
            是否符合条件
        """
        # 日期过滤
        if since_date and email_obj.date:
            if email_obj.date < since_date:
                return False

        # 发件人过滤
        if from_addr and email_obj.from_addr:
            if from_addr.lower() not in email_obj.from_addr.address.lower():
                return False

        # 主题关键词过滤
        if subject_contains and email_obj.subject:
            if subject_contains.lower() not in email_obj.subject.lower():
                return False

        return True
