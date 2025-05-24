"""
优化的SMTP服务器 - 专门用于高并发处理
"""

import os
import sys
import ssl
import time
import uuid
import email
import email.utils
import datetime
import asyncio
import threading
from pathlib import Path
from email.parser import Parser
from email import policy
from email.header import decode_header
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import SMTP as SMTPServer, LoginPassword
from aiosmtpd.smtp import AuthResult

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.config import (
    SSL_CERT_FILE,
    SSL_KEY_FILE,
    AUTH_REQUIRED,
    MAX_CONNECTIONS,
    CONNECTION_TIMEOUT,
)
from common.port_config import resolve_port
from server.optimized_db_handler import OptimizedDatabaseHandler
from server.user_auth import UserAuth

# 设置日志
logger = setup_logging("optimized_smtp_server")


class OptimizedSMTPHandler:
    """优化的SMTP处理器，专注于高并发性能"""

    def __init__(self, db_handler: OptimizedDatabaseHandler, server_instance):
        self.db_handler = db_handler
        self.server_instance = server_instance
        self.user_auth = UserAuth()
        self.authenticated_sessions = set()

        # 性能统计
        self.stats = {
            "total_emails": 0,
            "successful_emails": 0,
            "failed_emails": 0,
            "start_time": time.time(),
            "processing_times": [],
        }

        logger.info("优化SMTP处理器已初始化")

    async def handle_DATA(self, server, session, envelope):
        """处理邮件数据，优化版本"""
        start_time = time.time()

        try:
            # 更新统计
            self.stats["total_emails"] += 1

            # 如果需要认证但未认证，拒绝邮件
            if self.server_instance.require_auth and not getattr(
                session, "authenticated", False
            ):
                logger.warning(f"未认证用户尝试发送邮件: {session.peer}")
                self.stats["failed_emails"] += 1
                return "530 Authentication required"

            # 获取邮件内容
            mail_from = envelope.mail_from
            rcpt_tos = envelope.rcpt_tos
            content = envelope.content

            # 快速解析邮件内容
            if isinstance(content, bytes):
                email_content = content.decode("utf-8", errors="replace")
            else:
                email_content = content

            # 使用异步方式处理邮件存储
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._process_email_sync, mail_from, rcpt_tos, email_content
            )

            # 记录处理时间
            processing_time = time.time() - start_time
            self.stats["processing_times"].append(processing_time)
            self.stats["successful_emails"] += 1

            logger.debug(f"邮件处理完成，耗时: {processing_time:.3f}秒")
            return "250 Message accepted for delivery"

        except Exception as e:
            processing_time = time.time() - start_time
            self.stats["failed_emails"] += 1
            logger.error(f"处理邮件时出错 (耗时: {processing_time:.3f}秒): {e}")
            return "451 Requested action aborted: error in processing"

    def _process_email_sync(self, mail_from, rcpt_tos, email_content):
        """同步处理邮件存储（在线程池中执行）"""
        try:
            # 解析邮件
            email_message = Parser(policy=policy.default).parsestr(email_content)

            # 提取或生成Message-ID
            message_id = email_message.get("Message-ID")
            if not message_id:
                message_id = f"<{uuid.uuid4()}@example.com>"
                email_content = f"Message-ID: {message_id}\r\n{email_content}"

            # 提取主题
            subject = email_message.get("Subject", "")
            if subject:
                try:
                    decoded_subject = decode_header(subject)
                    if decoded_subject[0][1]:
                        subject = decoded_subject[0][0].decode(decoded_subject[0][1])
                    elif isinstance(decoded_subject[0][0], bytes):
                        subject = decoded_subject[0][0].decode(
                            "utf-8", errors="replace"
                        )
                except Exception:
                    pass  # 保持原始主题

            # 提取日期
            try:
                date = email.utils.parsedate_to_datetime(email_message.get("Date"))
            except (TypeError, ValueError):
                date = datetime.datetime.now()

            # 异步保存邮件内容和元数据到队列
            self.db_handler.save_email_content(message_id, email_content)
            self.db_handler.save_email_metadata(
                message_id=message_id,
                from_addr=mail_from,
                to_addrs=rcpt_tos,
                subject=subject,
                date=date,
                size=len(email_content),
                is_spam=False,
                spam_score=0.0,
            )

            logger.debug(f"邮件已保存: {message_id}")

        except Exception as e:
            logger.error(f"同步处理邮件时出错: {e}")
            raise

    def get_stats(self):
        """获取性能统计"""
        current_time = time.time()
        uptime = current_time - self.stats["start_time"]

        avg_processing_time = 0
        if self.stats["processing_times"]:
            avg_processing_time = sum(self.stats["processing_times"]) / len(
                self.stats["processing_times"]
            )

        return {
            "uptime": uptime,
            "total_emails": self.stats["total_emails"],
            "successful_emails": self.stats["successful_emails"],
            "failed_emails": self.stats["failed_emails"],
            "success_rate": self.stats["successful_emails"]
            / max(1, self.stats["total_emails"])
            * 100,
            "emails_per_second": self.stats["total_emails"] / max(1, uptime),
            "avg_processing_time": avg_processing_time,
        }


