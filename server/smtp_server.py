# -*- coding: utf-8 -*-
"""
稳定的SMTP服务器 - 专门解决连接稳定性问题
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
import socket
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
from server.new_db_handler import EmailService
from server.user_auth import UserAuth

# 设置日志
logger = setup_logging("stable_smtp_server")


class StableSMTPHandler:
    """稳定的SMTP处理器"""

    def __init__(self, db_handler: EmailService, server_instance):
        self.db_handler = db_handler
        self.server_instance = server_instance
        self.user_auth = UserAuth()
        self.authenticated_sessions = set()

        logger.info("稳定SMTP处理器已初始化")

    async def handle_DATA(self, server, session, envelope):
        """处理邮件数据"""
        try:
            # 如果需要认证但未认证，拒绝邮件
            if self.server_instance.require_auth and not getattr(
                session, "authenticated", False
            ):
                logger.warning(f"未认证用户尝试发送邮件: {session.peer}")
                return "530 Authentication required"

            # 获取邮件内容
            mail_from = envelope.mail_from
            rcpt_tos = envelope.rcpt_tos
            content = envelope.content

            # 解析邮件内容
            if isinstance(content, bytes):
                email_content = content.decode("utf-8", errors="replace")
            else:
                email_content = content

            # 处理邮件存储
            self._process_email(mail_from, rcpt_tos, email_content)

            logger.info(f"邮件处理完成: {mail_from} -> {rcpt_tos}")
            return "250 Message accepted for delivery"

        except Exception as e:
            logger.error(f"处理邮件时出错: {e}")
            return "451 Requested action aborted: error in processing"

    def _process_email(self, mail_from, rcpt_tos, email_content):
        """处理邮件存储"""
        try:
            # 解析邮件
            email_message = Parser(policy=policy.default).parsestr(email_content)

            # 提取或生成Message-ID（符合RFC 5322标准）
            message_id = email_message.get("Message-ID")
            if not message_id:
                # 使用标准的Message-ID生成函数
                from common.utils import generate_message_id

                message_id = generate_message_id("smtp.localhost")
                # 在邮件内容开头添加Message-ID头部
                email_content = f"Message-ID: {message_id}\r\n{email_content}"
                logger.info(f"SMTP服务器自动添加Message-ID: {message_id}")

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
                    pass

            # 提取日期
            try:
                date = email.utils.parsedate_to_datetime(email_message.get("Date"))
            except (TypeError, ValueError):
                date = datetime.datetime.now()

            # 使用新的EmailService统一接口保存邮件
            success = self.db_handler.save_email(
                message_id=message_id,
                from_addr=mail_from,
                to_addrs=rcpt_tos,
                subject=subject,
                content=email_content,
                date=date,
                is_spam=False,
                spam_score=0.0,
            )

            if not success:
                logger.error(f"邮件保存失败: {message_id}")
                raise Exception("邮件保存失败")

            logger.debug(f"邮件已保存: {message_id}")

        except Exception as e:
            logger.error(f"处理邮件存储时出错: {e}")
            raise


class StableSMTPServer:
    """稳定的SMTP服务器"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 465,  # 默认使用SSL端口
        db_handler: EmailService = None,
        require_auth: bool = True,
        use_ssl: bool = True,  # 默认启用SSL
        ssl_cert_file: str = SSL_CERT_FILE,
        ssl_key_file: str = SSL_KEY_FILE,
        max_connections: int = MAX_CONNECTIONS,
    ):
        self.host = host
        self.port = port
        self.db_handler = db_handler or EmailService()
        self.require_auth = require_auth
        self.use_ssl = use_ssl
        self.ssl_cert_file = ssl_cert_file
        self.ssl_key_file = ssl_key_file
        self.max_connections = max_connections

        # 创建处理器
        self.handler = StableSMTPHandler(self.db_handler, self)
        self.controller = None

        # 确保测试用户存在
        self._ensure_test_user_exists()

        # 创建SSL上下文
        self.ssl_context = None
        if self.use_ssl:
            self.ssl_context = self._create_ssl_context()

        logger.info(
            f"稳定SMTP服务器已初始化: {host}:{port}, "
            f"SSL: {'启用' if self.use_ssl else '禁用'}, "
            f"认证: {'启用' if require_auth else '禁用'}"
        )

    def _create_ssl_context(self):
        """创建SSL上下文"""
        try:
            # 确保证书文件存在
            if not os.path.exists(self.ssl_cert_file) or not os.path.exists(
                self.ssl_key_file
            ):
                self._create_self_signed_cert()

            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(
                certfile=self.ssl_cert_file, keyfile=self.ssl_key_file
            )

            # 设置SSL选项以提高兼容性
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.set_ciphers(
                "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
            )

            logger.info(f"SSL上下文已创建: {self.ssl_cert_file}")
            return context

        except Exception as e:
            logger.error(f"创建SSL上下文时出错: {e}")
            self.use_ssl = False
            return None

    def _create_self_signed_cert(self):
        """创建自签名证书"""
        try:
            # 确保证书目录存在
            cert_dir = os.path.dirname(self.ssl_cert_file)
            os.makedirs(cert_dir, exist_ok=True)

            # 使用Python的cryptography库创建证书
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            import datetime

            # 生成私钥
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )

            # 创建证书
            subject = issuer = x509.Name(
                [
                    x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                    x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Email Server"),
                    x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
                ]
            )

            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(private_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(datetime.datetime.utcnow())
                .not_valid_after(
                    datetime.datetime.utcnow() + datetime.timedelta(days=365)
                )
                .add_extension(
                    x509.SubjectAlternativeName(
                        [
                            x509.DNSName("localhost"),
                        ]
                    ),
                    critical=False,
                )
                .sign(private_key, hashes.SHA256())
            )

            # 保存私钥
            with open(self.ssl_key_file, "wb") as f:
                f.write(
                    private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )

            # 保存证书
            with open(self.ssl_cert_file, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))

            logger.info(f"自签名证书已创建: {self.ssl_cert_file}")

        except ImportError:
            logger.warning("cryptography库未安装，尝试使用OpenSSL命令")
            self._create_cert_with_openssl()
        except Exception as e:
            logger.error(f"创建自签名证书时出错: {e}")
            raise

    def _create_cert_with_openssl(self):
        """使用OpenSSL命令创建证书"""
        try:
            import subprocess

            cert_dir = os.path.dirname(self.ssl_cert_file)
            os.makedirs(cert_dir, exist_ok=True)

            cmd = [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:4096",
                "-keyout",
                self.ssl_key_file,
                "-out",
                self.ssl_cert_file,
                "-days",
                "365",
                "-nodes",
                "-subj",
                "/CN=localhost",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("使用OpenSSL创建证书成功")
            else:
                raise Exception(f"OpenSSL命令失败: {result.stderr}")

        except Exception as e:
            logger.error(f"使用OpenSSL创建证书时出错: {e}")
            raise

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

        try:
            # 测试端口是否可用
            self._test_port_availability()

            # 创建控制器
            self.controller = Controller(
                handler=self.handler,
                hostname=self.host,
                port=self.port,
                authenticator=self.auth_callback if self.require_auth else None,
                auth_require_tls=False,  # 允许非TLS认证以提高兼容性
                ssl_context=self.ssl_context,
                ready_timeout=30,
                enable_SMTPUTF8=True,
            )

            # 启动控制器
            self.controller.start()

            logger.info(f"稳定SMTP服务器已启动: {self.host}:{self.port}")

        except Exception as e:
            logger.error(f"启动SMTP服务器时出错: {e}")
            if self.controller:
                try:
                    self.controller.stop()
                except:
                    pass
            self.controller = None
            raise

    def _test_port_availability(self):
        """测试端口可用性"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.close()
            logger.info(f"端口 {self.port} 可用")
        except Exception as e:
            logger.error(f"端口 {self.port} 不可用: {e}")
            raise

    def stop(self) -> None:
        """停止SMTP服务器"""
        if self.controller:
            self.controller.stop()
            self.controller = None
            logger.info("稳定SMTP服务器已停止")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="稳定SMTP服务器")
    parser.add_argument("--host", default="localhost", help="服务器主机名")
    parser.add_argument("--port", type=int, default=465, help="服务器端口")
    parser.add_argument("--no-ssl", dest="ssl", action="store_false", help="禁用SSL")
    parser.add_argument("--no-auth", dest="auth", action="store_false", help="禁用认证")
    parser.set_defaults(ssl=True, auth=True)
    args = parser.parse_args()

    # 创建并启动服务器
    server = StableSMTPServer(
        host=args.host,
        port=args.port,
        require_auth=args.auth,
        use_ssl=args.ssl,
    )
    server.start()

    try:
        print(f"稳定SMTP服务器已启动: {args.host}:{args.port}")
        print(f"SSL: {'启用' if args.ssl else '禁用'}")
        print("按Ctrl+C停止服务器")

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("正在停止服务器...")
    finally:
        server.stop()
