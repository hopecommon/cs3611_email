# -*- coding: utf-8 -*-
"""
POP3连接管理器
负责POP3服务器的连接、认证和断开连接
"""

import poplib
import ssl
import time
import socket
from typing import Optional, Literal

from common.utils import setup_logging
from client.socket_utils import close_ssl_connection_safely

# 设置日志
logger = setup_logging("pop3_connection_manager")


class POP3ConnectionManager:
    """POP3连接管理器"""

    def __init__(
        self,
        host: str,
        port: int,
        use_ssl: bool = True,
        username: Optional[str] = None,
        password: Optional[str] = None,
        auth_method: Optional[Literal["BASIC", "APOP", "AUTO"]] = "AUTO",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        初始化连接管理器

        Args:
            host: POP3服务器主机名
            port: POP3服务器端口
            use_ssl: 是否使用SSL/TLS
            username: 认证用户名
            password: 认证密码
            auth_method: 认证方法
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
                    # 创建增强的SSL上下文以解决各种邮件服务器的兼容性问题
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE

                    # 设置更宽松的SSL选项以兼容不同服务器
                    context.options |= ssl.OP_NO_SSLv2
                    context.options |= ssl.OP_NO_SSLv3
                    context.options |= ssl.OP_NO_TLSv1
                    context.options |= ssl.OP_NO_TLSv1_1

                    # 设置密码套件以提高兼容性
                    try:
                        context.set_ciphers(
                            "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
                        )
                    except ssl.SSLError:
                        # 如果设置失败，使用默认密码套件
                        logger.debug("使用默认SSL密码套件")

                    # 针对不同邮件服务器的特殊处理
                    if (
                        "qq.com" in self.host.lower()
                        or "smtp.qq.com" in self.host.lower()
                    ):
                        # QQ邮箱特殊配置
                        context.minimum_version = ssl.TLSVersion.TLSv1_2
                        context.maximum_version = ssl.TLSVersion.TLSv1_3
                    elif (
                        "gmail.com" in self.host.lower()
                        or "google.com" in self.host.lower()
                    ):
                        # Gmail特殊配置
                        context.minimum_version = ssl.TLSVersion.TLSv1_2
                    elif (
                        "outlook.com" in self.host.lower()
                        or "hotmail.com" in self.host.lower()
                    ):
                        # Outlook特殊配置
                        context.minimum_version = ssl.TLSVersion.TLSv1_2

                    # 增加超时时间并添加重试机制
                    connection_timeout = self.timeout * 3
                    temp_connection = poplib.POP3_SSL(
                        self.host,
                        self.port,
                        timeout=connection_timeout,
                        context=context,
                    )
                else:
                    temp_connection = poplib.POP3(
                        self.host, self.port, timeout=self.timeout
                    )

                # 如果提供了认证信息，则进行认证
                if self.username and self.password:
                    self._authenticate(temp_connection)

                # 认证成功后，将临时连接赋值给实例变量
                self.connection = temp_connection
                temp_connection = None  # 避免在finally中关闭连接

                logger.info(f"已连接到POP3服务器: {self.host}:{self.port}")
                return

            except (poplib.error_proto, OSError, ssl.SSLError) as e:
                last_exception = e
                retry_count += 1

                # 详细的错误分析和处理
                error_msg = str(e).lower()
                error_type = self._analyze_error_type(error_msg)

                # 根据错误类型提供具体的解决建议
                if error_type == "qq_auth_code":
                    logger.warning(
                        f"QQ邮箱要求使用授权码而非密码登录，请在QQ邮箱设置中获取授权码"
                    )
                elif error_type == "ssl_handshake":
                    logger.warning(f"SSL握手失败，尝试降级SSL版本或调整密码套件")
                elif error_type == "ssl_protocol":
                    logger.warning(f"SSL协议错误，可能是服务器SSL配置问题")
                elif error_type == "connection_timeout":
                    logger.warning(f"连接超时，可能是网络问题或服务器负载过高")
                elif error_type == "connection_refused":
                    logger.warning(f"连接被拒绝，请检查服务器地址和端口")
                elif error_type == "auth_failed":
                    logger.warning(f"认证失败，请检查用户名和密码")

                logger.warning(
                    f"连接POP3服务器失败 (尝试 {retry_count}/{self.max_retries}): {e}"
                )

                # 确保临时连接被安全关闭
                close_ssl_connection_safely(temp_connection)

                # 智能重试策略
                if self._should_retry(error_type, retry_count):
                    # 如果是认证错误，尝试不同的认证方法
                    if error_type == "auth_failed" and self.auth_method == "AUTO":
                        if retry_count == 1:
                            logger.info(f"尝试切换到BASIC认证方法")
                            self.auth_method = "BASIC"
                        elif retry_count == 2:
                            logger.info(f"尝试切换到APOP认证方法")
                            self.auth_method = "APOP"

                    # 根据错误类型调整等待时间
                    wait_time = self._get_retry_wait_time(error_type, retry_count)
                    time.sleep(wait_time)
                else:
                    # 某些错误不应该重试
                    logger.error(f"错误类型 {error_type} 不适合重试，停止尝试")
                    break

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

    def _authenticate(self, connection) -> None:
        """
        进行认证

        Args:
            connection: POP3连接对象

        Raises:
            poplib.error_proto: 认证失败时抛出
        """
        try:
            # 获取服务器欢迎信息，检查是否支持APOP
            welcome = connection.welcome
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
                    connection.apop(self.username, self.password)
                    logger.info(f"已使用APOP认证: {self.username}")
                except (poplib.error_proto, Exception) as auth_err:
                    # 如果APOP认证失败，且是AUTO模式，尝试基本认证
                    if self.auth_method == "AUTO":
                        logger.warning(f"APOP认证失败: {auth_err}, 尝试基本认证")
                        connection.user(self.username)
                        connection.pass_(self.password)
                        logger.info(f"已使用基本认证: {self.username}")
                    else:
                        # 如果指定了APOP且失败，则抛出异常
                        raise
            else:
                # 使用基本认证
                connection.user(self.username)
                connection.pass_(self.password)
                logger.info(f"已使用基本认证: {self.username}")

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
            finally:
                # 确保连接对象被清除
                self.connection = None
                logger.debug("连接对象已清除")
        else:
            logger.debug("没有活动的连接需要断开")

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connection is not None

    def get_connection(self):
        """获取连接对象"""
        if not self.connection:
            self.connect()
        return self.connection

    def _analyze_error_type(self, error_msg: str) -> str:
        """
        分析错误类型

        Args:
            error_msg: 错误消息（小写）

        Returns:
            错误类型字符串
        """
        if "please using authorized code to login" in error_msg:
            return "qq_auth_code"
        elif "handshake" in error_msg and "ssl" in error_msg:
            return "ssl_handshake"
        elif "eof occurred in violation of protocol" in error_msg:
            return "ssl_protocol"
        elif "timed out" in error_msg or "timeout" in error_msg:
            return "connection_timeout"
        elif "connection refused" in error_msg or "refused" in error_msg:
            return "connection_refused"
        elif "authentication failed" in error_msg or "auth" in error_msg:
            return "auth_failed"
        elif "certificate" in error_msg or "cert" in error_msg:
            return "ssl_certificate"
        elif "network" in error_msg or "unreachable" in error_msg:
            return "network_error"
        else:
            return "unknown"

    def _should_retry(self, error_type: str, retry_count: int) -> bool:
        """
        判断是否应该重试

        Args:
            error_type: 错误类型
            retry_count: 当前重试次数

        Returns:
            是否应该重试
        """
        # 不应该重试的错误类型
        no_retry_errors = ["qq_auth_code", "connection_refused"]

        if error_type in no_retry_errors:
            return False

        # 达到最大重试次数
        if retry_count >= self.max_retries:
            return False

        return True

    def _get_retry_wait_time(self, error_type: str, retry_count: int) -> float:
        """
        获取重试等待时间

        Args:
            error_type: 错误类型
            retry_count: 当前重试次数

        Returns:
            等待时间（秒）
        """
        base_wait_time = {
            "ssl_handshake": 3.0,
            "ssl_protocol": 2.0,
            "connection_timeout": 5.0,
            "auth_failed": 1.0,
            "ssl_certificate": 2.0,
            "network_error": 4.0,
            "unknown": 2.0,
        }

        wait_time = base_wait_time.get(error_type, 2.0)

        # 指数退避：每次重试增加等待时间
        return wait_time * (1.5 ** (retry_count - 1))
