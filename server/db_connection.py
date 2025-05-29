"""
数据库连接管理 - 负责SQLite数据库的连接、初始化和基础操作
"""

import os
import sqlite3
import time
from typing import Optional
from pathlib import Path

from common.utils import setup_logging
from common.config import DB_PATH

# 设置日志
logger = setup_logging("db_connection")


class DatabaseConnection:
    """数据库连接管理器"""

    def __init__(self, db_path: str = DB_PATH) -> None:
        """
        初始化数据库连接管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path

        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        logger.info(f"数据库连接管理器已初始化: {db_path}")

    def get_connection(self, timeout: float = 5.0) -> sqlite3.Connection:
        """
        获取数据库连接，带有超时和重试机制

        Args:
            timeout: 连接超时时间（秒）

        Returns:
            sqlite3.Connection: 数据库连接对象

        Raises:
            sqlite3.OperationalError: 当连接失败或超时时抛出
        """
        start_time = time.time()
        last_error: Optional[Exception] = None
        retry_count = 0
        max_retries = 5  # 减少重试次数

        while time.time() - start_time < timeout and retry_count < max_retries:
            try:
                # 设置更短的单次连接超时
                conn = sqlite3.connect(self.db_path, timeout=1.0)

                # 启用外键约束
                conn.execute("PRAGMA foreign_keys = ON")

                # 设置WAL模式以提高并发性能
                conn.execute("PRAGMA journal_mode = WAL")

                # 设置更短的忙等待超时
                conn.execute("PRAGMA busy_timeout = 1000")  # 1秒

                # 设置其他优化参数
                conn.execute("PRAGMA synchronous = NORMAL")
                conn.execute("PRAGMA cache_size = 2000")
                conn.execute("PRAGMA temp_store = MEMORY")

                return conn
            except sqlite3.OperationalError as e:
                last_error = e
                retry_count += 1

                # 如果是"database is locked"错误，等待一段时间后重试
                if "database is locked" in str(e) or "database is busy" in str(e):
                    wait_time = min(0.05 * (2**retry_count), 0.5)  # 指数退避，最大0.5秒
                    logger.debug(
                        f"数据库忙碌，等待 {wait_time:.3f} 秒后重试 (第 {retry_count} 次)"
                    )
                    time.sleep(wait_time)
                else:
                    # 其他操作错误直接抛出
                    raise

        # 如果超时，抛出最后一个错误
        if last_error:
            logger.error(f"数据库连接失败，已重试 {retry_count} 次: {last_error}")
            raise last_error
        else:
            raise sqlite3.OperationalError("数据库连接超时")

    def init_database(self) -> None:
        """
        初始化数据库表

        创建必要的数据库表，包括用户表、接收邮件元数据表和已发送邮件元数据表。
        如果表已存在，则不会重新创建。
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # 创建用户表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    full_name TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_login TEXT
                )
            """
            )

            # 创建接收邮件元数据表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS emails (
                    message_id TEXT PRIMARY KEY,
                    from_addr TEXT NOT NULL,
                    to_addrs TEXT NOT NULL,
                    subject TEXT,
                    date TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    is_read INTEGER DEFAULT 0,
                    is_deleted INTEGER DEFAULT 0,
                    is_spam INTEGER DEFAULT 0,
                    spam_score REAL DEFAULT 0.0,
                    content_path TEXT,
                    is_recalled INTEGER DEFAULT 0,
                    recalled_at TEXT,
                    recalled_by TEXT
                )
            """
            )

            # 创建已发送邮件元数据表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sent_emails (
                    message_id TEXT PRIMARY KEY,
                    from_addr TEXT NOT NULL,
                    to_addrs TEXT NOT NULL,
                    cc_addrs TEXT,
                    bcc_addrs TEXT,
                    subject TEXT,
                    date TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    has_attachments INTEGER DEFAULT 0,
                    content_path TEXT,
                    status TEXT,
                    is_read INTEGER DEFAULT 0,
                    is_spam INTEGER DEFAULT 0,
                    spam_score REAL DEFAULT 0.0,
                    is_recalled INTEGER DEFAULT 0,
                    recalled_at TEXT,
                    recalled_by TEXT
                )
            """
            )

            conn.commit()
            conn.close()

            logger.info("数据库表已初始化")
        except Exception as e:
            logger.error(f"初始化数据库表时出错: {e}")
            raise

    def execute_query(
        self,
        query: str,
        params: tuple = (),
        fetch_one: bool = False,
        fetch_all: bool = False,
    ):
        """
        执行数据库查询

        Args:
            query: SQL查询语句
            params: 查询参数
            fetch_one: 是否返回单行结果
            fetch_all: 是否返回所有结果

        Returns:
            查询结果或None
        """
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row  # 返回字典形式的结果
            cursor = conn.cursor()

            cursor.execute(query, params)

            if fetch_one:
                result = cursor.fetchone()
                conn.close()
                return dict(result) if result else None
            elif fetch_all:
                results = cursor.fetchall()
                conn.close()
                return [dict(row) for row in results]
            else:
                conn.commit()
                conn.close()
                return True

        except Exception as e:
            logger.error(f"执行数据库查询时出错: {e}")
            raise

    def execute_insert(
        self, table: str, data: dict, ignore_duplicates: bool = True
    ) -> bool:
        """
        执行插入操作，带有强化的重试机制

        Args:
            table: 表名
            data: 要插入的数据字典
            ignore_duplicates: 是否忽略重复记录（使用INSERT OR IGNORE）

        Returns:
            bool: 操作是否成功
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                columns = ", ".join(data.keys())
                placeholders = ", ".join(["?" for _ in data])

                # 根据参数选择INSERT语句类型
                if ignore_duplicates:
                    query = f"INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})"
                else:
                    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute(query, tuple(data.values()))

                # 检查是否实际插入了数据
                rows_affected = cursor.rowcount

                conn.commit()
                conn.close()

                if attempt > 0:
                    logger.info(f"插入操作在第 {attempt + 1} 次尝试后成功: {table}")

                # 如果使用INSERT OR IGNORE，即使没有插入也算成功
                if ignore_duplicates:
                    if rows_affected == 0:
                        logger.debug(f"记录已存在，跳过插入: {table}")
                    return True
                else:
                    return rows_affected > 0

            except sqlite3.IntegrityError as e:
                # 主键冲突等完整性错误
                if "UNIQUE constraint failed" in str(e) or "PRIMARY KEY" in str(e):
                    if ignore_duplicates:
                        logger.debug(f"记录已存在（主键重复），跳过插入: {table}")
                        return True
                    else:
                        logger.warning(
                            f"插入数据时发生完整性错误（主键重复）: {table} - {str(e)}"
                        )
                        return False
                else:
                    logger.warning(f"插入数据时发生完整性错误: {table} - {str(e)}")
                    return False
            except sqlite3.OperationalError as e:
                if (
                    "database is locked" in str(e) or "database is busy" in str(e)
                ) and attempt < max_retries - 1:
                    # 使用指数退避，但限制最大等待时间为1秒
                    wait_time = min(0.1 * (2**attempt), 1.0)
                    if attempt == 0:
                        logger.debug(f"插入操作数据库忙碌，开始重试机制: {table}")
                    logger.debug(
                        f"等待 {wait_time:.2f} 秒后进行第 {attempt + 2} 次尝试"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"插入数据时出错: {e}")
                    raise
            except Exception as e:
                logger.error(f"插入数据时出错: {e}")
                raise

        logger.error(f"插入操作在 {max_retries} 次尝试后仍然失败: {table}")
        return False

    def execute_update(
        self, table: str, data: dict, where_clause: str, where_params: tuple = ()
    ) -> bool:
        """
        执行更新操作，带有重试机制

        Args:
            table: 表名
            data: 要更新的数据字典
            where_clause: WHERE子句
            where_params: WHERE子句参数

        Returns:
            bool: 操作是否成功
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
                query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"

                params = tuple(data.values()) + where_params

                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                conn.close()

                return True
            except sqlite3.OperationalError as e:
                if (
                    "database is locked" in str(e) or "database is busy" in str(e)
                ) and attempt < max_retries - 1:
                    wait_time = 0.1 * (2**attempt)
                    logger.debug(f"更新操作数据库忙碌，等待 {wait_time:.2f} 秒后重试")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"更新数据时出错: {e}")
                    raise
            except Exception as e:
                logger.error(f"更新数据时出错: {e}")
                raise

        return False

    def execute_delete(
        self, table: str, where_clause: str, where_params: tuple = ()
    ) -> bool:
        """
        执行删除操作

        Args:
            table: 表名
            where_clause: WHERE子句
            where_params: WHERE子句参数

        Returns:
            bool: 操作是否成功
        """
        try:
            query = f"DELETE FROM {table} WHERE {where_clause}"

            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, where_params)
            conn.commit()
            conn.close()

            return True
        except Exception as e:
            logger.error(f"删除数据时出错: {e}")
            raise
