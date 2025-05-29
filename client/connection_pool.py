# -*- coding: utf-8 -*-
"""
客户端连接池模块 - 管理SMTP和POP3客户端连接
"""

import os
import sys
import time
import socket
import smtplib
import poplib
import ssl
import threading
import queue
from typing import Optional, Dict, Any, Union
from contextlib import contextmanager
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.config import CLIENT_CONNECTION_POOL_SIZE
from common.utils import setup_logging

logger = setup_logging("client_connection_pool")


class SMTPConnectionPool:
    """SMTP连接池"""

    def __init__(
        self,
        host: str,
        port: int,
        username: str = "",
        password: str = "",
        use_ssl: bool = False,
        pool_size: int = CLIENT_CONNECTION_POOL_SIZE,
    ):
        """
        初始化SMTP连接池

        Args:
            host: SMTP服务器地址
            port: SMTP端口
            username: 用户名
            password: 密码
            use_ssl: 是否使用SSL
            pool_size: 连接池大小
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.pool_size = pool_size

        self.pool = queue.Queue(maxsize=pool_size)
        self.lock = threading.RLock()
        self.created_connections = 0
        self.active_connections = 0

        logger.info(f"SMTP连接池已初始化: {host}:{port}, 池大小: {pool_size}")

    def _create_connection(self) -> Optional[smtplib.SMTP]:
        """创建新的SMTP连接"""
        try:
            if self.use_ssl:
                smtp = smtplib.SMTP_SSL(self.host, self.port, timeout=30)
            else:
                smtp = smtplib.SMTP(self.host, self.port, timeout=30)

            # 进行认证
            if self.username and self.password:
                smtp.login(self.username, self.password)

            with self.lock:
                self.created_connections += 1

            logger.debug(f"创建新SMTP连接 #{self.created_connections}")
            return smtp

        except Exception as e:
            logger.error(f"创建SMTP连接失败: {e}")
            return None

    @contextmanager
    def get_connection(self, timeout: float = 30.0):
        """
        获取SMTP连接（上下文管理器）

        Args:
            timeout: 获取连接的超时时间

        Yields:
            smtplib.SMTP: SMTP连接
        """
        smtp = None
        try:
            # 尝试从池中获取连接
            try:
                smtp = self.pool.get(timeout=timeout)
                with self.lock:
                    self.active_connections += 1
                logger.debug(
                    f"从SMTP连接池获取连接，活跃连接数: {self.active_connections}"
                )
            except queue.Empty:
                logger.debug("SMTP连接池为空，创建新连接")
                smtp = self._create_connection()
                if not smtp:
                    raise RuntimeError("无法创建SMTP连接")
                with self.lock:
                    self.active_connections += 1

            # 检查连接是否有效
            if not self._validate_connection(smtp):
                logger.warning("SMTP连接无效，重新创建")
                smtp.quit()
                smtp = self._create_connection()
                if not smtp:
                    raise RuntimeError("无法创建有效的SMTP连接")

            yield smtp

        except Exception as e:
            logger.error(f"获取SMTP连接时出错: {e}")
            raise
        finally:
            # 归还连接到池中
            if smtp:
                try:
                    # 将连接放回池中
                    if self.pool.qsize() < self.pool_size:
                        self.pool.put(smtp)
                        logger.debug("SMTP连接已归还到连接池")
                    else:
                        smtp.quit()
                        logger.debug("SMTP连接池已满，关闭连接")

                    with self.lock:
                        self.active_connections = max(0, self.active_connections - 1)

                except Exception as e:
                    logger.error(f"归还SMTP连接时出错: {e}")
                    try:
                        smtp.quit()
                    except:
                        pass
                    with self.lock:
                        self.active_connections = max(0, self.active_connections - 1)

    def _validate_connection(self, smtp: smtplib.SMTP) -> bool:
        """验证SMTP连接是否有效"""
        try:
            status = smtp.noop()[0]
            return status == 250
        except Exception:
            return False

    def close_all(self):
        """关闭所有连接"""
        logger.info("关闭SMTP连接池...")

        while not self.pool.empty():
            try:
                smtp = self.pool.get_nowait()
                smtp.quit()
            except:
                pass

        with self.lock:
            self.active_connections = 0
            self.created_connections = 0

        logger.info("SMTP连接池已关闭")


class POP3ConnectionPool:
    """POP3连接池"""

    def __init__(
        self,
        host: str,
        port: int,
        username: str = "",
        password: str = "",
        use_ssl: bool = False,
        pool_size: int = CLIENT_CONNECTION_POOL_SIZE,
    ):
        """
        初始化POP3连接池

        Args:
            host: POP3服务器地址
            port: POP3端口
            username: 用户名
            password: 密码
            use_ssl: 是否使用SSL
            pool_size: 连接池大小
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.pool_size = pool_size

        self.pool = queue.Queue(maxsize=pool_size)
        self.lock = threading.RLock()
        self.created_connections = 0
        self.active_connections = 0

        logger.info(f"POP3连接池已初始化: {host}:{port}, 池大小: {pool_size}")

    def _create_connection(self) -> Optional[poplib.POP3]:
        """创建新的POP3连接"""
        try:
            if self.use_ssl:
                pop3 = poplib.POP3_SSL(self.host, self.port, timeout=30)
            else:
                pop3 = poplib.POP3(self.host, self.port, timeout=30)

            # 进行认证
            if self.username and self.password:
                pop3.user(self.username)
                pop3.pass_(self.password)

            with self.lock:
                self.created_connections += 1

            logger.debug(f"创建新POP3连接 #{self.created_connections}")
            return pop3

        except Exception as e:
            logger.error(f"创建POP3连接失败: {e}")
            return None

    @contextmanager
    def get_connection(self, timeout: float = 30.0):
        """
        获取POP3连接（上下文管理器）

        Args:
            timeout: 获取连接的超时时间

        Yields:
            poplib.POP3: POP3连接
        """
        pop3 = None
        try:
            # 尝试从池中获取连接
            try:
                pop3 = self.pool.get(timeout=timeout)
                with self.lock:
                    self.active_connections += 1
                logger.debug(
                    f"从POP3连接池获取连接，活跃连接数: {self.active_connections}"
                )
            except queue.Empty:
                logger.debug("POP3连接池为空，创建新连接")
                pop3 = self._create_connection()
                if not pop3:
                    raise RuntimeError("无法创建POP3连接")
                with self.lock:
                    self.active_connections += 1

            # 检查连接是否有效
            if not self._validate_connection(pop3):
                logger.warning("POP3连接无效，重新创建")
                pop3.quit()
                pop3 = self._create_connection()
                if not pop3:
                    raise RuntimeError("无法创建有效的POP3连接")

            yield pop3

        except Exception as e:
            logger.error(f"获取POP3连接时出错: {e}")
            raise
        finally:
            # 归还连接到池中
            if pop3:
                try:
                    # 将连接放回池中
                    if self.pool.qsize() < self.pool_size:
                        self.pool.put(pop3)
                        logger.debug("POP3连接已归还到连接池")
                    else:
                        pop3.quit()
                        logger.debug("POP3连接池已满，关闭连接")

                    with self.lock:
                        self.active_connections = max(0, self.active_connections - 1)

                except Exception as e:
                    logger.error(f"归还POP3连接时出错: {e}")
                    try:
                        pop3.quit()
                    except:
                        pass
                    with self.lock:
                        self.active_connections = max(0, self.active_connections - 1)

    def _validate_connection(self, pop3: poplib.POP3) -> bool:
        """验证POP3连接是否有效"""
        try:
            pop3.stat()  # 获取邮箱状态
            return True
        except Exception:
            return False

    def close_all(self):
        """关闭所有连接"""
        logger.info("关闭POP3连接池...")

        while not self.pool.empty():
            try:
                pop3 = self.pool.get_nowait()
                pop3.quit()
            except:
                pass

        with self.lock:
            self.active_connections = 0
            self.created_connections = 0

        logger.info("POP3连接池已关闭")


