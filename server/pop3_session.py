"""
POP3会话模块 - 处理POP3客户端连接和会话
"""

import socket
import time
import logging
import ssl
import datetime
import traceback
from typing import Tuple, Optional

from common.utils import setup_logging
from common.config import CONNECTION_IDLE_TIMEOUT
from server.db_handler import DatabaseHandler
from server.pop3_auth import POP3Authenticator
from server.pop3_commands import POP3CommandHandler

# 设置日志
logger = setup_logging("pop3_session")


class POP3Session:
    """POP3会话类，处理单个客户端连接"""

    def __init__(
        self,
        client_socket: socket.socket,
        client_address: Tuple[str, int],
        db_handler: DatabaseHandler,
        authenticator: POP3Authenticator,
    ):
        """
        初始化POP3会话

        Args:
            client_socket: 客户端套接字
            client_address: 客户端地址
            db_handler: 数据库处理器
            authenticator: POP3认证器
        """
        self.socket = client_socket
        self.address = client_address
        self.db_handler = db_handler
        self.authenticator = authenticator

        # 设置更长的超时时间，确保会话不会过早结束
        self.socket.settimeout(CONNECTION_IDLE_TIMEOUT)  # 使用空闲超时而不是连接超时

        # 创建命令处理器
        self.command_handler = POP3CommandHandler(
            db_handler=self.db_handler,
            authenticator=self.authenticator,
            send_response_callback=self.send_response,
        )

        # 会话统计信息
        self.command_count = 0
        self.bytes_received = 0
        self.bytes_sent = 0
        self.start_time = time.time()
        self.last_command_time = time.time()  # 上次命令时间，用于检测空闲超时

        logger.info(f"新的POP3会话: {client_address}")

    def handle(self) -> None:
        """处理POP3会话"""
        try:
            # 发送欢迎消息
            server_name = socket.gethostname()
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            welcome_message = f"+OK POP3 server ready at {server_name} [{timestamp}]"
            self.send_response(welcome_message)

            logger.debug(f"会话 {self.address} 开始，发送欢迎消息")

            # 处理命令
            idle_timeout = CONNECTION_IDLE_TIMEOUT
            while True:
                # 检查空闲超时
                if time.time() - self.last_command_time > idle_timeout:
                    logger.warning(f"会话 {self.address} 空闲超时")
                    self.send_response("-ERR Session idle timeout")
                    break

                # 接收命令
                logger.debug(f"会话 {self.address} 等待命令...")
                command = self.receive_command()
                if not command:
                    logger.debug(f"会话 {self.address} 接收到空命令或连接关闭")
                    break

                # 更新上次命令时间
                self.last_command_time = time.time()
                self.command_count += 1

                # 处理命令
                logger.debug(
                    f"会话 {self.address} 处理命令 #{self.command_count}: {command}"
                )
                if not self.command_handler.handle_command(command):
                    logger.debug(f"会话 {self.address} 命令处理返回False，结束会话")
                    break
        except ssl.SSLError as e:
            logger.error(f"SSL错误: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            # 尝试发送错误响应
            try:
                self.send_response(f"-ERR SSL error: connection closing")
            except:
                pass
        except ConnectionError as e:
            logger.error(f"连接错误: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
        except Exception as e:
            logger.error(f"处理POP3会话时出错: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            # 尝试发送错误响应
            try:
                self.send_response(f"-ERR Internal server error: connection closing")
            except:
                pass
        finally:
            # 如果在UPDATE状态，执行删除操作
            try:
                if self.command_handler.state == "UPDATE":
                    self.command_handler.perform_deletions()
            except Exception as e:
                logger.error(f"执行删除操作时出错: {e}")

            # 关闭连接
            try:
                # 确保套接字不是None
                if self.socket is None:
                    logger.debug(f"套接字已经是None: {self.address}")
                    return

                # 确保套接字关闭
                if hasattr(self.socket, "shutdown"):
                    try:
                        # 尝试正常关闭套接字（先shutdown再close）
                        self.socket.shutdown(socket.SHUT_RDWR)
                    except (OSError, socket.error, ssl.SSLError, ConnectionError):
                        # 如果shutdown失败，忽略异常，继续尝试close
                        pass

                # 关闭套接字
                if hasattr(self.socket, "_closed"):
                    if not self.socket._closed:
                        self.socket.close()
                        logger.debug(f"已关闭套接字: {self.address}")
                else:
                    # 直接尝试关闭套接字
                    try:
                        self.socket.close()
                        logger.debug(f"已关闭套接字: {self.address}")
                    except:
                        pass
            except Exception as e:
                logger.debug(f"关闭套接字时出错: {e}")
            finally:
                # 无论如何都置空引用，帮助垃圾回收
                self.socket = None

            # 记录会话统计信息
            duration = time.time() - self.start_time
            logger.info(
                f"POP3会话结束: {self.address}, "
                f"持续时间: {duration:.2f}秒, "
                f"命令数: {self.command_count}, "
                f"接收: {self.bytes_received} 字节, "
                f"发送: {self.bytes_sent} 字节"
            )

    def receive_command(self) -> Optional[str]:
        """
        接收POP3命令

        Returns:
            命令字符串，如果连接关闭则返回None
        """
        try:
            data = self.socket.recv(1024)
            if not data:
                logger.debug(f"连接 {self.address} 已关闭")
                return None

            self.bytes_received += len(data)
            command = data.decode("utf-8", errors="ignore").strip()

            # 对于密码命令，不记录实际内容
            if command.upper().startswith("PASS "):
                log_command = "PASS [密码已隐藏]"
            else:
                log_command = command

            logger.debug(f"收到命令 ({self.address}): {log_command}")
            return command
        except socket.timeout:
            logger.warning(f"连接超时: {self.address}")
            try:
                self.send_response("-ERR Connection timed out")
            except:
                pass  # 如果发送响应失败，忽略异常
            return None
        except ssl.SSLError as e:
            if "timed out" in str(e):
                logger.warning(f"SSL连接超时: {self.address}")
                try:
                    self.send_response("-ERR SSL connection timed out")
                except:
                    pass  # 如果发送响应失败，忽略异常
            else:
                logger.error(f"SSL错误: {e}")
            return None
        except ConnectionError as e:
            logger.error(f"连接错误: {e}")
            return None
        except UnicodeDecodeError as e:
            logger.warning(f"解码命令时出错: {e}")
            try:
                self.send_response("-ERR Invalid command encoding")
            except:
                pass  # 如果发送响应失败，忽略异常
            return None
        except Exception as e:
            logger.error(f"接收命令时出错: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            return None

    def send_response(self, response: str) -> None:
        """
        发送POP3响应

        Args:
            response: 响应消息
        """
        try:
            # 确保响应以CRLF结尾
            if not response.endswith("\r\n"):
                response_bytes = f"{response}\r\n".encode("utf-8")
            else:
                response_bytes = response.encode("utf-8")

            self.socket.sendall(response_bytes)
            self.bytes_sent += len(response_bytes)

            # 对于多行响应，只记录第一行
            log_response = response.split("\r\n")[0]
            if len(log_response) > 100:
                log_response = log_response[:97] + "..."

            logger.debug(f"发送响应 ({self.address}): {log_response}")
        except ssl.SSLError as e:
            logger.error(f"SSL错误: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            raise
        except ConnectionError as e:
            logger.error(f"发送响应时连接错误: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            raise
        except Exception as e:
            logger.error(f"发送响应时出错: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            raise