class OptimizedSMTPServer:
    """优化的SMTP服务器，支持高并发"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8025,
        db_handler: OptimizedDatabaseHandler = None,
        require_auth: bool = True,
        use_ssl: bool = False,
        ssl_cert_file: str = SSL_CERT_FILE,
        ssl_key_file: str = SSL_KEY_FILE,
        max_connections: int = MAX_CONNECTIONS,
    ):
        self.host = host
        self.port = port
        self.db_handler = db_handler or OptimizedDatabaseHandler()
        self.require_auth = require_auth
        self.use_ssl = use_ssl
        self.ssl_cert_file = ssl_cert_file
        self.ssl_key_file = ssl_key_file
        self.max_connections = max_connections

        # 创建处理器
        self.handler = OptimizedSMTPHandler(self.db_handler, self)
        self.controller = None

        # 确保测试用户存在
        self._ensure_test_user_exists()

        # 创建SSL上下文
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
            f"优化SMTP服务器已初始化: {host}:{port}, "
            f"最大连接数: {max_connections}, "
            f"认证: {'启用' if require_auth else '禁用'}, "
            f"SSL: {'启用' if self.use_ssl else '禁用'}"
        )

    def _ensure_test_user_exists(self):
        """确保测试用户存在"""
        try:
            test_username = "testuser"
            test_password = "testpass"

            user = self.handler.user_auth.get_user_by_username(test_username)
            if not user:
                self.handler.user_auth.add_user(test_username, test_password)
                logger.info(f"已创建测试用户: {test_username}")
        except Exception as e:
            logger.error(f"创建测试用户时出错: {e}")

    def auth_callback(self, server, session, envelope, mechanism, auth_data):
        """认证回调函数"""
        if mechanism == "PLAIN":
            try:
                if isinstance(auth_data, LoginPassword):
                    username = auth_data.login.decode("utf-8", errors="replace")
                    password = auth_data.password.decode("utf-8", errors="replace")
                else:
                    auth_str = auth_data.decode("utf-8", errors="replace")
                    parts = auth_str.split("\0")
                    if len(parts) == 3:
                        _, username, password = parts
                    elif len(parts) == 2:
                        username, password = parts
                    else:
                        return AuthResult(
                            success=False, message="Invalid authentication format"
                        )

                user = self.handler.user_auth.authenticate(username, password)
                if user:
                    session.authenticated = True
                    self.handler.authenticated_sessions.add(session)
                    return AuthResult(success=True, message="Authentication successful")
                else:
                    return AuthResult(success=False, message="Authentication failed")
            except Exception as e:
                logger.error(f"认证过程中出错: {e}")
                return AuthResult(
                    success=False, message=f"Authentication error: {str(e)}"
                )

        return AuthResult(
            success=False, message=f"Unsupported authentication mechanism: {mechanism}"
        )

    def start(self) -> None:
        """启动SMTP服务器"""
        if self.controller:
            logger.warning("SMTP服务器已经在运行")
            return

        # 端口管理
        port, changed, message = resolve_port(
            "smtp", self.port, self.use_ssl, auto_detect=True
        )

        if port == 0:
            logger.error(message)
            raise RuntimeError(message)

        if changed:
            logger.warning(message)
            self.port = port

        try:
            # 创建控制器，优化配置
            self.controller = Controller(
                handler=self.handler,
                hostname=self.host,
                port=self.port,
                authenticator=self.auth_callback if self.require_auth else None,
                auth_require_tls=False,
                ssl_context=self.ssl_context,
                # 优化配置
                ready_timeout=30,
                enable_SMTPUTF8=True,
            )

            # 启动控制器
            self.controller.start()

            logger.info(f"优化SMTP服务器已启动: {self.host}:{self.port}")
            logger.info(f"最大连接数: {self.max_connections}")

        except Exception as e:
            logger.error(f"启动SMTP服务器时出错: {e}")
            if self.controller:
                try:
                    self.controller.stop()
                except:
                    pass
            self.controller = None
            raise

    def stop(self) -> None:
        """停止SMTP服务器"""
        if self.controller:
            self.controller.stop()
            self.controller = None
            logger.info("优化SMTP服务器已停止")

    def get_stats(self):
        """获取服务器统计信息"""
        return self.handler.get_stats()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="优化SMTP服务器")
    parser.add_argument("--host", default="localhost", help="服务器主机名")
    parser.add_argument("--port", type=int, default=8025, help="服务器端口")
    parser.add_argument(
        "--max-connections", type=int, default=MAX_CONNECTIONS, help="最大连接数"
    )
    parser.add_argument("--auth", action="store_true", help="启用认证")
    parser.add_argument("--no-auth", dest="auth", action="store_false", help="禁用认证")
    parser.add_argument("--ssl", action="store_true", help="启用SSL")
    parser.add_argument("--no-ssl", dest="ssl", action="store_false", help="禁用SSL")
    parser.set_defaults(auth=True, ssl=False)
    args = parser.parse_args()

    # 创建并启动服务器
    server = OptimizedSMTPServer(
        host=args.host,
        port=args.port,
        require_auth=args.auth,
        use_ssl=args.ssl,
        max_connections=args.max_connections,
    )
    server.start()

    try:
        print(f"优化SMTP服务器已启动: {args.host}:{server.port}")
        print(f"最大连接数: {args.max_connections}")
        print("按Ctrl+C停止服务器")

        # 定期打印统计信息
        import time

        while True:
            time.sleep(10)
            stats = server.get_stats()
            print(
                f"统计: 总邮件={stats['total_emails']}, "
                f"成功={stats['successful_emails']}, "
                f"成功率={stats['success_rate']:.1f}%, "
                f"速度={stats['emails_per_second']:.2f}封/秒"
            )
    except KeyboardInterrupt:
        print("正在停止服务器...")
    finally:
        server.stop()