class ClientConnectionManager:
    """客户端连接管理器"""

    def __init__(self):
        """初始化连接管理器"""
        self.smtp_pools: Dict[str, SMTPConnectionPool] = {}
        self.pop3_pools: Dict[str, POP3ConnectionPool] = {}
        self.lock = threading.RLock()

    def get_smtp_pool(
        self,
        host: str,
        port: int,
        username: str = "",
        password: str = "",
        use_ssl: bool = False,
        pool_size: int = CLIENT_CONNECTION_POOL_SIZE,
    ) -> SMTPConnectionPool:
        """
        获取SMTP连接池

        Args:
            host: SMTP服务器地址
            port: SMTP端口
            username: 用户名
            password: 密码
            use_ssl: 是否使用SSL
            pool_size: 连接池大小

        Returns:
            SMTPConnectionPool: SMTP连接池
        """
        pool_key = f"{host}:{port}:{username}:{use_ssl}"

        with self.lock:
            if pool_key not in self.smtp_pools:
                self.smtp_pools[pool_key] = SMTPConnectionPool(
                    host, port, username, password, use_ssl, pool_size
                )
            return self.smtp_pools[pool_key]

    def get_pop3_pool(
        self,
        host: str,
        port: int,
        username: str = "",
        password: str = "",
        use_ssl: bool = False,
        pool_size: int = CLIENT_CONNECTION_POOL_SIZE,
    ) -> POP3ConnectionPool:
        """
        获取POP3连接池

        Args:
            host: POP3服务器地址
            port: POP3端口
            username: 用户名
            password: 密码
            use_ssl: 是否使用SSL
            pool_size: 连接池大小

        Returns:
            POP3ConnectionPool: POP3连接池
        """
        pool_key = f"{host}:{port}:{username}:{use_ssl}"

        with self.lock:
            if pool_key not in self.pop3_pools:
                self.pop3_pools[pool_key] = POP3ConnectionPool(
                    host, port, username, password, use_ssl, pool_size
                )
            return self.pop3_pools[pool_key]

    def close_all_pools(self):
        """关闭所有连接池"""
        logger.info("关闭所有客户端连接池...")

        with self.lock:
            for pool in self.smtp_pools.values():
                pool.close_all()
            for pool in self.pop3_pools.values():
                pool.close_all()

            self.smtp_pools.clear()
            self.pop3_pools.clear()

        logger.info("所有客户端连接池已关闭")

    def get_status(self) -> Dict[str, Any]:
        """获取所有连接池的状态"""
        with self.lock:
            return {
                "smtp_pools": len(self.smtp_pools),
                "pop3_pools": len(self.pop3_pools),
                "smtp_details": {
                    key: {
                        "active_connections": pool.active_connections,
                        "pool_size": pool.pool_size,
                        "available": pool.pool.qsize(),
                    }
                    for key, pool in self.smtp_pools.items()
                },
                "pop3_details": {
                    key: {
                        "active_connections": pool.active_connections,
                        "pool_size": pool.pool_size,
                        "available": pool.pool.qsize(),
                    }
                    for key, pool in self.pop3_pools.items()
                },
            }


# 全局连接管理器实例
connection_manager = ClientConnectionManager()


def get_smtp_connection_pool(*args, **kwargs) -> SMTPConnectionPool:
    """获取SMTP连接池的便捷函数"""
    return connection_manager.get_smtp_pool(*args, **kwargs)


def get_pop3_connection_pool(*args, **kwargs) -> POP3ConnectionPool:
    """获取POP3连接池的便捷函数"""
    return connection_manager.get_pop3_pool(*args, **kwargs)


def close_all_connection_pools():
    """关闭所有连接池的便捷函数"""
    connection_manager.close_all_pools()


if __name__ == "__main__":
    # 测试连接池
    import tempfile

    # 测试SMTP连接池
    smtp_pool = SMTPConnectionPool("localhost", 8025, pool_size=3)

    try:
        # 模拟多个连接
        with smtp_pool.get_connection() as smtp:
            print(f"SMTP连接成功: {smtp}")
    except Exception as e:
        print(f"SMTP连接失败: {e}")

    # 显示状态
    print(f"连接管理器状态: {connection_manager.get_status()}")

    # 清理
    connection_manager.close_all_pools()
    print("连接池测试完成")
