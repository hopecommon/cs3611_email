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

    def get_connection(self, timeout: float = 30.0) -> sqlite3.Connection:
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

        while time.time() - start_time < timeout:
            try:
                # 设置超时和忙等待重试
                conn = sqlite3.connect(self.db_path, timeout=5.0)
                # 启用外键约束
                conn.execute("PRAGMA foreign_keys = ON")
                return conn
            except sqlite3.OperationalError as e:
                last_error = e
                # 如果是"database is locked"错误，等待一段时间后重试
                if "database is locked" in str(e):
                    time.sleep(0.5)
                else:
                    # 其他操作错误直接抛出
                    raise

        # 如果超时，抛出最后一个错误
        if last_error:
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
                    content_path TEXT
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
                    status TEXT
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

    def execute_insert(self, table: str, data: dict) -> bool:
        """
        执行插入操作

        Args:
            table: 表名
            data: 要插入的数据字典

        Returns:
            bool: 操作是否成功
        """
        try:
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?" for _ in data])
            query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, tuple(data.values()))
            conn.commit()
            conn.close()

            return True
        except sqlite3.IntegrityError:
            # 主键冲突等完整性错误
            logger.warning(f"插入数据时发生完整性错误: {table}")
            return False
        except Exception as e:
            logger.error(f"插入数据时出错: {e}")
            raise

    def execute_update(
        self, table: str, data: dict, where_clause: str, where_params: tuple = ()
    ) -> bool:
        """
        执行更新操作

        Args:
            table: 表名
            data: 要更新的数据字典
            where_clause: WHERE子句
            where_params: WHERE子句参数

        Returns:
            bool: 操作是否成功
        """
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
        except Exception as e:
            logger.error(f"更新数据时出错: {e}")
            raise

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
