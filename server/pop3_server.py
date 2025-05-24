# -*- coding: utf-8 -*-
"""
稳定的POP3服务器 - 专门解决连接稳定性问题
"""

import os
import sys
import ssl
import time
import socket
import threading
import socketserver
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.config import SSL_CERT_FILE, SSL_KEY_FILE
from server.new_db_handler import EmailService
from server.user_auth import UserAuth

# 设置日志
logger = setup_logging("stable_pop3_server")


class StablePOP3Handler(socketserver.StreamRequestHandler):
    """稳定的POP3处理器"""

    def __init__(self, request, client_address, server):
        self.db_handler = server.db_handler
        self.user_auth = server.user_auth
        self.authenticated_user = None
        self.use_ssl = server.use_ssl
        # 邮件列表缓存
        self.cached_emails = None
        self.cache_user_email = None
        super().__init__(request, client_address, server)

    def setup(self):
        """设置连接"""
        super().setup()
        if (
            self.use_ssl
            and hasattr(self.server, "ssl_context")
            and self.server.ssl_context
        ):
            try:
                # 设置socket超时，避免无限等待
                self.request.settimeout(30)

                # 包装SSL套接字
                self.request = self.server.ssl_context.wrap_socket(
                    self.request,
                    server_side=True,
                    do_handshake_on_connect=False,  # 手动控制握手
                )

                # 执行SSL握手
                self.request.do_handshake()

                # 重新创建文件对象以确保SSL正常工作
                self.rfile = self.request.makefile("rb", -1)
                self.wfile = self.request.makefile("wb", 0)

                logger.debug(f"SSL连接已建立: {self.client_address}")
            except ssl.SSLError as e:
                logger.warning(f"SSL握手失败，客户端可能不支持SSL: {e}")
                # 关闭连接，让客户端重新以非SSL方式连接
                try:
                    self.request.close()
                except:
                    pass
                raise
            except Exception as e:
                logger.error(f"SSL连接设置失败: {e}")
                import traceback

                logger.error(f"SSL握手详细错误: {traceback.format_exc()}")
                try:
                    self.request.close()
                except:
                    pass
                raise

    def handle(self):
        """处理POP3连接"""
        try:
            logger.info(f"新的POP3连接: {self.client_address}")

            # 发送欢迎消息
            self.send_response("+OK POP3 server ready")

            while True:
                try:
                    # 读取命令
                    line = (
                        self.rfile.readline().decode("utf-8", errors="replace").strip()
                    )
                    if not line:
                        break

                    logger.debug(f"收到命令: {line}")

                    # 解析命令
                    parts = line.split(" ", 1)
                    command = parts[0].upper()
                    args = parts[1] if len(parts) > 1 else ""

                    # 处理命令
                    if command == "USER":
                        self.handle_user(args)
                    elif command == "PASS":
                        self.handle_pass(args)
                    elif command == "STAT":
                        self.handle_stat()
                    elif command == "LIST":
                        self.handle_list(args)
                    elif command == "RETR":
                        self.handle_retr(args)
                    elif command == "DELE":
                        self.handle_dele(args)
                    elif command == "NOOP":
                        self.handle_noop()
                    elif command == "RSET":
                        self.handle_rset()
                    elif command == "QUIT":
                        self.handle_quit()
                        break
                    else:
                        self.send_response(f"-ERR Unknown command: {command}")

                except Exception as e:
                    logger.error(f"处理命令时出错: {e}")
                    self.send_response("-ERR Internal server error")
                    break

        except Exception as e:
            logger.error(f"处理连接时出错: {e}")
        finally:
            logger.info(f"POP3连接关闭: {self.client_address}")

    def send_response(self, response):
        """发送响应"""
        try:
            self.wfile.write(f"{response}\r\n".encode("utf-8"))
            self.wfile.flush()
            logger.debug(f"发送响应: {response}")
        except Exception as e:
            logger.error(f"发送响应时出错: {e}")

    def get_user_emails(self):
        """获取用户邮件列表（带缓存）"""
        if not self.authenticated_user:
            logger.warning("get_user_emails: 用户未认证")
            return []

        user_email = self.authenticated_user.email
        logger.debug(f"get_user_emails: 查询用户 {user_email} 的邮件")

        # 检查缓存是否有效
        if self.cached_emails is not None and self.cache_user_email == user_email:
            logger.debug(f"get_user_emails: 使用缓存，{len(self.cached_emails)} 封邮件")
            return self.cached_emails

        # 重新查询并缓存
        try:
            logger.debug(f"get_user_emails: 从数据库查询邮件")
            emails = self.db_handler.list_emails(
                user_email=user_email, include_deleted=False, include_spam=False
            )
            self.cached_emails = emails
            self.cache_user_email = user_email
            logger.debug(
                f"get_user_emails: 缓存用户 {user_email} 的 {len(emails)} 封邮件"
            )
            return emails
        except Exception as e:
            logger.error(f"get_user_emails: 获取用户邮件时出错: {e}")
            import traceback

            logger.error(f"get_user_emails: 详细错误信息: {traceback.format_exc()}")
            return []

    def invalidate_cache(self):
        """清除邮件列表缓存"""
        self.cached_emails = None
        self.cache_user_email = None

    def handle_user(self, username):
        """处理USER命令"""
        self.username = username
        self.send_response(f"+OK User {username} accepted")

    def handle_pass(self, password):
        """处理PASS命令"""
        if not hasattr(self, "username"):
            self.send_response("-ERR USER command must come first")
            return

        try:
            user = self.user_auth.authenticate(self.username, password)
            if user:
                self.authenticated_user = user
                self.send_response(f"+OK User {self.username} authenticated")
                logger.info(f"用户认证成功: {self.username}")
            else:
                self.send_response("-ERR Authentication failed")
                logger.warning(f"用户认证失败: {self.username}")
        except Exception as e:
            logger.error(f"认证过程中出错: {e}")
            self.send_response("-ERR Authentication error")

    def handle_stat(self):
        """处理STAT命令"""
        if not self.authenticated_user:
            logger.warning("STAT命令: 用户未认证")
            self.send_response("-ERR Not authenticated")
            return

        try:
            logger.debug(f"STAT命令: 开始处理，用户 {self.authenticated_user.email}")

            # 使用缓存的邮件列表
            emails = self.get_user_emails()
            logger.debug(f"STAT命令: 获取到 {len(emails)} 封邮件")

            total_size = sum(email.get("size", 0) for email in emails)
            logger.debug(f"STAT命令: 计算总大小 {total_size} 字节")

            response = f"+OK {len(emails)} {total_size}"
            self.send_response(response)
            logger.info(
                f"STAT命令成功: 用户 {self.authenticated_user.email} 有 {len(emails)} 封邮件，总大小 {total_size} 字节"
            )

        except Exception as e:
            logger.error(f"处理STAT命令时出错: {e}")
            import traceback

            logger.error(f"详细错误信息: {traceback.format_exc()}")
            self.send_response("-ERR Internal server error")

    def handle_list(self, args):
        """处理LIST命令"""
        if not self.authenticated_user:
            self.send_response("-ERR Not authenticated")
            return

        try:
            # 使用缓存的邮件列表
            emails = self.get_user_emails()

            if args:  # LIST specific message
                try:
                    msg_num = int(args)
                    if 1 <= msg_num <= len(emails):
                        email = emails[msg_num - 1]
                        size = email.get("size", 0)
                        self.send_response(f"+OK {msg_num} {size}")
                    else:
                        self.send_response("-ERR No such message")
                except ValueError:
                    self.send_response("-ERR Invalid message number")
            else:  # LIST all messages
                self.send_response(f"+OK {len(emails)} messages")
                for i, email in enumerate(emails, 1):
                    size = email.get("size", 0)
                    self.send_response(f"{i} {size}")
                self.send_response(".")

        except Exception as e:
            logger.error(f"处理LIST命令时出错: {e}")
            self.send_response("-ERR Internal server error")

    def handle_retr(self, args):
        """处理RETR命令"""
        if not self.authenticated_user:
            self.send_response("-ERR Not authenticated")
            return

        try:
            msg_num = int(args)
            # 使用缓存的邮件列表
            emails = self.get_user_emails()

            if 1 <= msg_num <= len(emails):
                email = emails[msg_num - 1]
                content = self.db_handler.get_email_content(email["message_id"])
                if content:
                    # 计算内容大小（字节）
                    content_bytes = content.encode("utf-8")
                    content_size = len(content_bytes)

                    self.send_response(f"+OK {content_size} octets")

                    # 按POP3协议要求逐行发送内容
                    # 确保内容格式正确，统一换行符为CRLF
                    content = (
                        content.replace("\r\n", "\n")
                        .replace("\r", "\n")
                        .replace("\n", "\r\n")
                    )

                    # 逐行发送邮件内容
                    for line in content.split("\r\n"):
                        # 处理行开头的点（透明性规则）
                        if line.startswith("."):
                            line = "." + line
                        self.send_response(line)

                    # 发送结束标记
                    self.send_response(".")
                    logger.debug(
                        f"RETR命令: 返回邮件 {msg_num} 内容，大小 {content_size} 字节"
                    )
                else:
                    self.send_response("-ERR Message content not found")
                    logger.warning(f"RETR命令: 邮件 {msg_num} 内容未找到")
            else:
                self.send_response("-ERR No such message")
                logger.warning(
                    f"RETR命令: 邮件编号 {msg_num} 超出范围 (1-{len(emails)})"
                )

        except ValueError:
            self.send_response("-ERR Invalid message number")
        except Exception as e:
            logger.error(f"处理RETR命令时出错: {e}")
            self.send_response("-ERR Internal server error")

    def handle_dele(self, args):
        """处理DELE命令"""
        if not self.authenticated_user:
            self.send_response("-ERR Not authenticated")
            return

        try:
            msg_num = int(args)
            # 使用缓存的邮件列表
            emails = self.get_user_emails()

            if 1 <= msg_num <= len(emails):
                email = emails[msg_num - 1]
                # 实际标记邮件为删除
                success = self.db_handler.mark_email_as_deleted(email["message_id"])
                if success:
                    # 清除缓存，因为邮件状态已改变
                    self.invalidate_cache()
                    self.send_response(f"+OK Message {msg_num} deleted")
                    logger.debug(f"DELE命令: 标记邮件 {msg_num} 为删除")
                else:
                    self.send_response("-ERR Failed to delete message")
                    logger.error(f"DELE命令: 删除邮件 {msg_num} 失败")
            else:
                self.send_response("-ERR No such message")
                logger.warning(
                    f"DELE命令: 邮件编号 {msg_num} 超出范围 (1-{len(emails)})"
                )

        except ValueError:
            self.send_response("-ERR Invalid message number")
        except Exception as e:
            logger.error(f"处理DELE命令时出错: {e}")
            self.send_response("-ERR Internal server error")

    def handle_noop(self):
        """处理NOOP命令"""
        self.send_response("+OK")

    def handle_rset(self):
        """处理RSET命令"""
        self.send_response("+OK")

    def handle_quit(self):
        """处理QUIT命令"""
        self.send_response("+OK POP3 server signing off")


