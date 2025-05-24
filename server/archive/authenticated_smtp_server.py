"""
认证SMTP服务器模块 - 使用aiosmtpd实现带完整认证功能的SMTP服务
"""

import os
import sys
import ssl
import socket
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any, Set, Tuple
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP, Session, Envelope, AuthResult, LoginPassword
import datetime
import uuid
import email
from email import policy
from email.parser import Parser
from email.header import decode_header

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.config import AUTH_REQUIRED, EMAIL_STORAGE_DIR, SSL_CERT_FILE, SSL_KEY_FILE
from server.new_db_handler import EmailService as DatabaseHandler
from server.user_auth import UserAuth
from common.port_config import resolve_port, is_port_available, find_available_port

# 设置日志
logger = setup_logging("authenticated_smtp_server")


class AuthenticatedSMTPHandler:
    """认证SMTP处理程序，处理SMTP命令和邮件接收，支持完整的认证功能"""

    def __init__(self, db_handler: DatabaseHandler = None, server=None):
        """
        初始化SMTP处理程序

        Args:
            db_handler: 数据库处理器，如果为None则创建一个新的
            server: SMTP服务器实例，用于访问服务器配置
        """
        self.db_handler = db_handler or EmailService()
        self.user_auth = UserAuth()
        self._server = server  # 保存服务器引用，用于访问配置

        # 认证状态
        self.authenticated_sessions: Set[Session] = set()

        logger.info("认证SMTP处理程序已初始化")

    async def handle_EHLO(self, server, session, envelope, hostname, responses):
        """
        处理EHLO命令

        Args:
            server: SMTP服务器实例
            session: 当前会话
            envelope: 当前邮件信封
            hostname: 客户端主机名
            responses: 计划的响应列表

        Returns:
            响应列表
        """
        session.host_name = hostname
        logger.info(f"EHLO: {hostname}")
        return responses

    async def handle_MAIL(self, server, session, envelope, address, mail_options):
        """
        处理MAIL FROM命令

        Args:
            server: SMTP服务器实例
            session: 当前会话
            envelope: 当前邮件信封
            address: 发件人地址
            mail_options: 邮件选项

        Returns:
            响应字符串
        """
        # 检查是否需要认证
        # 打印认证状态，帮助调试
        if hasattr(self, "_server") and self._server:
            logger.debug(
                f"认证要求状态: {'需要认证' if self._server.require_auth else '无需认证'}"
            )
            logger.debug(
                f"会话认证状态: {'已认证' if session in self.authenticated_sessions else '未认证'}"
            )

        # 只有当服务器要求认证且会话未认证时才拒绝
        if (
            hasattr(self, "_server")
            and self._server
            and self._server.require_auth
            and session not in self.authenticated_sessions
        ):
            logger.warning(f"未认证的会话尝试发送邮件: {address}")
            return "530 Authentication required"

        envelope.mail_from = address
        envelope.mail_options.extend(mail_options)
        logger.info(f"MAIL FROM: {address}")
        return "250 OK"

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        """
        处理RCPT TO命令

        Args:
            server: SMTP服务器实例
            session: 当前会话
            envelope: 当前邮件信封
            address: 收件人地址
            rcpt_options: 收件人选项

        Returns:
            响应字符串
        """
        if not address:
            return "550 Invalid recipient address"

        # 这里可以添加收件人验证逻辑
        # 例如，检查收件人是否存在于系统中

        envelope.rcpt_tos.append(address)
        envelope.rcpt_options.extend(rcpt_options)
        logger.info(f"RCPT TO: {address}")
        return "250 OK"

    async def handle_DATA(self, server, session, envelope):
        """
        处理DATA命令

        Args:
            server: SMTP服务器实例
            session: 当前会话
            envelope: 当前邮件信封

        Returns:
            响应字符串
        """
        if not envelope.mail_from:
            return "503 Error: need MAIL command"
        if not envelope.rcpt_tos:
            return "503 Error: need RCPT command"

        # 获取邮件内容
        mail_from = envelope.mail_from
        rcpt_tos = envelope.rcpt_tos
        content = envelope.content

        try:
            # 解析邮件内容
            if isinstance(content, bytes):
                email_content = content.decode("utf-8", errors="replace")
            else:
                email_content = content  # 如果已经是字符串，直接使用

            email_message = Parser(policy=policy.default).parsestr(email_content)

            # 提取Message-ID，如果没有则生成
            message_id = email_message.get("Message-ID")
            if not message_id:
                # 生成唯一的消息ID
                message_id = f"<{uuid.uuid4()}@example.com>"
                # 更新邮件内容中的Message-ID
                email_content = f"Message-ID: {message_id}\r\n{email_content}"

            # 确保message_id是有效的字符串
            message_id = str(message_id).strip()
            logger.debug(f"邮件Message-ID: {message_id}")

            # 提取和处理主题
            subject = email_message.get("Subject", "")
            # 如果主题是编码的，进行解码
            if subject:
                try:
                    decoded_subject = decode_header(subject)
                    if decoded_subject[0][1]:  # 如果有编码信息
                        subject = decoded_subject[0][0].decode(decoded_subject[0][1])
                    elif isinstance(decoded_subject[0][0], bytes):  # 如果是bytes类型
                        subject = decoded_subject[0][0].decode(
                            "utf-8", errors="replace"
                        )
                except Exception as e:
                    logger.warning(f"解码主题时出错: {e}")
            logger.debug(f"邮件主题: {subject}")

            # 详细记录和确保发件人地址正确
            logger.debug(f"原始发件人: {mail_from}")
            # 尝试从邮件头获取From字段并解析
            from_header = email_message.get("From", "")
            if from_header:
                try:
                    # 尝试解析发件人头
                    from email.utils import parseaddr

                    name, address = parseaddr(from_header)
                    if address:  # 如果解析出的地址非空，使用解析后的地址
                        mail_from = address
                        logger.debug(f"从头部解析的发件人地址: {mail_from}")
                except Exception as e:
                    logger.warning(f"解析发件人头时出错: {e}")

            # 详细记录收件人地址
            logger.debug(f"原始收件人列表: {rcpt_tos}")
            # 尝试从邮件头获取To字段并解析
            to_header = email_message.get("To", "")
            if to_header:
                try:
                    from email.utils import getaddresses

                    parsed_recipients = getaddresses([to_header])
                    if parsed_recipients:
                        parsed_addrs = [addr for _, addr in parsed_recipients if addr]
                        if parsed_addrs:
                            logger.debug(f"从头部解析的收件人地址: {parsed_addrs}")
                            # 保留原始rcpt_tos，仅用于日志记录
                            logger.debug(f"使用envelope中的收件人地址: {rcpt_tos}")
                except Exception as e:
                    logger.warning(f"解析收件人头时出错: {e}")

            # 提取日期（如果邮件头中有指定）
            try:
                date = email.utils.parsedate_to_datetime(email_message.get("Date"))
            except (TypeError, ValueError):
                date = datetime.datetime.now()
            logger.debug(f"邮件日期: {date}")

            # 记录解析结果
            logger.info(
                f"解析邮件: ID={message_id}, 主题='{subject}', 发件人={mail_from}, 收件人={rcpt_tos}"
            )

            # 保存邮件内容，使用提取的message_id
            self.db_handler.save_email_content(message_id, email_content)

            # 保存邮件元数据，使用相同的message_id
            self.db_handler.save_email_metadata(
                message_id=message_id,
                from_addr=mail_from,
                to_addrs=rcpt_tos,
                subject=subject,
                date=date,
                size=len(content),
                is_spam=False,
                spam_score=0.0,
            )

            logger.info(f"邮件已保存到数据库: ID={message_id}")
            return "250 Message accepted for delivery"
        except Exception as e:
            logger.error(f"保存邮件时出错: {e}")
            return "451 Requested action aborted: error in processing"


