"""
POP3客户端模块 - 处理邮件接收功能
"""

import os
import poplib
import ssl
import email
import time
import base64
from email import policy
from email.parser import BytesParser
from email.message import EmailMessage
from typing import List, Dict, Optional, Tuple, Any, Literal
import datetime
import re
from pathlib import Path

from common.utils import setup_logging, safe_filename
from common.models import Email, EmailAddress, Attachment, EmailStatus
from common.config import POP3_SERVER, EMAIL_STORAGE_DIR
from client.socket_utils import close_socket_safely, close_ssl_connection_safely

# 设置日志
logger = setup_logging("pop3_client")


class POP3Client:
    """POP3客户端类，处理邮件接收"""

    def __init__(
        self,
        host: str = POP3_SERVER["host"],
        port: int = POP3_SERVER["port"],
        use_ssl: bool = POP3_SERVER["use_ssl"],
        ssl_port: int = POP3_SERVER["ssl_port"],
        username: Optional[str] = None,
        password: Optional[str] = None,
        auth_method: Optional[Literal["BASIC", "APOP", "AUTO"]] = "AUTO",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        初始化POP3客户端

        Args:
            host: POP3服务器主机名
            port: POP3服务器端口
            use_ssl: 是否使用SSL/TLS
            ssl_port: SSL/TLS端口
            username: 认证用户名
            password: 认证密码
            auth_method: 认证方法，可选值为"BASIC"、"APOP"或"AUTO"（自动选择）
            timeout: 连接超时时间（秒）
            max_retries: 最大重试次数
        """
        self.host = host
        self.port = ssl_port if use_ssl else port
        self.use_ssl = use_ssl
        self.username = username
        self.password = password
        self.auth_method = auth_method
        self.timeout = timeout
        self.max_retries = max_retries
        self.connection = None

    def connect(self) -> None:
        """
        连接到POP3服务器

        Raises:
            poplib.error_proto: 连接失败时抛出
        """
        retry_count = 0
        last_exception = None
        temp_connection = None

        while retry_count < self.max_retries:
            try:
                if self.use_ssl:
                    context = ssl.create_default_context()
                    temp_connection = poplib.POP3_SSL(
                        self.host, self.port, timeout=self.timeout, context=context
                    )
                else:
                    temp_connection = poplib.POP3(
                        self.host, self.port, timeout=self.timeout
                    )

                # 如果提供了认证信息，则进行认证
                if self.username and self.password:
                    # 使用临时连接进行认证
                    if self.auth_method == "AUTO" or self.auth_method == "BASIC":
                        # 使用基本认证
                        temp_connection.user(self.username)
                        temp_connection.pass_(self.password)
                        logger.info(f"已使用基本认证: {self.username}")
                    elif self.auth_method == "APOP":
                        # 使用APOP认证（如果服务器支持）
                        if (
                            hasattr(temp_connection, "welcome")
                            and "<"
                            in temp_connection.welcome.decode("utf-8", errors="ignore")
                            and ">"
                            in temp_connection.welcome.decode("utf-8", errors="ignore")
                        ):
                            temp_connection.apop(self.username, self.password)
                            logger.info(f"已使用APOP认证: {self.username}")
                        else:
                            logger.warning("服务器不支持APOP认证，尝试使用基本认证")
                            temp_connection.user(self.username)
                            temp_connection.pass_(self.password)
                            logger.info(f"已使用基本认证: {self.username}")
                    else:
                        # 默认使用基本认证
                        temp_connection.user(self.username)
                        temp_connection.pass_(self.password)
                        logger.info(f"已使用默认认证: {self.username}")

                # 认证成功后，将临时连接赋值给实例变量
                self.connection = temp_connection
                temp_connection = None  # 避免在finally中关闭连接

                logger.info(f"已连接到POP3服务器: {self.host}:{self.port}")
                return
            except (poplib.error_proto, OSError) as e:
                last_exception = e
                retry_count += 1

                # 检查是否是QQ邮箱特定的错误
                error_msg = str(e).lower()
                if "please using authorized code to login" in error_msg:
                    logger.warning(
                        f"QQ邮箱要求使用授权码而非密码登录，请在QQ邮箱设置中获取授权码"
                    )

                logger.warning(
                    f"连接POP3服务器失败 (尝试 {retry_count}/{self.max_retries}): {e}"
                )

                # 确保临时连接被安全关闭
                close_ssl_connection_safely(temp_connection)

                # 如果是认证错误，尝试不同的认证方法
                if "authentication failed" in error_msg and self.auth_method == "AUTO":
                    if retry_count == 1:
                        logger.info(f"尝试切换到BASIC认证方法")
                        self.auth_method = "BASIC"
                    elif retry_count == 2:
                        logger.info(f"尝试切换到APOP认证方法")
                        self.auth_method = "APOP"

                # 短暂等待后重试
                time.sleep(1)
            except Exception as e:
                logger.error(f"连接POP3服务器失败: {e}")
                raise
            finally:
                # 确保临时连接被关闭
                if temp_connection:
                    try:
                        temp_connection.quit()
                    except Exception as e:
                        logger.debug(f"关闭临时连接时出错: {e}")

        # 如果所有重试都失败，抛出最后一个异常
        if last_exception:
            logger.error(f"连接POP3服务器失败，已达到最大重试次数: {last_exception}")
            raise last_exception

    def _authenticate(self) -> None:
        """
        使用指定的认证方法进行认证

        Raises:
            poplib.error_proto: 认证失败时抛出
        """
        try:
            # 检查服务器欢迎信息，判断是否支持APOP
            supports_apop = False
            if hasattr(self.connection, "welcome"):
                welcome = self.connection.welcome.decode("utf-8", errors="ignore")
                # APOP服务器在欢迎信息中包含时间戳，格式通常为 <timestamp@hostname>
                supports_apop = "<" in welcome and ">" in welcome and "@" in welcome
                logger.debug(f"服务器欢迎信息: {welcome}")
                logger.debug(f"服务器是否支持APOP: {supports_apop}")

            if self.auth_method == "AUTO":
                # 自动选择认证方法
                if supports_apop:
                    try:
                        self.connection.apop(self.username, self.password)
                        logger.info(f"已使用APOP认证: {self.username}")
                    except Exception as e:
                        logger.warning(f"APOP认证失败，尝试基本认证: {e}")
                        self.connection.user(self.username)
                        self.connection.pass_(self.password)
                        logger.info(f"已使用基本认证: {self.username}")
                else:
                    self.connection.user(self.username)
                    self.connection.pass_(self.password)
                    logger.info(f"已使用基本认证: {self.username}")
            elif self.auth_method == "APOP":
                # 使用APOP认证（如果服务器支持）
                if supports_apop:
                    self.connection.apop(self.username, self.password)
                    logger.info(f"已使用APOP认证: {self.username}")
                else:
                    logger.warning("服务器不支持APOP认证，尝试使用基本认证")
                    self.connection.user(self.username)
                    self.connection.pass_(self.password)
                    logger.info(f"已使用基本认证: {self.username}")
            elif self.auth_method == "BASIC":
                # 使用基本认证
                self.connection.user(self.username)
                self.connection.pass_(self.password)
                logger.info(f"已使用基本认证: {self.username}")
            else:
                # 默认使用基本认证
                self.connection.user(self.username)
                self.connection.pass_(self.password)
                logger.info(f"已使用默认认证: {self.username}")
        except Exception as e:
            logger.error(f"认证失败 ({self.auth_method}): {e}")
            raise

    def disconnect(self) -> None:
        """断开与POP3服务器的连接"""
        if self.connection:
            # 使用工具函数安全地关闭连接
            if close_ssl_connection_safely(self.connection):
                logger.info("已断开与POP3服务器的连接")
            else:
                logger.warning("断开与POP3服务器的连接可能不完全")

            # 确保连接对象被清除
            self.connection = None

    def get_mailbox_status(self) -> Tuple[int, int]:
        """
        获取邮箱状态

        Returns:
            (邮件数量, 邮箱大小(字节))元组
        """
        if not self.connection:
            self.connect()

        try:
            status = self.connection.stat()
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
        if not self.connection:
            self.connect()

        try:
            _, listings, _ = self.connection.list()  # 忽略响应码
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
        if not self.connection:
            self.connect()

        try:
            # 获取邮件内容
            _, lines, _ = self.connection.retr(msg_num)  # 忽略响应码和字节数

            # 解析邮件
            msg_content = b"\r\n".join(lines)
            parser = BytesParser(policy=policy.default)
            msg = parser.parsebytes(msg_content)

            # 转换为Email对象
            email_obj = self._convert_to_email(msg)

            # 如果需要，标记邮件为删除
            if delete:
                self.connection.dele(msg_num)
                logger.info(f"邮件已标记为删除: {msg_num}")

            logger.info(f"已获取邮件: {msg_num}")
            return email_obj
        except Exception as e:
            logger.error(f"获取邮件失败: {e}")
            return None

    def retrieve_all_emails(
        self,
        delete: bool = False,
        limit: int = None,
        since_date: datetime = None,
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
            only_unread: 是否只获取未读邮件（注意：POP3协议本身不支持邮件状态，此功能依赖本地数据库）
            from_addr: 只获取来自特定发件人的邮件
            subject_contains: 只获取主题包含特定字符串的邮件

        Returns:
            Email对象列表
        """
        emails = []

        try:
            # 获取邮件列表
            email_list = self.list_emails()

            # 如果设置了limit，只获取指定数量的邮件
            if limit and limit < len(email_list):
                email_list = email_list[-limit:]  # 获取最新的limit封邮件

            # 获取每封邮件
            for msg_num, _ in email_list:
                email_obj = self.retrieve_email(msg_num, delete)
                if not email_obj:
                    continue

                # 应用过滤条件
                # 日期过滤
                if since_date and email_obj.date < since_date:
                    continue

                # 发件人过滤
                if (
                    from_addr
                    and from_addr.lower() not in email_obj.from_addr.address.lower()
                ):
                    continue

                # 主题过滤
                if (
                    subject_contains
                    and subject_contains.lower() not in email_obj.subject.lower()
                ):
                    continue

                # 未读状态过滤（需要与本地数据库集成）
                if only_unread:
                    # 这里需要查询数据库判断邮件是否已读
                    # 暂时跳过此过滤条件，后续实现
                    pass

                emails.append(email_obj)

            logger.info(f"已获取{len(emails)}封邮件")
            return emails
        except Exception as e:
            logger.error(f"获取所有邮件失败: {e}")
            return emails

    def save_email_as_eml(
        self, email_obj: Email, directory: str = EMAIL_STORAGE_DIR
    ) -> str:
        """
        将邮件保存为.eml文件

        Args:
            email_obj: Email对象
            directory: 保存目录

        Returns:
            保存的文件路径
        """
        # 确保目录存在
        os.makedirs(directory, exist_ok=True)

        # 生成文件名
        date_str = email_obj.date.strftime("%Y%m%d_%H%M%S")
        subject = safe_filename(email_obj.subject)
        if len(subject) > 50:
            subject = subject[:47] + "..."

        filename = f"{date_str}_{subject}.eml"
        filepath = os.path.join(directory, filename)

        # 创建MIME消息
        from client.smtp_client import SMTPClient

        smtp_client = SMTPClient()
        mime_msg = smtp_client._create_mime_message(email_obj)

        # 保存为.eml文件
        with open(filepath, "wb") as f:
            f.write(mime_msg.as_bytes())

        logger.info(f"邮件已保存为: {filepath}")
        return filepath

    def _convert_to_email(self, msg: EmailMessage) -> Email:
        """
        将EmailMessage转换为Email对象

        Args:
            msg: EmailMessage对象

        Returns:
            Email对象
        """
        # 提取基本信息
        subject = msg.get("Subject", "")

        # 处理发件人
        from_addr = self._parse_address(msg.get("From", ""))

        # 处理收件人
        to_addrs = []
        if msg.get("To"):
            to_field = msg.get("To")
            to_addrs = self._parse_addresses(to_field)

        # 处理抄送
        cc_addrs = []
        if msg.get("Cc"):
            cc_field = msg.get("Cc")
            cc_addrs = self._parse_addresses(cc_field)

        # 获取邮件ID
        message_id = msg.get("Message-ID", "")

        # 获取日期
        date = datetime.datetime.now()
        if msg.get("Date"):
            try:
                date_str = msg.get("Date")
                date = email.utils.parsedate_to_datetime(date_str)
            except:
                pass

        # 获取内容
        text_content = ""
        html_content = ""
        attachments = []

        # 处理邮件内容
        text_content, html_content = self._process_message_parts(
            msg, text_content, html_content, attachments
        )

        # 创建Email对象
        email_obj = Email(
            message_id=message_id,
            subject=subject,
            from_addr=from_addr,
            to_addrs=to_addrs,
            cc_addrs=cc_addrs,
            text_content=text_content,
            html_content=html_content,
            attachments=attachments,
            date=date,
            status=EmailStatus.RECEIVED,
            is_read=False,
        )

        return email_obj

    def _parse_address(self, addr_str: str) -> EmailAddress:
        """
        解析单个邮件地址

        Args:
            addr_str: 地址字符串

        Returns:
            EmailAddress对象
        """
        try:
            name, address = email.utils.parseaddr(addr_str)
            return EmailAddress(name=name, address=address)
        except:
            # 如果解析失败，尝试简单解析
            match = re.search(r"<([^>]+)>", addr_str)
            if match:
                address = match.group(1)
                name = addr_str.split("<")[0].strip()
            else:
                address = addr_str.strip()
                name = ""

            return EmailAddress(name=name, address=address)

    def _parse_addresses(self, addr_str: str) -> List[EmailAddress]:
        """
        解析多个邮件地址

        Args:
            addr_str: 地址字符串

        Returns:
            EmailAddress对象列表
        """
        result = []

        # 分割地址
        for addr in addr_str.split(","):
            if addr.strip():
                result.append(self._parse_address(addr))

        return result

    def _process_message_parts(
        self,
        msg: EmailMessage,
        text_content: str,
        html_content: str,
        attachments: List[Attachment],
    ) -> Tuple[str, str]:
        """
        处理邮件各部分内容

        Args:
            msg: EmailMessage对象
            text_content: 纯文本内容
            html_content: HTML内容
            attachments: 附件列表（引用传递）

        Returns:
            (text_content, html_content)元组，包含更新后的内容
        """
        # 如果是单部分邮件
        if not msg.is_multipart():
            content_type = msg.get_content_type()
            content_disposition = msg.get_content_disposition()

            # 获取内容
            try:
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or "utf-8"
                content = payload.decode(charset, errors="replace")
            except:
                content = str(msg.get_payload())

            # 根据内容类型处理
            if content_type == "text/plain" and content_disposition != "attachment":
                text_content = content
            elif content_type == "text/html" and content_disposition != "attachment":
                html_content = content
            else:
                # 作为附件处理
                filename = msg.get_filename() or "unknown"
                attachment = Attachment(
                    filename=filename, content_type=content_type, content=payload
                )
                attachments.append(attachment)
        else:
            # 多部分邮件，递归处理每个部分
            for part in msg.get_payload():
                text_content, html_content = self._process_message_parts(
                    part, text_content, html_content, attachments
                )

        return text_content, html_content