class StablePOP3Server:
    """稳定的POP3服务器"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 995,  # 默认使用SSL端口
        use_ssl: bool = True,  # 默认启用SSL
        ssl_cert_file: str = SSL_CERT_FILE,
        ssl_key_file: str = SSL_KEY_FILE,
        max_connections: int = 10,
    ):
        self.host = host
        self.port = port
        self.ssl_cert_file = ssl_cert_file
        self.ssl_key_file = ssl_key_file
        self.max_connections = max_connections

        # 初始化数据库和认证
        self.db_handler = EmailService()
        self.user_auth = UserAuth()

        # 创建SSL上下文
        self.ssl_context = None
        self.use_ssl = use_ssl  # 设置初始SSL状态

        if use_ssl:
            self.ssl_context = self._create_ssl_context()
            if self.ssl_context is None:
                # SSL上下文创建失败，禁用SSL
                self.use_ssl = False
                logger.warning("SSL上下文创建失败，已自动禁用SSL功能")

        # 服务器实例
        self.server = None
        self.server_thread = None

        ssl_status = "启用" if self.use_ssl else "禁用"
        logger.info(f"稳定POP3服务器已初始化: {host}:{port}, SSL: {ssl_status}")

        # 如果请求的是SSL但实际禁用了，给出提示
        if use_ssl and not self.use_ssl:
            logger.warning(
                "注意: 请求启用SSL但由于配置问题已被禁用，服务器将以非SSL模式运行"
            )

    def _create_ssl_context(self):
        """创建SSL上下文"""
        try:
            # 确保证书文件存在
            if not os.path.exists(self.ssl_cert_file) or not os.path.exists(
                self.ssl_key_file
            ):
                logger.warning("SSL证书文件不存在，尝试创建...")
                try:
                    self._create_self_signed_cert()
                except Exception as cert_error:
                    logger.error(f"无法创建SSL证书: {cert_error}")
                    logger.info("将禁用SSL功能")
                    return None

            # 创建SSL上下文
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

            # 加载证书链
            context.load_cert_chain(
                certfile=self.ssl_cert_file, keyfile=self.ssl_key_file
            )

            # 设置SSL选项以提高兼容性和安全性
            context.minimum_version = ssl.TLSVersion.TLSv1_2

            # 设置密码套件，提高兼容性
            try:
                context.set_ciphers(
                    "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
                )
            except ssl.SSLError:
                # 如果自定义密码套件失败，使用默认的
                logger.warning("无法设置自定义密码套件，使用默认配置")

            # 不要求客户端证书
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            logger.info(f"SSL上下文已创建: {self.ssl_cert_file}")
            return context

        except Exception as e:
            logger.error(f"创建SSL上下文时出错: {e}")
            import traceback

            logger.error(f"SSL上下文创建详细错误: {traceback.format_exc()}")
            logger.info("将禁用SSL功能")
            return None

    def _create_self_signed_cert(self):
        """创建自签名证书"""
        try:
            # 确保证书目录存在
            cert_dir = os.path.dirname(self.ssl_cert_file)
            os.makedirs(cert_dir, exist_ok=True)

            logger.info("正在生成自签名证书...")

            # 尝试使用OpenSSL命令生成证书
            import subprocess

            cmd = [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-keyout",
                self.ssl_key_file,
                "-out",
                self.ssl_cert_file,
                "-days",
                "365",
                "-nodes",
                "-subj",
                "/C=CN/ST=Beijing/L=Beijing/O=Test/OU=IT/CN=localhost",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=cert_dir)
            if result.returncode == 0:
                logger.info(f"使用OpenSSL创建证书成功: {self.ssl_cert_file}")
                return
            else:
                logger.warning(f"OpenSSL命令失败: {result.stderr}")
                self._create_cert_with_python()

        except FileNotFoundError:
            logger.warning("OpenSSL命令未找到，尝试使用Python生成证书...")
            self._create_cert_with_python()
        except Exception as e:
            logger.error(f"使用OpenSSL创建证书时出错: {e}")
            self._create_cert_with_python()

    def _create_cert_with_python(self):
        """使用Python cryptography库生成自签名证书"""
        try:
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.primitives import serialization
            import datetime
            import ipaddress

            logger.info("使用Python cryptography库生成证书...")

            # 生成私钥
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )

            # 创建证书主题
            subject = issuer = x509.Name(
                [
                    x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
                    x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
                    x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Organization"),
                    x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
                ]
            )

            # 创建证书
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
                            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                        ]
                    ),
                    critical=False,
                )
                .sign(private_key, hashes.SHA256())
            )

            # 确保证书目录存在
            cert_dir = os.path.dirname(self.ssl_cert_file)
            os.makedirs(cert_dir, exist_ok=True)

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

            logger.info(f"使用Python生成证书成功: {self.ssl_cert_file}")

        except ImportError:
            logger.error("cryptography库未安装，无法生成SSL证书")
            logger.error("请安装: pip install cryptography")
            logger.error("或手动生成证书:")
            logger.error(
                f"  openssl req -x509 -newkey rsa:2048 -keyout {self.ssl_key_file} -out {self.ssl_cert_file} -days 365 -nodes -subj '/CN=localhost'"
            )
            raise Exception("无法生成SSL证书")
        except Exception as e:
            logger.error(f"使用Python生成SSL证书时出错: {e}")
            raise

    def start(self):
        """启动POP3服务器"""
        try:
            # 创建服务器
            class ThreadedTCPServer(
                socketserver.ThreadingMixIn, socketserver.TCPServer
            ):
                allow_reuse_address = True
                daemon_threads = True

                def __init__(
                    self,
                    server_address,
                    RequestHandlerClass,
                    db_handler,
                    user_auth,
                    use_ssl,
                    ssl_context,
                ):
                    self.db_handler = db_handler
                    self.user_auth = user_auth
                    self.use_ssl = use_ssl
                    self.ssl_context = ssl_context
                    super().__init__(server_address, RequestHandlerClass)

            self.server = ThreadedTCPServer(
                (self.host, self.port),
                StablePOP3Handler,
                self.db_handler,
                self.user_auth,
                self.use_ssl,
                self.ssl_context,
            )

            # 在单独线程中启动服务器
            self.server_thread = threading.Thread(
                target=self.server.serve_forever, daemon=True
            )
            self.server_thread.start()

            logger.info(f"稳定POP3服务器已启动: {self.host}:{self.port}")

        except Exception as e:
            logger.error(f"启动POP3服务器时出错: {e}")
            raise

    def stop(self):
        """停止POP3服务器"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None

        if self.server_thread:
            self.server_thread.join(timeout=5)
            self.server_thread = None

        logger.info("稳定POP3服务器已停止")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="稳定POP3服务器")
    parser.add_argument("--host", default="localhost", help="服务器主机名")
    parser.add_argument("--port", type=int, default=995, help="服务器端口")
    parser.add_argument("--no-ssl", dest="ssl", action="store_false", help="禁用SSL")
    parser.set_defaults(ssl=True)
    args = parser.parse_args()

    # 创建并启动服务器
    server = StablePOP3Server(
        host=args.host,
        port=args.port,
        use_ssl=args.ssl,
    )
    server.start()

    try:
        print(f"稳定POP3服务器已启动: {args.host}:{args.port}")
        print(f"SSL: {'启用' if args.ssl else '禁用'}")
        print("按Ctrl+C停止服务器")

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("正在停止服务器...")
    finally:
        server.stop()