class AuthenticatedSMTPServer:
    """认证SMTP服务器类，使用aiosmtpd实现，支持完整的认证功能"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8025,
        db_handler: DatabaseHandler = None,
        require_auth: bool = True,  # 默认启用认证
        use_ssl: bool = True,  # 默认启用SSL
        ssl_cert_file: str = SSL_CERT_FILE,
        ssl_key_file: str = SSL_KEY_FILE,
    ):
        """
        初始化SMTP服务器

        Args:
            host: 服务器主机名或IP地址
            port: 服务器端口
            db_handler: 数据库处理器，如果为None则创建一个新的
            require_auth: 是否要求认证
            use_ssl: 是否使用SSL/TLS
            ssl_cert_file: SSL证书文件路径
            ssl_key_file: SSL密钥文件路径
        """
        # 确保host是有效的绑定地址
        if (
            host != "localhost"
            and host != "127.0.0.1"
            and not host.startswith("192.168.")
            and not host.startswith("10.")
        ):
            try:
                import socket

                # 尝试解析域名
                socket.gethostbyname(host)
            except:
                # 如果解析失败，回退到localhost
                logger.warning(f"无法解析主机名 {host}，回退到localhost")
                host = "localhost"

        self.host = host
        self.port = port
        self.db_handler = db_handler or EmailService()
        self.require_auth = require_auth
        self.use_ssl = use_ssl
        self.ssl_cert_file = ssl_cert_file
        self.ssl_key_file = ssl_key_file

        # 将服务器实例传递给处理程序
        self.handler = AuthenticatedSMTPHandler(self.db_handler, self)
        self.controller = None

        # 确保测试用户存在（用于测试）
        self._ensure_test_user_exists()

        # 创建SSL上下文（如果启用SSL）
        self.ssl_context = None
        if self.use_ssl:
            try:
                self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                self.ssl_context.load_cert_chain(
                    certfile=self.ssl_cert_file, keyfile=self.ssl_key_file
                )
                logger.info(f"已加载SSL证书: {self.ssl_cert_file}")
            except Exception as e:
                logger.error(f"加载SSL证书时出错: {e}")
                self.use_ssl = False
                self.ssl_context = None

        logger.info(
            f"认证SMTP服务器已初始化: {host}:{port}, "
            f"认证要求: {'启用' if require_auth else '禁用'}, "
            f"SSL: {'启用' if self.use_ssl else '禁用'}"
        )

    def _ensure_test_user_exists(self):
        """确保测试用户存在"""
        try:
            # 测试用户信息
            test_username = "testuser"
            test_password = "testpass"

            # 检查用户是否存在
            user = self.handler.user_auth.get_user_by_username(test_username)
            if not user:
                # 如果用户不存在，则创建
                self.handler.user_auth.add_user(test_username, test_password)
                logger.info(f"已创建测试用户: {test_username}")
            else:
                logger.debug(f"测试用户已存在: {test_username}")
        except Exception as e:
            logger.error(f"创建测试用户时出错: {e}")

    def auth_callback(self, server, session, envelope, mechanism, auth_data):
        """
        认证回调函数

        Args:
            server: SMTP服务器实例
            session: 当前会话
            envelope: 当前邮件信封
            mechanism: 认证机制
            auth_data: 认证数据

        Returns:
            认证结果
        """
        logger.debug(f"认证请求: 机制={mechanism}, 会话ID={id(session)}")

        if mechanism == "PLAIN":
            try:
                # 检查auth_data的类型
                if isinstance(auth_data, LoginPassword):
                    # 如果是LoginPassword对象，直接获取login和password
                    logger.debug("收到LoginPassword对象用于PLAIN认证")
                    username = auth_data.login.decode("utf-8", errors="replace")
                    password = auth_data.password.decode("utf-8", errors="replace")
                else:
                    # 否则，按照标准PLAIN格式解析
                    # PLAIN认证格式: \0username\0password
                    auth_str = auth_data.decode("utf-8", errors="replace")
                    parts = auth_str.split("\0")

                    # PLAIN认证可能有两种格式:
                    # 1. \0username\0password (3部分，第一部分为空)
                    # 2. username\0password (2部分)
                    if len(parts) == 3:
                        identity, username, password = parts
                    elif len(parts) == 2:
                        username, password = parts
                    else:
                        logger.warning(f"无效的PLAIN认证格式: {auth_str}")
                        return AuthResult(
                            success=False, message="Invalid authentication format"
                        )

                logger.debug(f"尝试PLAIN认证: 用户名={username}")

                # 使用UserAuth进行认证
                user = self.handler.user_auth.authenticate(username, password)
                if user:
                    # 认证成功
                    session.authenticated = True
                    self.handler.authenticated_sessions.add(session)
                    logger.info(f"用户认证成功: {username}")
                    return AuthResult(success=True, message="Authentication successful")
                else:
                    # 认证失败
                    logger.warning(f"用户认证失败: {username}")
                    return AuthResult(success=False, message="Authentication failed")
            except Exception as e:
                logger.error(f"PLAIN认证过程中出错: {e}")
                return AuthResult(
                    success=False, message=f"Authentication error: {str(e)}"
                )

        elif mechanism == "LOGIN":
            try:
                # LOGIN认证格式: 两步交互，第一步是用户名，第二步是密码
                if isinstance(auth_data, LoginPassword):
                    # 直接从LoginPassword对象获取用户名和密码
                    username = auth_data.login.decode("utf-8", errors="replace")
                    password = auth_data.password.decode("utf-8", errors="replace")

                    logger.debug(f"尝试LOGIN认证: 用户名={username}")

                    # 使用UserAuth进行认证
                    user = self.handler.user_auth.authenticate(username, password)
                    if user:
                        # 认证成功
                        session.authenticated = True
                        self.handler.authenticated_sessions.add(session)
                        logger.info(f"用户认证成功: {username}")
                        return AuthResult(
                            success=True, message="Authentication successful"
                        )
                    else:
                        # 认证失败
                        logger.warning(f"用户认证失败: {username}")
                        return AuthResult(
                            success=False, message="Authentication failed"
                        )
                elif isinstance(auth_data, bytes):
                    # 如果是bytes，可能是单独的用户名或密码
                    # 在LOGIN认证流程中，这种情况通常不会直接导致认证完成
                    # 我们应该返回一个中间结果，让客户端继续提供密码
                    logger.debug(f"收到LOGIN认证中间数据: {auth_data}")
                    return AuthResult(
                        success=False,
                        message="Continue authentication",
                        auth_continue=True,
                        auth_continue_prompt="Password:",
                    )
                else:
                    logger.error(f"不支持的LOGIN认证数据格式: {type(auth_data)}")
                    return AuthResult(success=False, message="Unsupported LOGIN format")
            except Exception as e:
                logger.error(f"LOGIN认证过程中出错: {e}")
                return AuthResult(
                    success=False, message=f"Authentication error: {str(e)}"
                )
        else:
            # 不支持的认证机制
            logger.warning(f"不支持的认证机制: {mechanism}")
            return AuthResult(
                success=False,
                message=f"Unsupported authentication mechanism: {mechanism}",
            )

    def start(self) -> None:
        """启动SMTP服务器"""
        if self.controller:
            logger.warning("SMTP服务器已经在运行")
            return

        # 使用统一的端口管理逻辑
        port, changed, message = resolve_port(
            "smtp", self.port, self.use_ssl, auto_detect=True
        )

        if port == 0:
            logger.error(message)
            raise RuntimeError(message)

        if changed:
            logger.warning(message)
            print(f"\n[警告] {message}\n")
            self.port = port

        logger.info(message)

        try:
            # 创建控制器
            self.controller = Controller(
                handler=self.handler,
                hostname=self.host,
                port=self.port,
                authenticator=self.auth_callback,  # 始终设置认证回调
                auth_require_tls=False,  # 在生产环境中应设置为True
                ssl_context=self.ssl_context,  # 如果启用SSL，则使用SSL上下文
            )

            # 启动控制器
            self.controller.start()

            logger.info(f"认证SMTP服务器已启动: {self.host}:{self.port}")
            logger.info(f"认证要求: {'启用' if self.require_auth else '禁用'}")
            logger.info(f"SSL: {'启用' if self.use_ssl else '禁用'}")
        except Exception as e:
            logger.error(f"启动SMTP服务器时出错: {e}")
            if self.controller:
                try:
                    self.controller.stop()
                except:
                    pass
            self.controller = None

    def stop(self) -> None:
        """停止SMTP服务器"""
        if self.controller:
            self.controller.stop()
            self.controller = None
            logger.info("认证SMTP服务器已停止")


if __name__ == "__main__":
    # 从命令行参数获取主机名和端口
    import argparse

    parser = argparse.ArgumentParser(description="认证SMTP服务器")
    parser.add_argument("--host", default="localhost", help="服务器主机名")
    parser.add_argument("--port", type=int, default=8025, help="服务器端口")
    parser.add_argument("--auth", action="store_true", help="启用认证")
    parser.add_argument("--no-auth", dest="auth", action="store_false", help="禁用认证")
    parser.add_argument("--ssl", action="store_true", help="启用SSL")
    parser.add_argument("--no-ssl", dest="ssl", action="store_false", help="禁用SSL")
    parser.add_argument(
        "--cert", type=str, default=SSL_CERT_FILE, help="SSL证书文件路径"
    )
    parser.add_argument("--key", type=str, default=SSL_KEY_FILE, help="SSL密钥文件路径")
    parser.set_defaults(auth=True, ssl=True)  # 默认启用认证和SSL
    args = parser.parse_args()

    # 创建并启动服务器
    server = AuthenticatedSMTPServer(
        host=args.host,
        port=args.port,
        require_auth=args.auth,
        use_ssl=args.ssl,
        ssl_cert_file=args.cert,
        ssl_key_file=args.key,
    )
    server.start()

    try:
        # 保持程序运行
        print(f"认证SMTP服务器已启动: {args.host}:{args.port}")
        print(f"认证要求: {'启用' if args.auth else '禁用'}")
        print(f"SSL: {'启用' if args.ssl else '禁用'}")
        print("按Ctrl+C停止服务器")

        # 使用asyncio事件循环运行服务器
        loop = asyncio.get_event_loop()
        loop.run_forever()
    except KeyboardInterrupt:
        print("正在停止服务器...")
    finally:
        server.stop()
