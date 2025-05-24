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
        获取指定邮件

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

                # 使用增强的邮件解析逻辑
                try:
                    # 首先尝试使用统一格式处理器
                    email_obj = EmailFormatHandler.parse_email_content(
                        msg_content.decode("utf-8", errors="ignore")
                    )

                    # 验证解析结果的完整性
                    if self._is_parsing_incomplete(email_obj):
                        logger.warning(f"邮件 {msg_num} 解析不完整，尝试备用解析方法")
                        # 使用备用解析方法
                        email_obj = self._enhanced_email_parsing(msg_content, msg_num)

                except Exception as parse_e:
                    logger.error(f"标准解析失败: {parse_e}")
                    # 使用备用解析方法
                    email_obj = self._enhanced_email_parsing(msg_content, msg_num)

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

    def _is_parsing_incomplete(self, email_obj: Email) -> bool:
        """
        检查邮件解析是否不完整

        Args:
            email_obj: 解析后的Email对象

        Returns:
            如果解析不完整返回True
        """
        # 检查关键字段是否缺失或为默认值
        if not email_obj.subject or email_obj.subject == "(无主题)":
            return True
        if (
            not email_obj.from_addr
            or email_obj.from_addr.address == "unknown@localhost"
        ):
            return True
        if not email_obj.to_addrs:
            return True
        if not email_obj.date:
            return True
        return False

    def _enhanced_email_parsing(self, msg_content: bytes, msg_num: int) -> Email:
        """
        增强的邮件解析方法，处理各种格式问题

        Args:
            msg_content: 邮件原始内容
            msg_num: 邮件编号

        Returns:
            解析后的Email对象
        """
        from email.parser import BytesParser
        from email import policy
        from common.models import Email, EmailAddress
        from common.email_header_processor import EmailHeaderProcessor
        from common.email_content_processor import EmailContentProcessor
        import datetime

        try:
            # 首先尝试修复邮件格式
            fixed_content = self._fix_email_format(msg_content)

            # 使用BytesParser直接解析
            parser = BytesParser(policy=policy.default)
            msg = parser.parsebytes(fixed_content)

            # 手动提取头部信息
            message_id = msg.get("Message-ID", "").strip("<>")

            # 增强的主题解析
            subject = msg.get("Subject", "")
            logger.debug(f"原始Subject: {subject}")
            if subject:
                subject = EmailHeaderProcessor.decode_header_value(subject)
                logger.debug(f"解码后Subject: {subject}")
            if not subject:
                subject = f"邮件 {msg_num}"
                logger.debug(f"使用默认Subject: {subject}")

            # 增强的发件人解析
            from_str = msg.get("From", "")
            logger.debug(f"原始From: {from_str}")
            if from_str:
                from_addr = EmailHeaderProcessor.parse_address(from_str)
                logger.debug(f"解析后From: {from_addr.name} <{from_addr.address}>")
            else:
                from_addr = EmailAddress("", "unknown@localhost")
                logger.debug(f"使用默认From: {from_addr.address}")

            # 增强的收件人解析
            to_str = msg.get("To", "")
            if to_str:
                to_addrs = EmailHeaderProcessor.parse_address_list(to_str)
            else:
                to_addrs = [EmailAddress("", "unknown@localhost")]

            # 抄送解析
            cc_str = msg.get("Cc", "")
            cc_addrs = EmailHeaderProcessor.parse_address_list(cc_str) if cc_str else []

            # 密送解析
            bcc_str = msg.get("Bcc", "")
            bcc_addrs = (
                EmailHeaderProcessor.parse_address_list(bcc_str) if bcc_str else []
            )

            # 日期解析
            date_str = msg.get("Date", "")
            if date_str:
                date = EmailHeaderProcessor.parse_date(date_str)
            else:
                date = datetime.datetime.now()

            # 内容解析
            text_content, html_content, attachments = (
                EmailContentProcessor.extract_content_and_attachments(msg)
            )

            # 如果内容为空，尝试从Base64编码中提取
            if not text_content and not html_content:
                text_content = self._extract_base64_content(msg_content)

            # 创建Email对象
            email_obj = Email(
                message_id=message_id,
                subject=subject,
                from_addr=from_addr,
                to_addrs=to_addrs,
                cc_addrs=cc_addrs,
                bcc_addrs=bcc_addrs,
                date=date,
                text_content=text_content,
                html_content=html_content,
                attachments=attachments,
            )

            logger.info(f"增强解析成功: {subject}")
            return email_obj

        except Exception as e:
            logger.error(f"增强解析也失败: {e}")
            # 返回一个基本的Email对象
            return Email(
                message_id=f"msg_{msg_num}",
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

    def _fix_email_format(self, msg_content: bytes) -> bytes:
        """
        修复邮件格式问题
        主要解决头部之间有空行的问题

        Args:
            msg_content: 原始邮件内容

        Returns:
            修复后的邮件内容
        """
        try:
            content_str = msg_content.decode("utf-8", errors="ignore")
            lines = content_str.split("\n")

            fixed_lines = []
            header_lines = []
            body_lines = []
            in_headers = True

            for line in lines:
                line = line.rstrip("\r")  # 移除回车符

                if in_headers:
                    # 检查是否是头部行
                    if line.strip() == "":
                        # 空行，可能是头部结束或头部中间的空行
                        # 如果已经有头部行，这可能是头部结束
                        if header_lines:
                            # 检查下一行是否是MIME边界或其他正文内容
                            continue  # 暂时跳过空行，稍后决定是否是头部结束
                    elif line.startswith("--"):
                        # 这是MIME边界，头部结束
                        in_headers = False
                        body_lines.append(line)
                    elif (
                        ":" in line
                        and not line.startswith(" ")
                        and not line.startswith("\t")
                    ):
                        # 这是一个新的头部字段
                        header_lines.append(line)
                    elif line.startswith(" ") or line.startswith("\t"):
                        # 这是头部字段的续行
                        if header_lines:
                            header_lines[-1] += " " + line.strip()
                    else:
                        # 其他情况，可能是正文开始
                        in_headers = False
                        body_lines.append(line)
                else:
                    # 正文部分，直接添加
                    body_lines.append(line)

            # 组装修复后的邮件
            fixed_lines.extend(header_lines)
            if header_lines and body_lines:
                fixed_lines.append("")  # 添加头部和正文之间的分隔空行
            fixed_lines.extend(body_lines)

            fixed_content = "\n".join(fixed_lines)
            logger.debug(
                f"邮件格式修复完成，原始行数: {len(lines)}, 修复后行数: {len(fixed_lines)}"
            )
            logger.debug(f"头部行数: {len(header_lines)}, 正文行数: {len(body_lines)}")

            return fixed_content.encode("utf-8")

        except Exception as e:
            logger.error(f"邮件格式修复失败: {e}")
            return msg_content

    def _extract_base64_content(self, msg_content: bytes) -> str:
        """
        从邮件内容中提取Base64编码的文本

        Args:
            msg_content: 邮件原始内容

        Returns:
            解码后的文本内容
        """
        import base64
        import re

        try:
            # 将字节转换为字符串
            content_str = msg_content.decode("utf-8", errors="ignore")

            # 查找Base64编码的内容
            base64_pattern = r"([A-Za-z0-9+/]{20,}={0,2})"
            matches = re.findall(base64_pattern, content_str)

            decoded_texts = []
            for match in matches:
                try:
                    # 尝试解码Base64
                    decoded_bytes = base64.b64decode(match + "==")  # 添加填充
                    decoded_text = decoded_bytes.decode("utf-8", errors="ignore")

                    # 检查是否是有意义的文本（包含中文或英文）
                    if len(decoded_text) > 3 and any(
                        ord(c) > 127 or c.isalpha() for c in decoded_text
                    ):
                        decoded_texts.append(decoded_text)
                        logger.info(f"成功解码Base64内容: {decoded_text[:50]}...")

                except Exception:
                    continue

            return "\n".join(decoded_texts) if decoded_texts else ""

        except Exception as e:
            logger.error(f"提取Base64内容失败: {e}")
            return ""

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
        获取所有邮件，支持多种过滤选项

        Args:
            delete: 获取后是否删除
            limit: 最多获取的邮件数量
            since_date: 只获取该日期之后的邮件
            only_unread: 是否只获取未读邮件
            from_addr: 只获取来自特定发件人的邮件
            subject_contains: 只获取主题包含特定字符串的邮件

        Returns:
            Email对象列表
        """
        emails = []
        connection_retry_count = 0
        max_connection_retries = 3
        processed_msgs = set()  # 记录已处理的邮件编号

        while connection_retry_count < max_connection_retries:
            try:
                # 确保连接
                connection = self.connection_manager.get_connection()

                # 获取邮件列表
                email_list = self.list_emails()

                # 如果设置了limit，只获取指定数量的邮件
                if limit:
                    email_list = email_list[-limit:]  # 获取最新的邮件

                logger.info(f"准备获取 {len(email_list)} 封邮件")

                for msg_num, msg_size in email_list:
                    # 跳过已处理的邮件
                    if msg_num in processed_msgs:
                        continue

                    try:
                        email_obj = self.retrieve_email(msg_num, delete)
                        if email_obj:
                            # 应用过滤条件
                            if self._should_include_email(
                                email_obj, since_date, from_addr, subject_contains
                            ):
                                emails.append(email_obj)
                                logger.debug(f"已添加邮件: {email_obj.subject}")

                        processed_msgs.add(msg_num)

                    except Exception as e:
                        logger.warning(f"获取邮件 {msg_num} 时出错: {e}")
                        # 继续处理下一封邮件
                        continue

                # 成功获取邮件，跳出重试循环
                break

            except Exception as e:
                connection_retry_count += 1
                logger.warning(
                    f"获取邮件列表失败 (尝试 {connection_retry_count}/{max_connection_retries}): {e}"
                )

                if connection_retry_count < max_connection_retries:
                    # 重新连接
                    try:
                        self.connection_manager.disconnect()
                        time.sleep(2)
                        self.connection_manager.connect()
                    except Exception as conn_err:
                        logger.error(f"重新连接失败: {conn_err}")
                        time.sleep(5)
                else:
                    logger.error("已达到最大连接重试次数，停止获取邮件")
                    break

        logger.info(f"共获取了 {len(emails)} 封邮件")
        return emails

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
            subject_contains: 主题过滤

        Returns:
            是否包含该邮件
        """
        # 日期过滤
        if since_date and email_obj.date and email_obj.date < since_date:
            return False

        # 发件人过滤
        if from_addr and email_obj.from_addr:
            if from_addr.lower() not in email_obj.from_addr.address.lower():
                return False

        # 主题过滤
        if subject_contains and email_obj.subject:
            if subject_contains.lower() not in email_obj.subject.lower():
                return False

        return True
