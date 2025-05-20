"""
POP3服务器模块 - 实现基本的POP3服务，支持SSL/TLS和用户认证
"""

import os
import socket
import threading
import ssl
import time
import datetime
import sys
import logging
import traceback
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.config import (
    MAX_CONNECTIONS,
    SSL_CERT_FILE,
    SSL_KEY_FILE,
    AUTH_REQUIRED,
    SOCKET_BACKLOG,
)
from server.db_handler import DatabaseHandler
from server.user_auth import UserAuth
from server.pop3_session import POP3Session
from server.pop3_auth import POP3Authenticator
from server.pop3_utils import (
    is_port_available,
    find_available_port,
    validate_host,
    create_ssl_context,
    close_socket_safely,
)
from server.pop3_test_data import POP3TestDataGenerator
from common.port_config import resolve_port, save_port_config, get_service_port
from server.pop3_commands import POP3CommandHandler

# 设置日志
logger = setup_logging("pop3_server", level="DEBUG")


class POP3Server:
    """POP3服务器类，管理服务器的启动、停止和连接处理"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 110,
        use_ssl: bool = False,
        ssl_port: int = 995,
        max_connections: int = MAX_CONNECTIONS,
        ssl_cert_file: str = SSL_CERT_FILE,
        ssl_key_file: str = SSL_KEY_FILE,
        auto_port_detection: bool = True,
    ):
        """
        初始化POP3服务器

        Args:
            host: 服务器主机名或IP地址
            port: 服务器端口（非SSL）
            use_ssl: 是否使用SSL/TLS
            ssl_port: SSL/TLS端口
            max_connections: 最大连接数
            ssl_cert_file: SSL证书文件路径
            ssl_key_file: SSL密钥文件路径
            auto_port_detection: 是否启用自动端口检测和切换
        """
        # 验证主机名
        self.host = validate_host(host)
        self.original_port = port  # 保存原始端口，用于报告端口变更
        self.original_ssl_port = ssl_port  # 保存原始SSL端口

        # 从配置文件获取端口
        if use_ssl:
            config_port = get_service_port("pop3_ssl_port", ssl_port)
            self.port = config_port
        else:
            config_port = get_service_port("pop3_port", port)
            self.port = config_port

        self.use_ssl = use_ssl
        self.ssl_cert_file = ssl_cert_file
        self.ssl_key_file = ssl_key_file
        self.max_connections = max_connections
        self.auto_port_detection = auto_port_detection
        self.port_changed = False  # 标记端口是否已更改
        self.running = False
        self.server_socket = None
        self.db_handler = DatabaseHandler()
        self.user_auth = UserAuth()
        self.connections = []
        self.thread_pool = ThreadPoolExecutor(max_workers=max_connections)
        self.ssl_context = None

        # 创建认证器
        self.authenticator = POP3Authenticator(self.user_auth)

        # 加载用户列表
        self.users = self.authenticator.load_users_from_user_auth()

        # 如果启用SSL，加载SSL证书
        if self.use_ssl:
            self.ssl_context = create_ssl_context(self.ssl_cert_file, self.ssl_key_file)
            if not self.ssl_context:
                self.use_ssl = False

        # 创建测试数据生成器并确保测试用户和邮件存在
        test_data_generator = POP3TestDataGenerator(self.db_handler, self.user_auth)
        test_data_generator.ensure_test_users_exist()

        logger.info(
            f"POP3服务器已初始化: {host}:{self.port}, "
            f"SSL: {'启用' if self.use_ssl else '禁用'}"
        )

    def start(self) -> None:
        """启动POP3服务器"""
        if self.running:
            logger.warning("POP3服务器已经在运行")
            return

        # 使用统一的端口管理逻辑
        service_name = "pop3"
        port, changed, message = resolve_port(
            service_name, self.port, self.use_ssl, auto_detect=True
        )

        if port == 0:
            logger.error(message)
            raise RuntimeError(message)

        if changed:
            logger.warning(message)
            print(f"\n[警告] {message}\n")
            self.port = port
            self.port_changed = True

            # 保存新端口到配置文件，以便客户端能够自动使用
            port_key = (
                f"{service_name}_ssl_port" if self.use_ssl else f"{service_name}_port"
            )
            save_port_config(port_key, port)

        logger.info(message)

        try:
            # 创建服务器套接字
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # 如果使用SSL，包装套接字
            if self.use_ssl and self.ssl_context:
                logger.info("使用SSL/TLS加密连接")
                # 绑定和监听在原始套接字上
                self.server_socket.bind((self.host, self.port))
                self.server_socket.listen(SOCKET_BACKLOG)
            else:
                # 非SSL模式
                self.server_socket.bind((self.host, self.port))
                self.server_socket.listen(SOCKET_BACKLOG)

            # 设置为非阻塞模式
            self.server_socket.settimeout(1.0)

            self.running = True

            # 显示服务器信息
            logger.info(f"POP3服务器已启动: {self.host}:{self.port}")
            logger.info(f"SSL: {'启用' if self.use_ssl else '禁用'}")

            # 如果端口已更改，显示醒目的提示
            if self.port_changed:
                logger.warning(f"注意: 服务器使用的端口与请求的端口不同")
                logger.warning(
                    f"请求的端口: {self.original_port if not self.use_ssl else self.original_ssl_port}"
                )
                logger.warning(f"实际使用的端口: {self.port}")

                # 在控制台显示醒目的提示
                print(f"\n{'='*60}")
                print(f"  POP3{'(SSL)' if self.use_ssl else ''}服务器端口信息")
                print(
                    f"  请求的端口: {self.original_port if not self.use_ssl else self.original_ssl_port}"
                )
                print(f"  实际使用的端口: {self.port}")
                print(f"  新端口已保存到配置文件，客户端将自动使用新端口。")
                print(f"{'='*60}\n")

            # 处理连接
            self._handle_connections()
        except Exception as e:
            logger.error(f"启动POP3服务器时出错: {e}")
            self.stop()
            raise  # 重新抛出异常，让调用者知道发生了错误

    def stop(self) -> None:
        """停止POP3服务器"""
        if not self.running:
            logger.debug("POP3服务器已经停止，无需再次停止")
            return

        logger.info("正在停止POP3服务器...")
        self.running = False

        # 关闭所有连接
        active_connections = len(self.connections)
        for conn in self.connections:
            try:
                conn.close()
            except Exception as e:
                logger.debug(f"关闭连接时出错: {e}")

        # 关闭服务器套接字
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                logger.debug(f"关闭服务器套接字时出错: {e}")
            self.server_socket = None

        # 关闭线程池
        try:
            self.thread_pool.shutdown(wait=True, cancel_futures=True)
        except TypeError:
            # Python 3.8及以下版本不支持cancel_futures参数
            self.thread_pool.shutdown(wait=True)
        except Exception as e:
            logger.debug(f"关闭线程池时出错: {e}")

        logger.info(f"POP3服务器已停止，关闭了 {active_connections} 个活动连接")

    def _handle_connections(self) -> None:
        """处理客户端连接"""
        # 上次清理时间
        last_cleanup_time = time.time()
        cleanup_interval = 60  # 60秒清理一次

        try:
            while self.running:
                try:
                    # 定期清理无效连接
                    current_time = time.time()
                    if current_time - last_cleanup_time > cleanup_interval:
                        self._cleanup_zombie_connections()
                        last_cleanup_time = current_time

                    # 接受连接
                    client_socket, client_address = self.server_socket.accept()

                    # 记录连接信息
                    logger.debug(f"收到新连接: {client_address}")

                    # 检查连接数是否超过限制
                    if len(self.connections) >= self.max_connections:
                        logger.warning(
                            f"连接数超过限制 ({len(self.connections)}/{self.max_connections}): {client_address}"
                        )
                        try:
                            client_socket.sendall(b"-ERR Too many connections\r\n")
                            client_socket.close()
                        except Exception as e:
                            logger.debug(f"拒绝连接时出错: {e}")
                        continue

                    # 如果使用SSL，包装客户端套接字
                    if self.use_ssl and self.ssl_context:
                        try:
                            client_socket = self.ssl_context.wrap_socket(
                                client_socket, server_side=True
                            )
                            logger.debug(f"已为连接 {client_address} 启用SSL")
                        except ssl.SSLError as e:
                            logger.error(f"SSL握手失败: {e}")
                            try:
                                client_socket.close()
                            except:
                                pass
                            continue
                        except Exception as e:
                            logger.error(f"包装SSL套接字时出错: {e}")
                            try:
                                client_socket.close()
                            except:
                                pass
                            continue

                    # 设置较长的超时时间防止会话过早终止
                    try:
                        client_socket.settimeout(
                            300
                        )  # 设置为5分钟，确保会话不会过早结束
                    except Exception as e:
                        logger.error(f"设置套接字超时时出错: {e}")
                        try:
                            client_socket.close()
                        except:
                            pass
                        continue

                    # 确保套接字是有效的，再添加到连接列表
                    if client_socket is None:
                        logger.error(f"客户端套接字为None，跳过处理: {client_address}")
                        continue

                    # 添加到连接列表
                    self.connections.append(client_socket)

                    try:
                        # 创建会话并处理
                        session = POP3Session(
                            client_socket=client_socket,
                            client_address=client_address,
                            db_handler=self.db_handler,
                            authenticator=self.authenticator,
                        )

                        # 使用线程池处理会话
                        future = self.thread_pool.submit(self._handle_session, session)

                        # 添加回调，处理异常
                        def handle_future_done(future):
                            try:
                                # 获取结果，如果有异常会抛出
                                future.result()
                            except Exception as e:
                                logger.error(f"会话处理线程异常: {e}")
                                logger.error(f"异常详情: {traceback.format_exc()}")

                        future.add_done_callback(handle_future_done)

                        logger.info(
                            f"接受连接: {client_address}, 当前连接数: {len(self.connections)}/{self.max_connections}"
                        )
                    except Exception as e:
                        logger.error(f"创建或提交会话处理时出错: {e}")
                        logger.error(f"异常详情: {traceback.format_exc()}")

                        # 尝试从连接列表中移除
                        try:
                            if client_socket in self.connections:
                                self.connections.remove(client_socket)
                        except:
                            pass

                        # 尝试关闭客户端套接字
                        try:
                            client_socket.close()
                        except:
                            pass
                except socket.timeout:
                    # 超时，继续循环
                    continue
                except ssl.SSLError as e:
                    if self.running:
                        logger.error(f"SSL错误: {e}")
                    continue
                except ConnectionError as e:
                    if self.running:
                        logger.error(f"连接错误: {e}")
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"处理连接时出错: {e}")
                        logger.error(f"异常详情: {traceback.format_exc()}")
                    continue
        except KeyboardInterrupt:
            logger.info("收到键盘中断，停止服务器")
        finally:
            self.stop()

    def _handle_session(self, session: POP3Session) -> None:
        """
        处理POP3会话

        Args:
            session: POP3会话对象
        """
        client_address = session.address
        start_time = time.time()

        try:
            # 处理会话
            logger.debug(f"开始处理会话: {client_address}")
            session.handle()
        except ssl.SSLError as e:
            logger.error(f"会话 {client_address} SSL错误: {e}")
        except ConnectionError as e:
            logger.error(f"会话 {client_address} 连接错误: {e}")
        except Exception as e:
            logger.error(f"处理会话 {client_address} 时出错: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
        finally:
            # 从连接列表中移除
            try:
                if session.socket in self.connections:
                    self.connections.remove(session.socket)
                    logger.debug(f"已从连接列表移除: {client_address}")
            except Exception as e:
                logger.error(f"从连接列表移除时出错: {e}")

            # 确保套接字已关闭
            try:
                if session.socket is not None and hasattr(session.socket, "_closed"):
                    if not session.socket._closed:
                        session.socket.close()
                        logger.debug(f"已关闭会话套接字: {client_address}")
                elif session.socket is not None:
                    try:
                        session.socket.close()
                        logger.debug(f"已关闭会话套接字: {client_address}")
                    except:
                        pass
            except Exception as e:
                logger.debug(f"关闭会话套接字时出错: {e}")

            # 记录会话处理时间
            duration = time.time() - start_time
            logger.info(f"会话 {client_address} 已结束，处理时间: {duration:.2f}秒")

    def _cleanup_zombie_connections(self) -> None:
        """清理已关闭或不活动的连接"""
        try:
            # 保存原始连接列表长度用于日志输出
            original_count = len(self.connections)

            # 检查并移除已关闭或不活动的连接
            valid_connections = []
            for conn in self.connections:
                # 首先检查连接是否为None
                if conn is None:
                    logger.debug("跳过None连接")
                    continue

                try:
                    # 尝试使用非阻塞方式检查连接是否还有效
                    if not hasattr(conn, "setblocking"):
                        logger.debug("连接对象没有setblocking方法，可能不是有效套接字")
                        continue

                    # 尝试使用非阻塞方式发送心跳，检查连接是否还有效
                    # 不会实际发送数据，只检查套接字状态
                    conn.setblocking(0)
                    # 使用空的peek数据调用recv，不会实际读取数据，但会检查连接状态
                    try:
                        conn.recv(1, socket.MSG_PEEK | socket.MSG_DONTWAIT)
                        valid_connections.append(conn)
                    except BlockingIOError:
                        # 如果收到BlockingIOError，表示连接正常但无数据可读，保留连接
                        valid_connections.append(conn)
                    except (ConnectionError, OSError, ssl.SSLError):
                        # 连接已断开或有错误，不添加到有效连接列表，记录关闭信息
                        try:
                            conn.close()
                        except:
                            pass
                        logger.debug(f"已清理无效连接")
                    finally:
                        # 恢复阻塞模式
                        try:
                            conn.setblocking(1)
                        except:
                            pass
                except Exception as e:
                    # 处理连接时出错，尝试关闭并从有效连接列表移除
                    logger.debug(f"检查连接状态时出错: {e}")
                    try:
                        # 确保连接有close方法
                        if hasattr(conn, "close"):
                            conn.close()
                    except:
                        pass

            # 更新连接列表
            cleaned_count = original_count - len(valid_connections)
            if cleaned_count > 0:
                self.connections = valid_connections
                logger.info(
                    f"清理了 {cleaned_count} 个僵尸连接，剩余 {len(valid_connections)} 个连接"
                )
        except Exception as e:
            logger.error(f"清理僵尸连接时出错: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
            # 出错时不更新连接列表，确保不会意外丢失所有连接


if __name__ == "__main__":
    # 从命令行参数获取主机名和端口
    import argparse

    parser = argparse.ArgumentParser(description="POP3服务器")
    parser.add_argument("--host", default="localhost", help="服务器主机名")
    parser.add_argument("--port", type=int, default=110, help="非SSL服务器端口")
    parser.add_argument("--ssl-port", type=int, default=995, help="SSL服务器端口")
    parser.add_argument("--ssl", action="store_true", help="启用SSL")
    parser.add_argument("--no-ssl", dest="ssl", action="store_false", help="禁用SSL")
    parser.add_argument("--max-connections", type=int, default=10, help="最大连接数")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.set_defaults(ssl=True)  # 默认启用SSL
    args = parser.parse_args()

    # 设置日志级别
    if args.debug:
        logger.setLevel(logging.DEBUG)
        print("已启用调试模式")

    # 创建并启动POP3服务器
    try:
        # 创建POP3服务器
        server = POP3Server(
            host=args.host,
            port=args.ssl_port if args.ssl else args.port,
            use_ssl=args.ssl,
            max_connections=args.max_connections,
        )

        # 启动服务器
        print(
            f"正在启动POP3服务器: {args.host}:{args.ssl_port if args.ssl else args.port}"
        )
        print(f"SSL: {'启用' if args.ssl else '禁用'}")
        print(f"最大连接数: {args.max_connections}")
        server.start()

        # 等待键盘中断
        print("服务器已启动，按Ctrl+C停止...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n收到键盘中断，正在停止服务器...")
        finally:
            server.stop()
            print("服务器已停止")
    except Exception as e:
        print(f"启动POP3服务器时出错: {e}")
        import traceback

        print(f"异常详情: {traceback.format_exc()}")
