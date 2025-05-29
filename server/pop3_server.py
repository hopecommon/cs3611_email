# -*- coding: utf-8 -*-
"""
稳定的POP3服务器 - 专门解决连接稳定性问题
增强Windows兼容性和错误恢复机制
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
from common.config import (
    SSL_CERT_FILE,
    SSL_KEY_FILE,
    MAX_CONNECTIONS,
    POP3_REQUEST_QUEUE_SIZE,
)
from server.new_db_handler import EmailService
from server.user_auth import UserAuth

# 设置日志
logger = setup_logging("stable_pop3_server")


class StablePOP3Handler(socketserver.StreamRequestHandler):
    """稳定的POP3处理器 - 增强Windows兼容性"""

    def __init__(self, request, client_address, server):
        self.email_service = server.email_service  # 改用email_service
        self.user_auth = server.user_auth
        self.authenticated_user = None
        self.use_ssl = server.use_ssl
        # 邮件列表缓存
        self.cached_emails = None
        self.cache_user_email = None
        # 添加连接统计
        self.connection_start_time = time.time()
        self.connection_active = True
        # Windows兼容性增强
        self.last_activity = time.time()
        super().__init__(request, client_address, server)

    def setup(self):
        """设置连接 - 增强Windows兼容性"""
        try:
            super().setup()

            # 设置socket选项以提高Windows兼容性
            if hasattr(self.request, "setsockopt"):
                # 设置TCP_NODELAY以减少延迟
                self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                # 设置SO_KEEPALIVE以检测断开的连接
                self.request.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                # Windows特定的keepalive设置
                if hasattr(socket, "SIO_KEEPALIVE_VALS"):
                    try:
                        # 启用keepalive，30秒间隔，3次重试
                        keepalive_vals = (1, 30000, 5000)  # 启用, 30秒, 5秒间隔
                        self.request.ioctl(socket.SIO_KEEPALIVE_VALS, keepalive_vals)
                    except:
                        pass

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
                    self._safe_close_connection()
                    raise
                except Exception as e:
                    logger.error(f"SSL连接设置失败: {e}")
                    import traceback

                    logger.error(f"SSL握手详细错误: {traceback.format_exc()}")
                    self._safe_close_connection()
                    raise
        except Exception as e:
            logger.debug(f"连接setup失败 (可能是客户端提前断开): {e}")
            self.connection_active = False
            raise

    def _safe_close_connection(self):
        """安全关闭连接"""
        try:
            if hasattr(self.request, "close"):
                self.request.close()
        except:
            pass

    def _is_connection_alive(self):
        """检查连接是否仍然活跃"""
        if not self.connection_active:
            return False

        try:
            # 检查socket状态
            if hasattr(self.request, "fileno"):
                import select

                ready, _, _ = select.select([], [self.request], [], 0)
                return len(ready) > 0 or (time.time() - self.last_activity) < 60
            return True
        except:
            return False

    def handle(self):
        """处理POP3连接 - 增强错误恢复"""
        connection_id = f"{self.client_address[0]}:{self.client_address[1]}"

        # 检查连接是否在setup阶段就失败了
        if not self.connection_active:
            logger.debug(f"连接在setup阶段失败，跳过处理: {connection_id}")
            return

        try:
            logger.info(f"新的POP3连接: {connection_id}")

            # 发送欢迎消息
            if not self._safe_send_response("+OK POP3 server ready"):
                return

            while self.connection_active and self._is_connection_alive():
                try:
                    # 设置读取超时，避免长时间阻塞
                    self.request.settimeout(30)

                    # 读取命令
                    line = self._safe_read_line()
                    if line is None:
                        break

                    self.last_activity = time.time()
                    logger.debug(f"收到命令: {line} from {connection_id}")

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
                        self._safe_send_response(f"-ERR Unknown command: {command}")

                except socket.timeout:
                    logger.debug(f"POP3连接超时: {connection_id}")
                    self._safe_send_response("-ERR Connection timeout")
                    break
                except (
                    ConnectionResetError,
                    ConnectionAbortedError,
                    BrokenPipeError,
                ) as e:
                    logger.debug(f"客户端断开连接: {connection_id} - {e}")
                    break
                except Exception as e:
                    logger.warning(f"处理命令时出错: {e} from {connection_id}")
                    if not self._safe_send_response("-ERR Internal server error"):
                        break

        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
            logger.debug(f"连接被重置或中止: {connection_id} - {e}")
        except Exception as e:
            logger.debug(f"处理连接时出错: {e} from {connection_id}")
        finally:
            self.connection_active = False
            connection_duration = time.time() - self.connection_start_time
            logger.info(
                f"POP3连接关闭: {connection_id}, 持续时间: {connection_duration:.2f}秒"
            )

    def _safe_read_line(self):
        """安全读取一行数据"""
        try:
            line = self.rfile.readline().decode("utf-8", errors="replace").strip()
            if not line:
                return None
            return line
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            return None
        except Exception as e:
            logger.debug(f"读取数据时出错: {e}")
            return None

    def _safe_send_response(self, response):
        """安全发送响应"""
        try:
            self.wfile.write(f"{response}\r\n".encode("utf-8"))
            self.wfile.flush()
            logger.debug(f"发送响应: {response}")
            return True
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            logger.debug("发送响应时连接被重置")
            self.connection_active = False
            return False
        except Exception as e:
            logger.debug(f"发送响应时出错: {e}")
            self.connection_active = False
            return False

    def send_response(self, response):
        """发送响应（兼容性方法）"""
        return self._safe_send_response(response)

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
            emails = self.email_service.list_emails(
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
        self._safe_send_response(f"+OK User {username} accepted")

    def handle_pass(self, password):
        """处理PASS命令"""
        if not hasattr(self, "username"):
            self._safe_send_response("-ERR USER command must come first")
            return

        try:
            user = self.user_auth.authenticate(self.username, password)
            if user:
                self.authenticated_user = user
                self._safe_send_response(f"+OK User {self.username} authenticated")
                logger.info(f"用户认证成功: {self.username}")
            else:
                self._safe_send_response("-ERR Authentication failed")
                logger.warning(f"用户认证失败: {self.username}")
        except Exception as e:
            logger.error(f"认证过程中出错: {e}")
            self._safe_send_response("-ERR Authentication error")

    def handle_stat(self):
        """处理STAT命令"""
        if not self.authenticated_user:
            logger.warning("STAT命令: 用户未认证")
            self._safe_send_response("-ERR Not authenticated")
            return

        try:
            logger.debug(f"STAT命令: 开始处理，用户 {self.authenticated_user.email}")

            # 使用缓存的邮件列表
            emails = self.get_user_emails()
            logger.debug(f"STAT命令: 获取到 {len(emails)} 封邮件")

            total_size = sum(email.get("size", 0) for email in emails)
            logger.debug(f"STAT命令: 计算总大小 {total_size} 字节")

            response = f"+OK {len(emails)} {total_size}"
            self._safe_send_response(response)
            logger.info(
                f"STAT命令成功: 用户 {self.authenticated_user.email} 有 {len(emails)} 封邮件，总大小 {total_size} 字节"
            )

        except Exception as e:
            logger.error(f"处理STAT命令时出错: {e}")
            import traceback

            logger.error(f"详细错误信息: {traceback.format_exc()}")
            self._safe_send_response("-ERR Internal server error")

    def handle_list(self, args):
        """处理LIST命令"""
        if not self.authenticated_user:
            self._safe_send_response("-ERR Not authenticated")
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
                        self._safe_send_response(f"+OK {msg_num} {size}")
                    else:
                        self._safe_send_response("-ERR No such message")
                except ValueError:
                    self._safe_send_response("-ERR Invalid message number")
            else:  # LIST all messages
                self._safe_send_response(f"+OK {len(emails)} messages")
                for i, email in enumerate(emails, 1):
                    size = email.get("size", 0)
                    if not self._safe_send_response(f"{i} {size}"):
                        return
                self._safe_send_response(".")

        except Exception as e:
            logger.error(f"处理LIST命令时出错: {e}")
            self._safe_send_response("-ERR Internal server error")

    def handle_retr(self, args):
        """处理RETR命令"""
        if not self.authenticated_user:
            self._safe_send_response("-ERR Not authenticated")
            return

        try:
            msg_num = int(args)
            # 使用缓存的邮件列表
            emails = self.get_user_emails()

            if 1 <= msg_num <= len(emails):
                email = emails[msg_num - 1]
                content = self.email_service.get_email_content(email["message_id"])
                if content:
                    # 计算内容大小（字节）
                    content_bytes = content.encode("utf-8")
                    content_size = len(content_bytes)

                    if not self._safe_send_response(f"+OK {content_size} octets"):
                        return

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
                        if not self._safe_send_response(line):
                            return

                    # 发送结束标记
                    self._safe_send_response(".")
                    logger.debug(
                        f"RETR命令: 返回邮件 {msg_num} 内容，大小 {content_size} 字节"
                    )
                else:
                    self._safe_send_response("-ERR Message content not found")
                    logger.warning(f"RETR命令: 邮件 {msg_num} 内容未找到")
            else:
                self._safe_send_response("-ERR No such message")
                logger.warning(
                    f"RETR命令: 邮件编号 {msg_num} 超出范围 (1-{len(emails)})"
                )

        except ValueError:
            self._safe_send_response("-ERR Invalid message number")
        except Exception as e:
            logger.error(f"处理RETR命令时出错: {e}")
            self._safe_send_response("-ERR Internal server error")

    def handle_dele(self, args):
        """处理DELE命令"""
        if not self.authenticated_user:
            self._safe_send_response("-ERR Not authenticated")
            return

        try:
            msg_num = int(args)
            # 使用缓存的邮件列表
            emails = self.get_user_emails()

            if 1 <= msg_num <= len(emails):
                email = emails[msg_num - 1]
                # 实际标记邮件为删除
                success = self.email_service.mark_email_as_deleted(email["message_id"])
                if success:
                    # 清除缓存，因为邮件状态已改变
                    self.invalidate_cache()
                    self._safe_send_response(f"+OK Message {msg_num} deleted")
                    logger.debug(f"DELE命令: 标记邮件 {msg_num} 为删除")
                else:
                    self._safe_send_response("-ERR Failed to delete message")
                    logger.error(f"DELE命令: 删除邮件 {msg_num} 失败")
            else:
                self._safe_send_response("-ERR No such message")
                logger.warning(
                    f"DELE命令: 邮件编号 {msg_num} 超出范围 (1-{len(emails)})"
                )

        except ValueError:
            self._safe_send_response("-ERR Invalid message number")
        except Exception as e:
            logger.error(f"处理DELE命令时出错: {e}")
            self._safe_send_response("-ERR Internal server error")

    def handle_noop(self):
        """处理NOOP命令"""
        self._safe_send_response("+OK")

    def handle_rset(self):
        """处理RSET命令"""
        self._safe_send_response("+OK")

    def handle_quit(self):
        """处理QUIT命令"""
        self._safe_send_response("+OK POP3 server signing off")


class StablePOP3Server:
    """稳定的POP3服务器"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 995,  # 默认使用SSL端口
        use_ssl: bool = True,  # 默认启用SSL
        ssl_cert_file: str = SSL_CERT_FILE,
        ssl_key_file: str = SSL_KEY_FILE,
        max_connections: int = MAX_CONNECTIONS,
    ):
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.ssl_cert_file = ssl_cert_file
        self.ssl_key_file = ssl_key_file
        self.max_connections = max_connections
        self.server = None
        self.ssl_context = None

        # 创建数据库服务和用户认证
        self.email_service = EmailService()  # 使用新的邮件服务
        self.user_auth = UserAuth()

        # 如果使用SSL，创建SSL上下文
        if self.use_ssl:
            self.ssl_context = self._create_ssl_context()

        logger.info(f"POP3服务器已初始化: {host}:{port} (SSL: {use_ssl})")

        # 服务器实例
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
                request_queue_size = POP3_REQUEST_QUEUE_SIZE  # 增加请求队列大小

                def __init__(
                    self,
                    server_address,
                    RequestHandlerClass,
                    email_service,  # 改用email_service
                    user_auth,
                    use_ssl,
                    ssl_context,
                    max_connections,  # 添加最大连接数参数
                ):
                    self.email_service = email_service
                    self.user_auth = user_auth
                    self.use_ssl = use_ssl
                    self.ssl_context = ssl_context
                    self.max_connections = max_connections
                    self.current_connections = 0
                    self.connection_lock = threading.Lock()
                    super().__init__(server_address, RequestHandlerClass)

                def get_request(self):
                    """重写get_request方法以实现连接数限制"""
                    with self.connection_lock:
                        if self.current_connections >= self.max_connections:
                            logger.warning(
                                f"POP3服务器达到最大连接数限制 {self.max_connections}，拒绝新连接"
                            )
                            # 接受连接但立即关闭
                            request, client_address = super().get_request()
                            request.close()
                            raise socket.error("连接数已达上限")
                        self.current_connections += 1
                        logger.debug(
                            f"POP3新连接建立，当前连接数: {self.current_connections}/{self.max_connections}"
                        )

                    return super().get_request()

                def close_request(self, request):
                    """重写close_request方法以更新连接计数"""
                    try:
                        with self.connection_lock:
                            self.current_connections = max(
                                0, self.current_connections - 1
                            )
                            logger.debug(
                                f"POP3连接断开，当前连接数: {self.current_connections}/{self.max_connections}"
                            )
                        if hasattr(request, "close"):
                            request.close()
                    except Exception as e:
                        logger.debug(f"关闭请求时出错: {e}")
                    super().close_request(request)

                def handle_error(self, request, client_address):
                    """处理请求错误，防止服务器崩溃"""
                    try:
                        logger.error(f"处理客户端 {client_address} 时出错")
                        import traceback

                        logger.error(f"错误详情: {traceback.format_exc()}")
                    except:
                        pass  # 确保错误处理本身不会崩溃

            self.server = ThreadedTCPServer(
                (self.host, self.port),
                StablePOP3Handler,
                self.email_service,  # 传递email_service
                self.user_auth,
                self.use_ssl,
                self.ssl_context,
                self.max_connections,  # 传递最大连接数
            )

            # 在单独线程中启动服务器
            self.server_thread = threading.Thread(
                target=self.server.serve_forever, daemon=True
            )
            self.server_thread.start()

            logger.info(f"稳定POP3服务器已启动: {self.host}:{self.port}")
            logger.info(
                f"最大连接数: {self.max_connections}, 请求队列大小: {POP3_REQUEST_QUEUE_SIZE}"
            )

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
