"""
SMTP客户端模块 - 处理邮件发送功能
"""

import os
import smtplib
import ssl
import base64
import time
import datetime
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.utils import formataddr, make_msgid, formatdate
from email.header import Header
from typing import List, Dict, Optional, Union, BinaryIO, Tuple, Literal
import mimetypes
from pathlib import Path
import re
import uuid

from common.utils import (
    setup_logging,
    generate_message_id,
    is_valid_email,
    safe_filename,
)
from common.models import Email, EmailAddress, Attachment, EmailStatus
from common.config import SMTP_SERVER, EMAIL_STORAGE_DIR
from client.mime_handler import MIMEHandler
from server.new_db_handler import EmailService
from client.socket_utils import close_socket_safely, close_ssl_connection_safely
from common.email_format_handler import EmailFormatHandler

# 设置日志
logger = setup_logging("smtp_client")


class SMTPClient:
    """SMTP客户端类，处理邮件发送"""

    def __init__(
        self,
        host: str = SMTP_SERVER["host"],
        port: int = SMTP_SERVER["port"],
        use_ssl: bool = SMTP_SERVER["use_ssl"],
        ssl_port: int = SMTP_SERVER["ssl_port"],
        username: Optional[str] = None,
        password: Optional[str] = None,
        auth_method: Optional[Literal["LOGIN", "PLAIN", "AUTO"]] = "AUTO",
        timeout: int = 30,
        save_sent_emails: bool = True,
        sent_emails_dir: str = EMAIL_STORAGE_DIR,
        max_retries: int = 3,
    ):
        """
        初始化SMTP客户端

        Args:
            host: SMTP服务器主机名
            port: SMTP服务器端口
            use_ssl: 是否使用SSL/TLS
            ssl_port: SSL/TLS端口
            username: 认证用户名
            password: 认证密码
            auth_method: 认证方法，可选值为"LOGIN"、"PLAIN"或"AUTO"（自动选择）
            timeout: 连接超时时间（秒）
            save_sent_emails: 是否保存已发送邮件
            sent_emails_dir: 已发送邮件保存目录
            max_retries: 最大重试次数
        """
        self.host = host
        self.port = ssl_port if use_ssl else port
        self.use_ssl = use_ssl
        self.username = username
        self.password = password
        self.auth_method = auth_method
        self.timeout = timeout
        self.connection = None
        self.save_sent_emails = save_sent_emails
        self.sent_emails_dir = os.path.join(sent_emails_dir, "sent")
        self.max_retries = max_retries

        # 确保已发送邮件目录存在
        if self.save_sent_emails:
            os.makedirs(self.sent_emails_dir, exist_ok=True)

        # 创建邮件服务
        self.email_service = EmailService()

    def connect(self) -> None:
        """
        连接到SMTP服务器

        Raises:
            smtplib.SMTPException: 连接失败时抛出
        """
        retry_count = 0
        last_exception = None
        temp_connection = None

        # 确保所有字符串都是 UTF-8 编码
        host = self.host
        username = self.username
        password = self.password

        # 确保这些值是字符串类型
        if not isinstance(host, str):
            host = str(host) if host is not None else ""
        if not isinstance(username, str):
            username = str(username) if username is not None else ""
        if not isinstance(password, str):
            password = str(password) if password is not None else ""

        while retry_count < self.max_retries:
            try:
                if self.use_ssl:
                    context = ssl.create_default_context()
                    temp_connection = smtplib.SMTP_SSL(
                        host, self.port, timeout=self.timeout, context=context
                    )
                else:
                    temp_connection = smtplib.SMTP(
                        host, self.port, timeout=self.timeout
                    )

                    # 如果服务器支持STARTTLS，则使用它
                    if temp_connection.has_extn("STARTTLS"):
                        context = ssl.create_default_context()
                        temp_connection.starttls(context=context)

                # 如果提供了认证信息，则进行认证
                if username and password:
                    # 检查服务器支持的认证方法
                    auth_methods = []
                    if hasattr(temp_connection, "esmtp_features"):
                        auth_feature = temp_connection.esmtp_features.get(
                            "auth", ""
                        ).upper()
                        if auth_feature:
                            auth_methods = auth_feature.split()

                    logger.debug(f"服务器支持的认证方法: {auth_methods}")

                    if self.auth_method == "AUTO":
                        # 使用标准登录方法，让smtplib自动选择
                        temp_connection.login(username, password)
                    elif self.auth_method == "PLAIN":
                        # 使用AUTH PLAIN
                        if not auth_methods or "PLAIN" in auth_methods:
                            # 使用UTF-8编码生成认证字符串
                            auth_bytes = (
                                b"\0"
                                + username.encode("utf-8")
                                + b"\0"
                                + password.encode("utf-8")
                            )
                            auth_string = base64.b64encode(auth_bytes).decode("utf-8")

                            code, response = temp_connection.docmd(
                                "AUTH PLAIN", auth_string
                            )
                            if code != 235:
                                raise smtplib.SMTPAuthenticationError(code, response)
                        else:
                            logger.warning("服务器不支持PLAIN认证，尝试使用标准登录")
                            temp_connection.login(username, password)
                    elif self.auth_method == "LOGIN":
                        # 使用AUTH LOGIN
                        if not auth_methods or "LOGIN" in auth_methods:
                            code, response = temp_connection.docmd("AUTH LOGIN")
                            if code != 334:
                                raise smtplib.SMTPAuthenticationError(code, response)

                            # 使用UTF-8编码用户名和密码
                            username_b64 = base64.b64encode(
                                username.encode("utf-8")
                            ).decode("utf-8")
                            password_b64 = base64.b64encode(
                                password.encode("utf-8")
                            ).decode("utf-8")

                            code, response = temp_connection.docmd(username_b64)
                            if code != 334:
                                raise smtplib.SMTPAuthenticationError(code, response)

                            code, response = temp_connection.docmd(password_b64)
                            if code != 235:
                                raise smtplib.SMTPAuthenticationError(code, response)
                        else:
                            logger.warning("服务器不支持LOGIN认证，尝试使用标准登录")
                            temp_connection.login(username, password)
                    else:
                        # 默认使用标准登录
                        temp_connection.login(username, password)

                    logger.info(f"已使用 {self.auth_method} 方法认证: {username}")

                # 认证成功后，将临时连接赋值给实例变量
                self.connection = temp_connection
                temp_connection = None  # 避免在finally中关闭连接

                logger.info(f"已连接到SMTP服务器: {host}:{self.port}")
                return
            except (smtplib.SMTPAuthenticationError, smtplib.SMTPException) as e:
                last_exception = e
                retry_count += 1

                # 检查是否是QQ邮箱特定的错误
                error_msg = str(e).lower()
                if "please using authorized code to login" in error_msg:
                    logger.warning(
                        f"QQ邮箱要求使用授权码而非密码登录，请在QQ邮箱设置中获取授权码"
                    )

                logger.warning(
                    f"连接SMTP服务器失败 (尝试 {retry_count}/{self.max_retries}): {e}"
                )

                # 确保临时连接被安全关闭
                close_ssl_connection_safely(temp_connection)

                # 如果是认证错误，尝试不同的认证方法
                if (
                    isinstance(e, smtplib.SMTPAuthenticationError)
                    and self.auth_method == "AUTO"
                ):
                    if retry_count == 1:
                        logger.info(f"尝试切换到LOGIN认证方法")
                        self.auth_method = "LOGIN"
                    elif retry_count == 2:
                        logger.info(f"尝试切换到PLAIN认证方法")
                        self.auth_method = "PLAIN"

                # 短暂等待后重试
                time.sleep(1)
            except Exception as e:
                logger.error(f"连接SMTP服务器失败: {e}")
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
            logger.error(f"连接SMTP服务器失败，已达到最大重试次数: {last_exception}")
            raise last_exception

    def _authenticate(self) -> None:
        """
        使用指定的认证方法进行认证

        Raises:
            smtplib.SMTPAuthenticationError: 认证失败时抛出
        """
        try:
            # 确保所有字符串都是 UTF-8 编码
            username = str(self.username) if self.username is not None else ""
            password = str(self.password) if self.password is not None else ""

            # 检查服务器支持的认证方法
            auth_methods = []
            if hasattr(self.connection, "esmtp_features"):
                auth_feature = self.connection.esmtp_features.get("auth", "").upper()
                if auth_feature:
                    auth_methods = auth_feature.split()

            logger.debug(f"服务器支持的认证方法: {auth_methods}")

            if self.auth_method == "AUTO":
                # 使用标准登录方法，让smtplib自动选择
                self.connection.login(username, password)
            elif self.auth_method == "PLAIN":
                # 使用AUTH PLAIN
                if not auth_methods or "PLAIN" in auth_methods:
                    auth_string = self._generate_auth_plain_string()
                    code, response = self.connection.docmd("AUTH PLAIN", auth_string)
                    if code != 235:
                        raise smtplib.SMTPAuthenticationError(code, response)
                else:
                    logger.warning("服务器不支持PLAIN认证，尝试使用标准登录")
                    self.connection.login(username, password)
            elif self.auth_method == "LOGIN":
                # 使用AUTH LOGIN
                if not auth_methods or "LOGIN" in auth_methods:
                    code, response = self.connection.docmd("AUTH LOGIN")
                    if code != 334:
                        raise smtplib.SMTPAuthenticationError(code, response)

                    # 使用UTF-8编码用户名和密码
                    username_b64 = base64.b64encode(username.encode("utf-8")).decode(
                        "utf-8"
                    )
                    password_b64 = base64.b64encode(password.encode("utf-8")).decode(
                        "utf-8"
                    )

                    code, response = self.connection.docmd(username_b64)
                    if code != 334:
                        raise smtplib.SMTPAuthenticationError(code, response)

                    code, response = self.connection.docmd(password_b64)
                    if code != 235:
                        raise smtplib.SMTPAuthenticationError(code, response)
                else:
                    logger.warning("服务器不支持LOGIN认证，尝试使用标准登录")
                    self.connection.login(username, password)
            else:
                # 默认使用标准登录
                self.connection.login(username, password)

            logger.info(f"已使用 {self.auth_method} 方法认证: {username}")
        except Exception as e:
            logger.error(f"认证失败 ({self.auth_method}): {e}")
            raise

    def _generate_auth_plain_string(self) -> str:
        """
        生成AUTH PLAIN认证字符串

        Returns:
            BASE64编码的认证字符串
        """
        # 确保用户名和密码是字符串类型
        username = str(self.username) if self.username is not None else ""
        password = str(self.password) if self.password is not None else ""

        # AUTH PLAIN格式: \0username\0password
        auth_bytes = b"\0" + username.encode("utf-8") + b"\0" + password.encode("utf-8")
        # 使用 utf-8 而不是 ascii 解码
        return base64.b64encode(auth_bytes).decode("utf-8")

    def disconnect(self) -> None:
        """断开与SMTP服务器的连接"""
        if self.connection:
            # 使用工具函数安全地关闭连接
            if close_ssl_connection_safely(self.connection):
                logger.info("已断开与SMTP服务器的连接")
            else:
                logger.warning("断开与SMTP服务器的连接可能不完全")

            # 确保连接对象被清除
            self.connection = None

    def send_email(self, email: Email) -> bool:
        """
        发送邮件

        Args:
            email: 邮件对象

        Returns:
            发送成功返回True，失败返回False
        """
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                # 确保连接已建立
                if not self.connection:
                    self.connect()

                # 使用统一的邮件格式处理器创建MIME消息
                mime_msg = EmailFormatHandler.create_mime_message(email)

                # 准备收件人列表（包括To、Cc、Bcc）
                all_recipients = []
                all_recipients.extend([addr.address for addr in email.to_addrs])
                all_recipients.extend([addr.address for addr in email.cc_addrs])
                all_recipients.extend([addr.address for addr in email.bcc_addrs])

                # 确保发件人地址
                from_addr = (
                    email.from_addr.address if email.from_addr else self.username
                )

                # 发送邮件
                self.connection.send_message(mime_msg, from_addr, all_recipients)

                # 保存已发送邮件
                if self.save_sent_emails:
                    self._save_sent_email(email)

                logger.info(f"邮件发送成功: {email.subject}")
                return True

            except Exception as e:
                retry_count += 1
                logger.error(
                    f"发送邮件失败 (尝试 {retry_count}/{self.max_retries}): {e}"
                )

                # 如果是连接相关错误，重新连接
                if "connection" in str(e).lower() or "timed out" in str(e).lower():
                    try:
                        self.disconnect()
                        time.sleep(2)  # 等待2秒后重试
                        self.connect()
                    except Exception as conn_e:
                        logger.error(f"重新连接失败: {conn_e}")

                if retry_count >= self.max_retries:
                    logger.error(f"邮件发送最终失败: {email.subject}")
                    return False

        return False

    def _save_sent_email(self, email: Email) -> None:
        """
        保存已发送邮件 - 统一使用EmailFormatHandler
        """
        try:
            # 使用统一的Message ID
            message_id = email.message_id

            # 生成安全的文件名，移除非法字符
            safe_message_id = re.sub(r'[<>:"/\\|?*]', "_", message_id)
            # 确保文件名不会太长
            if len(safe_message_id) > 100:
                safe_message_id = safe_message_id[:100]

            # 与POP3服务器保持一致的命名方式
            filename = f"{safe_message_id}.eml"
            filepath = os.path.join(self.sent_emails_dir, filename)

            # 保存为.eml文件 - 使用统一的格式处理器
            formatted_content = EmailFormatHandler.format_email_for_storage(email)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(formatted_content)

            # 保存元数据到数据库
            self.email_service.save_sent_email(
                message_id=email.message_id,
                from_addr=str(email.from_addr),
                to_addrs=[str(addr) for addr in email.to_addrs],
                subject=email.subject,
                date=email.date,
                content=formatted_content,
            )

            logger.info(f"已保存已发送邮件: {filepath}")
        except Exception as e:
            logger.error(f"保存已发送邮件失败: {e}")
            # 不抛出异常，以免影响正常的邮件发送流程

    def _create_mime_message(self, email: Email):
        """
        向后兼容方法：创建MIME消息
        为了保持向后兼容性，保留此方法但内部调用统一的EmailFormatHandler

        Args:
            email: Email对象

        Returns:
            MIME消息对象
        """
        try:
            # 使用统一的EmailFormatHandler创建MIME消息
            return EmailFormatHandler.create_mime_message(email)
        except Exception as e:
            logger.error(f"创建MIME消息失败: {e}")
            raise
