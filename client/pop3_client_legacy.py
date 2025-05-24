"""
POP3客户端模块 - 处理邮件接收功能
"""

import os
import poplib
import ssl
import email
import time
import base64
import socket
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
            username: 认证用户名
            password: 认证密码
            auth_method: 认证方法，可选值为"BASIC"、"APOP"或"AUTO"（自动选择）
            timeout: 连接超时时间（秒）
            max_retries: 最大重试次数
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.username = username
        self.password = password
        self.auth_method = auth_method
        self.timeout = timeout
        self.max_retries = max_retries
        self.connection = None
        self.socket = None
        self.ssl_context = None

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
                    # 创建更宽松的SSL上下文以解决握手问题
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    # 设置更宽松的SSL选项
                    context.options |= ssl.OP_NO_SSLv2
                    context.options |= ssl.OP_NO_SSLv3
                    # 增加超时时间并设置更大的缓冲区
                    temp_connection = poplib.POP3_SSL(
                        self.host, self.port, timeout=self.timeout * 3, context=context
                    )
                else:
                    temp_connection = poplib.POP3(
                        self.host, self.port, timeout=self.timeout
                    )

                # 如果提供了认证信息，则进行认证
                if self.username and self.password:
                    # 获取服务器欢迎信息，检查是否支持APOP
                    welcome = temp_connection.welcome
                    supports_apop = False

                    if isinstance(welcome, bytes):
                        welcome = welcome.decode("utf-8", errors="ignore")

                    supports_apop = "<" in welcome and ">" in welcome and "@" in welcome

                    logger.debug(f"服务器是否支持APOP: {supports_apop}")

                    # 根据认证方法进行认证
                    if self.auth_method == "APOP" or (
                        self.auth_method == "AUTO" and supports_apop
                    ):
                        # 使用APOP认证
                        try:
                            temp_connection.apop(self.username, self.password)
                            logger.info(f"已使用APOP认证: {self.username}")
                        except (poplib.error_proto, Exception) as auth_err:
                            # 如果APOP认证失败，且是AUTO模式，尝试基本认证
                            if self.auth_method == "AUTO":
                                logger.warning(
                                    f"APOP认证失败: {auth_err}, 尝试基本认证"
                                )
                                temp_connection.user(self.username)
                                temp_connection.pass_(self.password)
                                logger.info(f"已使用基本认证: {self.username}")
                            else:
                                # 如果指定了APOP且失败，则抛出异常
                                raise
                    else:
                        # 使用基本认证
                        temp_connection.user(self.username)
                        temp_connection.pass_(self.password)
                        logger.info(f"已使用基本认证: {self.username}")

                # 认证成功后，将临时连接赋值给实例变量
                self.connection = temp_connection
                temp_connection = None  # 避免在finally中关闭连接

                logger.info(f"已连接到POP3服务器: {self.host}:{self.port}")
                return
            except (poplib.error_proto, OSError, ssl.SSLError) as e:
                last_exception = e
                retry_count += 1

                # 检查是否是QQ邮箱特定的错误
                error_msg = str(e).lower()
                if "please using authorized code to login" in error_msg:
                    logger.warning(
                        f"QQ邮箱要求使用授权码而非密码登录，请在QQ邮箱设置中获取授权码"
                    )

                # 检查是否是SSL相关错误
                if "eof occurred in violation of protocol" in error_msg:
                    logger.warning(f"SSL协议错误，可能是服务器SSL配置问题")
                elif "ssl" in error_msg and "handshake" in error_msg:
                    logger.warning(f"SSL握手失败，尝试调整SSL设置")

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

                # 对于SSL错误，增加等待时间
                wait_time = 2 if "ssl" in error_msg else 1
                time.sleep(wait_time)
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
            try:
                # 发送QUIT命令
                logger.debug("发送QUIT命令")
                try:
                    self.connection.quit()
                    logger.info("已发送QUIT命令并断开连接")
                except (
                    socket.timeout,
                    ssl.SSLError,
                    ConnectionError,
                    poplib.error_proto,
                ) as e:
                    error_msg = str(e).lower()
                    if "eof occurred in violation of protocol" in error_msg:
                        logger.warning(f"SSL连接已断开，跳过QUIT命令: {e}")
                    else:
                        logger.warning(f"发送QUIT命令时出错: {e}")

                    # 如果QUIT命令失败，尝试直接关闭套接字
                    if hasattr(self.connection, "sock") and self.connection.sock:
                        try:
                            self.connection.sock.close()
                            logger.info("已直接关闭套接字")
                        except Exception as close_e:
                            logger.debug(f"关闭套接字时出错: {close_e}")
            except Exception as e:
                logger.error(f"断开连接时出错: {e}")
                import traceback

                logger.error(f"异常详情: {traceback.format_exc()}")
            finally:
                # 确保连接对象被清除
                self.connection = None
                logger.debug("连接对象已清除")
        else:
            logger.debug("没有活动的连接需要断开")

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

        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                # 获取邮件内容
                _, lines, _ = self.connection.retr(msg_num)  # 忽略响应码和字节数

                # 解析邮件
                msg_content = b"\r\n".join(lines)

                # 修复POP3服务器返回的不标准邮件格式（每个头部字段后有额外空行）
                msg_content_fixed = self._fix_email_headers(msg_content)

                parser = BytesParser(policy=policy.default)
                msg = parser.parsebytes(msg_content_fixed)

                # 先检查是否是包装邮件
                # 注意：只有在头部字段为空时才检测包装邮件
                if self._is_wrapped_email(msg):
                    logger.info("检测到包装邮件，尝试解包")
                    unwrapped_msg = self._unwrap_email(msg)
                    if unwrapped_msg:
                        msg = unwrapped_msg
                        logger.info("邮件解包成功")
                else:
                    logger.debug("邮件不是包装邮件，直接处理")

                # 转换为Email对象
                email_obj = self._convert_to_email(msg)

                # 如果需要，标记邮件为删除
                if delete:
                    self.connection.dele(msg_num)
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
                        if self.connection:
                            self.connection = None
                    except:
                        pass

                    # 等待后重新连接
                    time.sleep(2)  # 增加等待时间
                    try:
                        self.connect()
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

    def _fix_email_headers(self, msg_content: bytes) -> bytes:
        """
        基本的邮件格式处理（服务器端已修复格式问题）

        由于服务器端的_build_complete_email_content方法已经修复了邮件格式问题，
        此方法现在只进行基本的容错处理。

        Args:
            msg_content: 原始邮件内容

        Returns:
            邮件内容（现在基本不做修改）
        """
        try:
            # 服务器端已修复格式问题，这里只做基本的编码容错
            return msg_content
        except Exception as e:
            logger.debug(f"邮件内容处理时出现异常（已忽略）: {e}")
            # 如果有任何问题，返回原始内容
            return msg_content

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
        connection_retry_count = 0
        max_connection_retries = 3
        processed_msgs = set()  # 记录已处理的邮件编号

        while connection_retry_count < max_connection_retries:
            try:
                # 确保连接
                if not self.connection:
                    self.connect()

                # 获取邮件列表
                email_list = self.list_emails()

                # 如果设置了limit，只获取指定数量的邮件
                if limit and limit < len(email_list):
                    email_list = email_list[-limit:]  # 获取最新的limit封邮件

                # 获取每封邮件
                for i, (msg_num, _) in enumerate(email_list):
                    # 如果邮件已处理，跳过
                    if msg_num in processed_msgs:
                        continue

                    try:
                        # 每处理5封邮件，重新连接一次，避免长时间连接导致超时
                        if (
                            len(emails) > 0
                            and len(emails) % 5 == 0
                            and msg_num not in processed_msgs
                        ):
                            logger.info(
                                f"已处理 {len(emails)} 封邮件，重新连接以避免超时"
                            )
                            self.disconnect()
                            time.sleep(1)  # 等待1秒
                            try:
                                self.connect()
                                logger.info(f"重新连接成功，继续获取剩余邮件")
                                # 不需要退出循环，继续处理当前邮件
                            except Exception as conn_err:
                                logger.error(f"重新连接失败: {conn_err}")
                                # 尝试再次连接
                                time.sleep(2)  # 等待更长时间
                                self.connect()
                                logger.info(f"第二次重新连接成功")

                        email_obj = self.retrieve_email(msg_num, delete)
                        if not email_obj:
                            logger.warning(f"无法获取邮件 {msg_num}，跳过")
                            processed_msgs.add(msg_num)  # 标记为已处理
                            continue

                        # 应用过滤条件
                        # 日期过滤
                        if since_date and email_obj.date:
                            try:
                                # 处理时区问题：将两个日期都转换为naive datetime进行比较
                                email_date = email_obj.date
                                filter_date = since_date

                                # 如果邮件日期有时区信息，转换为naive datetime
                                if email_date.tzinfo is not None:
                                    email_date = email_date.replace(tzinfo=None)

                                # 如果过滤日期有时区信息，转换为naive datetime
                                if filter_date.tzinfo is not None:
                                    filter_date = filter_date.replace(tzinfo=None)

                                if email_date < filter_date:
                                    processed_msgs.add(msg_num)  # 标记为已处理
                                    continue
                            except Exception as date_err:
                                logger.warning(
                                    f"日期比较失败，跳过日期过滤: {date_err}"
                                )
                                # 如果日期比较失败，不应用日期过滤，继续处理邮件

                        # 发件人过滤
                        if (
                            from_addr
                            and from_addr.lower()
                            not in email_obj.from_addr.address.lower()
                        ):
                            processed_msgs.add(msg_num)  # 标记为已处理
                            continue

                        # 主题过滤
                        if (
                            subject_contains
                            and subject_contains.lower()
                            not in email_obj.subject.lower()
                        ):
                            processed_msgs.add(msg_num)  # 标记为已处理
                            continue

                        # 未读状态过滤（需要与本地数据库集成）
                        if only_unread:
                            # 这里需要查询数据库判断邮件是否已读
                            # 暂时跳过此过滤条件，后续实现
                            pass

                        emails.append(email_obj)
                        processed_msgs.add(msg_num)  # 标记为已处理
                    except Exception as e:
                        logger.error(f"处理邮件 {msg_num} 时出错: {e}")
                        processed_msgs.add(msg_num)  # 即使出错也标记为已处理
                        continue

                # 如果成功获取了所有邮件，跳出循环
                break
            except (socket.timeout, ssl.SSLError, ConnectionError) as e:
                connection_retry_count += 1
                error_msg = str(e).lower()

                if (
                    "timed out" in error_msg
                    or "cannot read from timed out object" in error_msg
                ):
                    logger.warning(
                        f"连接超时，尝试重新连接 ({connection_retry_count}/{max_connection_retries})"
                    )
                    # 重新连接
                    self.disconnect()
                    time.sleep(2)  # 等待2秒
                    try:
                        self.connect()
                    except Exception as conn_err:
                        logger.error(f"重新连接失败: {conn_err}")
                        time.sleep(2)  # 等待更长时间
                else:
                    logger.error(f"获取邮件列表失败: {e}")
                    break
            except Exception as e:
                logger.error(f"获取所有邮件失败: {e}")
                import traceback

                logger.error(f"异常详情: {traceback.format_exc()}")
                break

        logger.info(f"已获取{len(emails)}封邮件")
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

        # 确保邮件有Message-ID
        if not email_obj.message_id:
            # 如果没有Message-ID，生成一个
            import uuid

            email_obj.message_id = f"<{uuid.uuid4()}@localhost>"
            logger.info(f"为邮件生成Message-ID: {email_obj.message_id}")

        # 清理邮件ID，移除尖括号和特殊字符
        message_id = email_obj.message_id.strip("<>").replace("@", "_at_")
        message_id = re.sub(r'[\\/*?:"<>|]', "_", message_id)

        # 与POP3服务器和SMTP客户端保持一致的命名方式，仅使用Message-ID作为文件名
        filename = f"{message_id}.eml"
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
        # 处理邮件内容
        text_content = ""
        html_content = ""
        attachments = []

        # 先检查是否是包装邮件
        # 注意：只有在头部字段为空时才检测包装邮件
        if self._is_wrapped_email(msg):
            logger.info("检测到包装邮件，尝试解包")
            unwrapped_msg = self._unwrap_email(msg)
            if unwrapped_msg:
                msg = unwrapped_msg
                logger.info("邮件解包成功")
        else:
            logger.debug("邮件不是包装邮件，直接处理")

        # 使用改进的内容处理方法
        text_content, html_content = self._process_message_parts_enhanced(
            msg, text_content, html_content, attachments
        )

        # 提取基本信息
        subject = msg.get("Subject", "")
        logger.debug(f"原始邮件头 - Subject: {subject}")
        logger.debug(f"原始邮件头 - From: {msg.get('From', '')}")
        logger.debug(f"原始邮件头 - To: {msg.get('To', '')}")
        logger.debug(f"原始邮件头 - Message-ID: {msg.get('Message-ID', '')}")

        # 详细解码主题
        if subject:
            subject = self._decode_header_value(subject)

        # 解析发件人
        from_addr_str = msg.get("From", "")
        if from_addr_str:
            from_addr = self._parse_address_enhanced(from_addr_str)
        else:
            from_addr = EmailAddress("", "")

        # 解析收件人
        to_addrs = []
        to_addr_str = msg.get("To", "")
        if to_addr_str:
            to_addrs = self._parse_addresses_enhanced(to_addr_str)

        # 解析抄送
        cc_addrs = []
        cc_addr_str = msg.get("Cc", "")
        if cc_addr_str:
            cc_addrs = self._parse_addresses_enhanced(cc_addr_str)

        # 解析密送
        bcc_addrs = []
        bcc_addr_str = msg.get("Bcc", "")
        if bcc_addr_str:
            bcc_addrs = self._parse_addresses_enhanced(bcc_addr_str)

        # 获取日期
        date_str = msg.get("Date", "")
        date = self._parse_date(date_str) if date_str else datetime.datetime.now()

        # 获取Message-ID
        message_id = msg.get("Message-ID", "")
        if message_id:
            # 去除尖括号
            message_id = message_id.strip("<>")

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

        return email_obj

    def _is_wrapped_email(self, msg: EmailMessage) -> bool:
        """
        检查是否是包装的邮件（有空的主题和发件人，但内容包含实际邮件）

        Args:
            msg: EmailMessage对象

        Returns:
            是否是包装邮件
        """
        # 检查关键字段是否为空或缺失
        subject = msg.get("Subject", "").strip()
        from_addr = msg.get("From", "").strip()
        to_addr = msg.get("To", "").strip()

        # 如果有正常的头部字段，不是包装邮件
        if subject or from_addr or to_addr:
            return False

        # 只有当所有关键字段都为空时，才考虑是包装邮件
        if not subject and not from_addr and not to_addr:
            # 检查是否有base64编码的内容且包含邮件头部
            try:
                # 获取文本内容
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        encoding = part.get("Content-Transfer-Encoding", "").lower()
                        if encoding == "base64":
                            payload = part.get_payload()
                            if isinstance(payload, str):
                                # 检查内容中是否包含邮件头部信息
                                if (
                                    "Subject:" in payload
                                    or "From:" in payload
                                    or "Content-Type:" in payload
                                    or "MIME-Version:" in payload
                                ):
                                    logger.info(
                                        "检测到包装邮件: 所有头部字段为空且内容包含邮件头部"
                                    )
                                    return True
                        else:
                            # 对于非base64内容，直接检查
                            try:
                                content = part.get_payload(decode=True)
                                if isinstance(content, bytes):
                                    content = content.decode("utf-8", errors="replace")
                                elif not isinstance(content, str):
                                    content = str(content)

                                # 检查内容中是否包含邮件头部信息和base64内容
                                if ("Subject:" in content or "From:" in content) and (
                                    "Content-Transfer-Encoding: base64" in content
                                    or "multipart/" in content
                                ):
                                    logger.info(
                                        "检测到包装邮件: 所有头部字段为空且内容包含邮件结构"
                                    )
                                    return True
                            except:
                                continue
            except:
                pass

        return False

    def _unwrap_email(self, msg: EmailMessage) -> Optional[EmailMessage]:
        """
        解包装邮件，提取内部的实际邮件

        Args:
            msg: 包装的EmailMessage对象

        Returns:
            解包后的EmailMessage对象，失败返回None
        """
        try:
            # 先尝试获取base64编码的内容
            content = self._get_base64_content(msg)

            # 如果没有base64内容，尝试获取普通的文本内容
            if not content:
                content = self._get_text_content(msg)

            if not content:
                return None

            logger.debug(f"解包前内容长度: {len(content)}")
            logger.debug(f"解包前内容开始: {content[:200]}")

            # 尝试解析内部邮件
            parser = email.parser.Parser(policy=policy.default)
            inner_msg = parser.parsestr(content)

            logger.debug(f"解包后主题: {inner_msg.get('Subject', '')}")
            logger.debug(f"解包后发件人: {inner_msg.get('From', '')}")

            return inner_msg
        except Exception as e:
            logger.warning(f"解包邮件失败: {e}")
            return None

    def _get_text_content(self, msg: EmailMessage) -> Optional[str]:
        """
        获取普通文本内容（非base64）

        Args:
            msg: EmailMessage对象

        Returns:
            文本内容，失败返回None
        """
        try:
            # 查找包含邮件头部的文本内容
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    encoding = part.get("Content-Transfer-Encoding", "").lower()
                    if encoding != "base64":  # 非base64内容
                        try:
                            content = part.get_payload(decode=True)
                            if isinstance(content, bytes):
                                content = content.decode("utf-8", errors="replace")
                            elif not isinstance(content, str):
                                content = str(content)

                            # 检查是否包含邮件头部信息
                            if "Subject:" in content and "From:" in content:
                                return content
                        except:
                            continue
        except Exception as e:
            logger.warning(f"获取文本内容失败: {e}")

        return None

    def _get_base64_content(self, msg: EmailMessage) -> Optional[str]:
        """
        获取并解码base64内容

        Args:
            msg: EmailMessage对象

        Returns:
            解码后的字符串内容，失败返回None
        """
        try:
            # 查找base64编码的内容
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    encoding = part.get("Content-Transfer-Encoding", "")
                    if encoding.lower() == "base64":
                        payload = part.get_payload()
                        if isinstance(payload, str):
                            # 解码base64
                            import base64

                            decoded_bytes = base64.b64decode(payload)
                            decoded_content = decoded_bytes.decode(
                                "utf-8", errors="replace"
                            )
                            return decoded_content
        except Exception as e:
            logger.warning(f"获取base64内容失败: {e}")

        return None

    def _decode_header_value(self, header_value: str) -> str:
        """
        解码邮件头部值

        Args:
            header_value: 原始头部值

        Returns:
            解码后的字符串
        """
        if not header_value:
            return ""

        try:
            from email.header import decode_header

            decoded_parts = decode_header(header_value)
            logger.debug(f"解码头部结果: {decoded_parts}")

            result_parts = []
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        try:
                            result_parts.append(part.decode(encoding))
                        except (UnicodeDecodeError, LookupError):
                            result_parts.append(part.decode("utf-8", errors="replace"))
                    else:
                        result_parts.append(part.decode("utf-8", errors="replace"))
                else:
                    result_parts.append(str(part))

            return "".join(result_parts)
        except Exception as e:
            logger.warning(f"解码头部值时出错: {e}")
            return header_value

    def _parse_address_enhanced(self, addr_str: str) -> EmailAddress:
        """
        增强的地址解析

        Args:
            addr_str: 地址字符串

        Returns:
            EmailAddress对象
        """
        if not addr_str:
            return EmailAddress(name="", address="")

        try:
            from email.utils import parseaddr

            name, address = parseaddr(addr_str)

            # 解码名称
            if name:
                name = self._decode_header_value(name)

            # 如果地址仍然为空，尝试从原始字段提取
            if not address and "<" in addr_str and ">" in addr_str:
                address = addr_str.split("<")[1].split(">")[0]

            return EmailAddress(name=name, address=address)
        except Exception as e:
            logger.warning(f"解析地址失败: {e}")
            return EmailAddress(name="", address=addr_str)

    def _parse_addresses_enhanced(self, addr_str: str) -> List[EmailAddress]:
        """
        增强的多地址解析

        Args:
            addr_str: 地址字符串

        Returns:
            EmailAddress对象列表
        """
        if not addr_str:
            return []

        try:
            from email.utils import getaddresses

            addresses = getaddresses([addr_str])
            result = []

            for name, address in addresses:
                # 解码名称
                if name:
                    name = self._decode_header_value(name)

                result.append(EmailAddress(name=name, address=address))

            return result
        except Exception as e:
            logger.warning(f"解析地址列表失败: {e}")
            # 回退到简单分割
            result = []
            for addr in addr_str.split(","):
                if addr.strip():
                    result.append(self._parse_address_enhanced(addr.strip()))
            return result

    def _parse_address(self, addr_str: str) -> EmailAddress:
        """
        解析单个邮件地址（向后兼容方法）

        Args:
            addr_str: 地址字符串

        Returns:
            EmailAddress对象
        """
        return self._parse_address_enhanced(addr_str)

    def _parse_addresses(self, addr_str: str) -> List[EmailAddress]:
        """
        解析多个邮件地址（向后兼容方法）

        Args:
            addr_str: 地址字符串

        Returns:
            EmailAddress对象列表
        """
        return self._parse_addresses_enhanced(addr_str)

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
                encoding = msg.get("Content-Transfer-Encoding", "").lower()
                charset = msg.get_content_charset() or "utf-8"

                if encoding == "base64":
                    # 处理base64编码的内容
                    payload = msg.get_payload()
                    if isinstance(payload, str):
                        import base64

                        try:
                            decoded_bytes = base64.b64decode(payload)
                            content = decoded_bytes.decode(charset, errors="replace")
                        except Exception as e:
                            logger.warning(f"base64解码失败: {e}")
                            content = payload  # 使用原始内容
                    else:
                        content = str(payload)
                elif encoding == "quoted-printable":
                    # 处理quoted-printable编码
                    payload = msg.get_payload()
                    if isinstance(payload, str):
                        import quopri

                        try:
                            decoded_bytes = quopri.decodestring(payload.encode())
                            content = decoded_bytes.decode(charset, errors="replace")
                        except Exception as e:
                            logger.warning(f"quoted-printable解码失败: {e}")
                            content = payload
                    else:
                        content = str(payload)
                else:
                    # 其他编码或无编码
                    payload = msg.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        content = payload.decode(charset, errors="replace")
                    else:
                        content = str(payload) if payload else ""

            except Exception as e:
                logger.warning(f"获取邮件内容失败: {e}")
                content = str(msg.get_payload()) if msg.get_payload() else ""

            # 根据内容类型处理
            if content_type == "text/plain" and content_disposition != "attachment":
                text_content = content
            elif content_type == "text/html" and content_disposition != "attachment":
                html_content = content
            else:
                # 作为附件处理
                filename = msg.get_filename() or "unknown"
                try:
                    payload_data = msg.get_payload(decode=True)
                    if not isinstance(payload_data, bytes):
                        payload_data = str(payload_data).encode("utf-8")
                except:
                    payload_data = b""

                attachment = Attachment(
                    filename=filename, content_type=content_type, content=payload_data
                )
                attachments.append(attachment)
        else:
            # 多部分邮件，递归处理每个部分
            for part in msg.get_payload():
                text_content, html_content = self._process_message_parts(
                    part, text_content, html_content, attachments
                )

        return text_content, html_content

    def _process_message_parts_enhanced(
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
                encoding = msg.get("Content-Transfer-Encoding", "").lower()
                charset = msg.get_content_charset() or "utf-8"

                if encoding == "base64":
                    # 处理base64编码的内容
                    payload = msg.get_payload()
                    if isinstance(payload, str):
                        import base64

                        try:
                            decoded_bytes = base64.b64decode(payload)
                            content = decoded_bytes.decode(charset, errors="replace")
                            logger.debug(f"成功解码base64内容，长度: {len(content)}")
                        except Exception as e:
                            logger.warning(f"base64解码失败: {e}")
                            content = payload  # 使用原始内容
                    else:
                        content = str(payload)
                elif encoding == "quoted-printable":
                    # 处理quoted-printable编码
                    payload = msg.get_payload()
                    if isinstance(payload, str):
                        import quopri

                        try:
                            decoded_bytes = quopri.decodestring(payload.encode())
                            content = decoded_bytes.decode(charset, errors="replace")
                        except Exception as e:
                            logger.warning(f"quoted-printable解码失败: {e}")
                            content = payload
                    else:
                        content = str(payload)
                else:
                    # 其他编码或无编码
                    payload = msg.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        content = payload.decode(charset, errors="replace")
                    else:
                        content = str(payload) if payload else ""

            except Exception as e:
                logger.warning(f"获取邮件内容失败: {e}")
                content = str(msg.get_payload()) if msg.get_payload() else ""

            # 根据内容类型处理
            if content_type == "text/plain" and content_disposition != "attachment":
                text_content = content
                logger.debug(f"设置文本内容，长度: {len(text_content)}")
            elif content_type == "text/html" and content_disposition != "attachment":
                html_content = content
                logger.debug(f"设置HTML内容，长度: {len(html_content)}")
            else:
                # 作为附件处理
                filename = msg.get_filename() or "unknown"
                try:
                    payload_data = msg.get_payload(decode=True)
                    if not isinstance(payload_data, bytes):
                        payload_data = str(payload_data).encode("utf-8")
                except:
                    payload_data = b""

                attachment = Attachment(
                    filename=filename, content_type=content_type, content=payload_data
                )
                attachments.append(attachment)
        else:
            # 多部分邮件，递归处理每个部分
            for part in msg.get_payload():
                # 特殊处理：如果部分的payload包含头部信息，提取真正的内容
                if not part.is_multipart():
                    payload = part.get_payload()

                    # 检查payload是否包含头部信息（这是POP3服务器格式问题导致的）
                    if isinstance(payload, str) and (
                        "Content-Type:" in payload or "MIME-Version:" in payload
                    ):
                        logger.debug("检测到payload包含头部信息，尝试提取base64内容")

                        # 分离头部和内容
                        lines = payload.split("\n")
                        base64_lines = []
                        in_content = False

                        for line in lines:
                            line_stripped = line.strip()
                            if in_content:
                                # 在内容区域，收集base64行
                                if line_stripped and not line_stripped.startswith("--"):
                                    base64_lines.append(line_stripped)
                            else:
                                # 在头部区域，查找Content-Transfer-Encoding
                                if line_stripped == "" or line_stripped == "\r":
                                    in_content = True
                                elif "Content-Transfer-Encoding: base64" in line:
                                    # 找到了base64编码标识
                                    pass

                        # 如果找到了base64内容，尝试解码
                        if base64_lines:
                            try:
                                # 连接所有base64行
                                base64_content = "".join(base64_lines)

                                # 解码base64
                                import base64

                                decoded_bytes = base64.b64decode(base64_content)
                                decoded_content = decoded_bytes.decode(
                                    "utf-8", errors="replace"
                                )

                                logger.debug(
                                    f"成功从payload中解码base64内容，长度: {len(decoded_content)}"
                                )

                                # 根据Content-Type确定是文本还是HTML
                                if "text/html" in payload:
                                    html_content = decoded_content
                                    logger.debug(
                                        f"设置HTML内容，长度: {len(html_content)}"
                                    )
                                elif "text/plain" in payload:
                                    text_content = decoded_content
                                    logger.debug(
                                        f"设置文本内容，长度: {len(text_content)}"
                                    )

                                continue  # 跳过正常处理

                            except Exception as e:
                                logger.warning(f"从payload中解码base64失败: {e}")

                # 正常递归处理
                text_content, html_content = self._process_message_parts_enhanced(
                    part, text_content, html_content, attachments
                )

        return text_content, html_content

    def _parse_date(self, date_str: str) -> datetime:
        """
        解析邮件日期

        Args:
            date_str: 日期字符串

        Returns:
            datetime对象
        """
        if not date_str:
            return datetime.datetime.now()

        try:
            from email.utils import parsedate_to_datetime

            return parsedate_to_datetime(date_str)
        except Exception as e:
            logger.warning(f"解析日期失败: {e}")
            try:
                # 尝试常见的日期格式
                import datetime as dt

                # 尝试ISO格式
                if "T" in date_str:
                    return dt.datetime.fromisoformat(date_str.replace("Z", "+00:00"))

                # 尝试其他格式
                formats = [
                    "%a, %d %b %Y %H:%M:%S %z",
                    "%a, %d %b %Y %H:%M:%S",
                    "%d %b %Y %H:%M:%S %z",
                    "%d %b %Y %H:%M:%S",
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d",
                ]

                for fmt in formats:
                    try:
                        return dt.datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue

            except Exception:
                pass

            # 如果所有解析都失败，返回当前时间
            return datetime.datetime.now()
