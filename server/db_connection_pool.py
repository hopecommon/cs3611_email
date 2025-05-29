# -*- coding: utf-8 -*-
"""
数据库连接池模块 - 提高数据库操作的并发性能
"""

import os
import sys
import sqlite3
import threading
import queue
import time
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.config import DB_CONNECTION_POOL_SIZE
from common.utils import setup_logging

logger = setup_logging("db_connection_pool")


class DatabaseConnectionPool:
    """数据库连接池"""

    def __init__(self, db_path: str, pool_size: int = DB_CONNECTION_POOL_SIZE):
        """
        初始化数据库连接池

        Args:
            db_path: 数据库文件路径
            pool_size: 连接池大小
        """
        self.db_path = db_path
        self.pool_size = pool_size
        self.pool = queue.Queue(maxsize=pool_size)
        self.lock = threading.RLock()
        self.created_connections = 0
        self.active_connections = 0

        # 预创建连接
        self._initialize_pool()

        logger.info(f"数据库连接池已初始化: {db_path}, 池大小: {pool_size}")

    def _initialize_pool(self):
        """初始化连接池"""
        for _ in range(self.pool_size):
            conn = self._create_connection()
            if conn:
                self.pool.put(conn)

    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """创建新的数据库连接"""
        try:
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,  # 允许多线程使用
                timeout=30.0,  # 设置超时时间
                isolation_level=None,  # 使用自动提交模式
            )

            # 设置连接属性
            conn.row_factory = sqlite3.Row  # 启用字典模式
            conn.execute("PRAGMA journal_mode=WAL")  # 启用WAL模式提高并发性能
            conn.execute("PRAGMA synchronous=NORMAL")  # 平衡性能和安全性
            conn.execute("PRAGMA cache_size=2000")  # 增加缓存大小
            conn.execute("PRAGMA temp_store=memory")  # 临时数据存储在内存中
            conn.execute("PRAGMA mmap_size=268435456")  # 启用内存映射

            with self.lock:
                self.created_connections += 1

            logger.debug(f"创建新数据库连接 #{self.created_connections}")
            return conn

        except Exception as e:
            logger.error(f"创建数据库连接失败: {e}")
            return None

    @contextmanager
    def get_connection(self, timeout: float = 30.0):
        """
        获取数据库连接（上下文管理器）

        Args:
            timeout: 获取连接的超时时间

        Yields:
            sqlite3.Connection: 数据库连接
        """
        conn = None
        try:
            # 尝试从池中获取连接
            try:
                conn = self.pool.get(timeout=timeout)
                with self.lock:
                    self.active_connections += 1
                logger.debug(f"从连接池获取连接，活跃连接数: {self.active_connections}")
            except queue.Empty:
                logger.warning("连接池为空，创建新连接")
                conn = self._create_connection()
                if not conn:
                    raise RuntimeError("无法创建数据库连接")
                with self.lock:
                    self.active_connections += 1

            # 检查连接是否有效
            if not self._validate_connection(conn):
                logger.warning("连接无效，创建新连接")
                conn.close()
                conn = self._create_connection()
                if not conn:
                    raise RuntimeError("无法创建有效的数据库连接")

            yield conn

        except Exception as e:
            logger.error(f"获取数据库连接时出错: {e}")
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise
        finally:
            # 归还连接到池中
            if conn:
                try:
                    # 确保事务已提交或回滚
                    if conn.in_transaction:
                        conn.commit()

                    # 将连接放回池中
                    if self.pool.qsize() < self.pool_size:
                        self.pool.put(conn)
                        logger.debug("连接已归还到连接池")
                    else:
                        conn.close()
                        logger.debug("连接池已满，关闭连接")

                    with self.lock:
                        self.active_connections = max(0, self.active_connections - 1)

                except Exception as e:
                    logger.error(f"归还连接时出错: {e}")
                    try:
                        conn.close()
                    except:
                        pass
                    with self.lock:
                        self.active_connections = max(0, self.active_connections - 1)

    def _validate_connection(self, conn: sqlite3.Connection) -> bool:
        """验证连接是否有效"""
        try:
            conn.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    def execute_query(self, query: str, params: tuple = (), timeout: float = 30.0):
        """
        执行查询语句

        Args:
            query: SQL查询语句
            params: 查询参数
            timeout: 超时时间

        Returns:
            查询结果
        """
        with self.get_connection(timeout) as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()

    def execute_update(
        self, query: str, params: tuple = (), timeout: float = 30.0
    ) -> int:
        """
        执行更新语句

        Args:
            query: SQL更新语句
            params: 更新参数
            timeout: 超时时间

        Returns:
            影响的行数
        """
        with self.get_connection(timeout) as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.rowcount

    def execute_script(self, script: str, timeout: float = 30.0):
        """
        执行SQL脚本

        Args:
            script: SQL脚本
            timeout: 超时时间
        """
        with self.get_connection(timeout) as conn:
            conn.executescript(script)
            conn.commit()

    def get_pool_status(self) -> dict:
        """获取连接池状态"""
        with self.lock:
            return {
                "pool_size": self.pool_size,
                "available_connections": self.pool.qsize(),
                "active_connections": self.active_connections,
                "created_connections": self.created_connections,
            }

    def close_all(self):
        """关闭所有连接"""
        logger.info("关闭数据库连接池...")

        # 关闭池中的所有连接
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except:
                pass

        with self.lock:
            self.active_connections = 0
            self.created_connections = 0

        logger.info("数据库连接池已关闭")

    def __del__(self):
        """析构函数"""
        try:
            self.close_all()
        except:
            pass


# 全局连接池实例
_connection_pools = {}
_pool_lock = threading.Lock()


def get_connection_pool(
    db_path: str, pool_size: int = DB_CONNECTION_POOL_SIZE
) -> DatabaseConnectionPool:
    """
    获取数据库连接池实例（单例模式）

    Args:
        db_path: 数据库文件路径
        pool_size: 连接池大小

    Returns:
        DatabaseConnectionPool: 连接池实例
    """
    with _pool_lock:
        if db_path not in _connection_pools:
            _connection_pools[db_path] = DatabaseConnectionPool(db_path, pool_size)
        return _connection_pools[db_path]


def close_all_pools():
    """关闭所有连接池"""
    with _pool_lock:
        for pool in _connection_pools.values():
            pool.close_all()
        _connection_pools.clear()


if __name__ == "__main__":
    # 测试连接池
    import tempfile
    import os

    # 创建临时数据库文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
        db_path = tmp.name

    try:
        # 创建连接池
        pool = DatabaseConnectionPool(db_path, pool_size=5)

        # 创建测试表
        pool.execute_script(
            """
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value INTEGER
            );
        """
        )

        # 测试插入
        pool.execute_update(
            "INSERT INTO test_table (name, value) VALUES (?, ?)", ("test", 123)
        )

        # 测试查询
        results = pool.execute_query("SELECT * FROM test_table")
        print(f"查询结果: {results}")

        # 显示连接池状态
        status = pool.get_pool_status()
        print(f"连接池状态: {status}")

        print("连接池测试完成")

    finally:
        # 清理
        pool.close_all()
        os.unlink(db_path)
