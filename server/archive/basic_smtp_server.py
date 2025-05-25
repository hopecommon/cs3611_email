"""
基础SMTP服务器模块 - 使用aiosmtpd实现基本的SMTP服务
"""

import os
import sys
import socket
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP, Session, Envelope, AuthResult, LoginPassword
import datetime
import uuid
import email
from email import policy
from email.parser import Parser

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.config import AUTH_REQUIRED, EMAIL_STORAGE_DIR
from server.new_db_handler import DatabaseHandler

from server.user_auth import UserAuth

# 设置日志
logger = setup_logging("basic_smtp_server")


def is_port_available(host: str, port: int) -> bool:
    """
    检查指定的端口是否可用

    Args:
        host: 主机名或IP地址
        port: 端口号

    Returns:
        如果端口可用，返回True；否则返回False
    """
    try:
        # 创建套接字
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # 设置超时时间
            s.settimeout(1)
            # 尝试绑定端口
            s.bind((host, port))
            # 如果能绑定成功，说明端口可用
            return True
    except Exception as e:
        # 如果绑定失败，说明端口不可用
        logger.debug(f"端口 {port} 不可用: {e}")
        return False


def find_available_port(host: str, start_port: int, max_attempts: int = 10) -> int:
    """
    查找可用端口

    Args:
        host: 主机名或IP地址
        start_port: 起始端口号
        max_attempts: 最大尝试次数

    Returns:
        可用的端口号，如果找不到则返回-1
    """
    port = start_port
    for _ in range(max_attempts):
        if is_port_available(host, port):
            return port
        port += 1
    return -1


class BasicSMTPHandler:
    """基础SMTP处理程序，处理SMTP命令和邮件接收"""

    def __init__(self, db_handler: DatabaseHandler = None, server=None):
        """
        初始化SMTP处理程序

        Args:
            db_handler: 数据库处理器，如果为None则创建一个新的
            server: SMTP服务器实例，用于访问服务器配置
        """
        self.db_handler = db_handler or DatabaseHandler()
        self.user_auth = UserAuth()
        self._server = server  # 保存服务器引用，用于访问配置

        # 认证状态
        self.authenticated_sessions = set()

        logger.info("SMTP处理程序已初始化")

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
            # 生成唯一的消息ID
            message_id = f"<{uuid.uuid4()}@example.com>"

            # 解析邮件内容
            if isinstance(content, bytes):
                email_content = content.decode("utf-8", errors="replace")
            else:
                email_content = content  # 如果已经是字符串，直接使用

            email_message = Parser(policy=policy.default).parsestr(email_content)

            # 提取主题
            subject = email_message.get("Subject", "")

            # 提取日期（如果邮件头中有指定）
            try:
                date = email.utils.parsedate_to_datetime(email_message.get("Date"))
            except (TypeError, ValueError):
                date = datetime.datetime.now()

            # 记录解析结果
            logger.info(f"解析邮件: 主题='{subject}'")

            # 保存邮件内容
            self.db_handler.save_email_content(message_id, email_content)

            # 保存邮件元数据
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

            logger.info(f"邮件已保存到数据库")
            return "250 Message accepted for delivery"
        except Exception as e:
            logger.error(f"保存邮件时出错: {e}")
            return "451 Requested action aborted: error in processing"


class BasicSMTPServer:
    """基础SMTP服务器类，使用aiosmtpd实现"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8025,
        db_handler: DatabaseHandler = None,
        require_auth: bool = AUTH_REQUIRED,
    ):
        """
        初始化SMTP服务器

        Args:
            host: 服务器主机名或IP地址。如果是域名，将尝试解析为IP地址；
                 如果解析失败，将回退到localhost
            port: 服务器端口
            db_handler: 数据库处理器，如果为None则创建一个新的
            require_auth: 是否要求认证
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
        self.db_handler = db_handler or DatabaseHandler()
        self.require_auth = require_auth
        # 将服务器实例传递给处理程序
        self.handler = BasicSMTPHandler(self.db_handler, self)
        self.controller = None

        logger.info(
            f"SMTP服务器已初始化: {host}:{port}, 认证要求: {'启用' if require_auth else '禁用'}"
        )

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
        if mechanism == "PLAIN":
            try:
                # PLAIN认证格式: \0username\0password
                identity, username, password = auth_data.decode().split("\0")
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
                logger.error(f"认证过程中出错: {e}")
                return AuthResult(success=False, message="Authentication error")
        elif mechanism == "LOGIN":
            try:
                # LOGIN认证格式: 两步交互，第一步是用户名，第二步是密码
                if isinstance(auth_data, LoginPassword):
                    username = auth_data.login.decode()
                    password = auth_data.password.decode()
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
                else:
                    logger.error(f"不支持的LOGIN认证数据格式: {type(auth_data)}")
                    return AuthResult(success=False, message="Unsupported LOGIN format")
            except Exception as e:
                logger.error(f"LOGIN认证过程中出错: {e}")
                return AuthResult(success=False, message="Authentication error")
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

        # 检查端口是否可用
        if not is_port_available(self.host, self.port):
            # 端口不可用，尝试查找其他可用端口
            logger.warning(f"端口 {self.port} 已被占用，尝试查找其他可用端口")
            new_port = find_available_port(self.host, self.port + 1)
            if new_port > 0:
                logger.info(f"找到可用端口: {new_port}，将使用此端口")
                self.port = new_port
            else:
                logger.error(f"无法找到可用端口，请手动指定其他端口")
                raise RuntimeError(f"端口 {self.port} 已被占用，且无法找到其他可用端口")

        try:
            # 创建控制器
            self.controller = Controller(
                handler=self.handler,
                hostname=self.host,
                port=self.port,
                authenticator=self.auth_callback if self.require_auth else None,
                auth_require_tls=False,  # 在生产环境中应设置为True
            )

            # 启动控制器
            self.controller.start()

            logger.info(f"SMTP服务器已启动: {self.host}:{self.port}")
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
            logger.info("SMTP服务器已停止")


if __name__ == "__main__":
    # 从命令行参数获取主机名和端口
    import argparse

    parser = argparse.ArgumentParser(description="基础SMTP服务器")
    parser.add_argument("--host", default="localhost", help="服务器主机名")
    parser.add_argument("--port", type=int, default=8025, help="服务器端口")
    parser.add_argument("--auth", action="store_true", help="启用认证")
    parser.add_argument("--no-auth", dest="auth", action="store_false", help="禁用认证")
    parser.set_defaults(auth=AUTH_REQUIRED)
    args = parser.parse_args()

    # 创建并启动服务器
    server = BasicSMTPServer(host=args.host, port=args.port, require_auth=args.auth)
    server.start()

    try:
        # 保持程序运行
        print(f"SMTP服务器已启动: {args.host}:{args.port}")
        print(f"认证要求: {'启用' if args.auth else '禁用'}")
        print("按Ctrl+C停止服务器")

        # 使用asyncio事件循环运行服务器
        loop = asyncio.get_event_loop()
        loop.run_forever()
    except KeyboardInterrupt:
        print("正在停止服务器...")
    finally:
        server.stop()
