"""
优化的数据库处理器 - 专门用于高并发邮件存储
"""

import os
import sys
import sqlite3
import threading
import queue
import time
import json
import re
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.config import DB_PATH, EMAIL_STORAGE_DIR

# 设置日志
logger = setup_logging("optimized_db_handler")


class OptimizedDatabaseHandler:
    """优化的数据库处理器，支持高并发写入"""

    def __init__(self, db_path: str = DB_PATH, batch_size: int = 10, flush_interval: float = 1.0):
        self.db_path = db_path
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        os.makedirs(EMAIL_STORAGE_DIR, exist_ok=True)
        
        # 批量操作队列
        self.metadata_queue = queue.Queue()
        self.content_queue = queue.Queue()
        
        # 控制标志
        self.running = True
        self.batch_thread = None
        
        # 初始化数据库
        self.init_db()
        
        # 启动批量处理线程
        self.start_batch_processor()
        
        logger.info(f"优化数据库处理器已初始化: {db_path}")

    def init_db(self) -> None:
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            
            # 设置SQLite优化参数
            cursor.execute("PRAGMA journal_mode = WAL")  # 使用WAL模式提高并发性
            cursor.execute("PRAGMA synchronous = NORMAL")  # 平衡性能和安全性
            cursor.execute("PRAGMA cache_size = 10000")  # 增加缓存大小
            cursor.execute("PRAGMA temp_store = MEMORY")  # 临时表存储在内存中
            cursor.execute("PRAGMA foreign_keys = ON")

            # 创建用户表
            cursor.execute("""
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
            """)

            # 创建接收邮件元数据表
            cursor.execute("""
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
            """)

            # 创建已发送邮件元数据表
            cursor.execute("""
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
            """)

            # 创建索引以提高查询性能
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_emails_date ON emails(date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_emails_from_addr ON emails(from_addr)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sent_emails_date ON sent_emails(date)")

            conn.commit()
            conn.close()

            logger.info("优化数据库表已初始化")
        except Exception as e:
            logger.error(f"初始化数据库表时出错: {e}")
            raise

    def start_batch_processor(self):
        """启动批量处理线程"""
        self.batch_thread = threading.Thread(target=self._batch_processor, daemon=True)
        self.batch_thread.start()
        logger.info("批量处理线程已启动")

    def _batch_processor(self):
        """批量处理线程主循环"""
        metadata_batch = []
        content_batch = []
        last_flush_time = time.time()

        while self.running:
            try:
                current_time = time.time()
                
                # 收集元数据
                try:
                    while len(metadata_batch) < self.batch_size:
                        item = self.metadata_queue.get(timeout=0.1)
                        metadata_batch.append(item)
                except queue.Empty:
                    pass

                # 收集内容数据
                try:
                    while len(content_batch) < self.batch_size:
                        item = self.content_queue.get(timeout=0.1)
                        content_batch.append(item)
                except queue.Empty:
                    pass

                # 检查是否需要刷新
                should_flush = (
                    len(metadata_batch) >= self.batch_size or
                    len(content_batch) >= self.batch_size or
                    (current_time - last_flush_time) >= self.flush_interval
                )

                if should_flush and (metadata_batch or content_batch):
                    # 批量处理元数据
                    if metadata_batch:
                        self._batch_save_metadata(metadata_batch)
                        metadata_batch.clear()

                    # 批量处理内容
                    if content_batch:
                        self._batch_save_content(content_batch)
                        content_batch.clear()

                    last_flush_time = current_time

                # 短暂休眠避免CPU占用过高
                time.sleep(0.01)

            except Exception as e:
                logger.error(f"批量处理线程出错: {e}")
                time.sleep(0.1)

        # 处理剩余的数据
        if metadata_batch:
            self._batch_save_metadata(metadata_batch)
        if content_batch:
            self._batch_save_content(content_batch)

    def _batch_save_metadata(self, batch: List[Dict[str, Any]]):
        """批量保存邮件元数据"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()

            # 准备批量插入数据
            insert_data = []
            for item in batch:
                # 转换to_addrs为JSON字符串
                to_addrs_json = json.dumps(item['to_addrs'])
                
                # 转换日期为ISO格式
                date_str = item['date'].isoformat()
                
                # 构建邮件内容路径
                safe_id = self._sanitize_message_id(item['message_id'])
                content_path = os.path.join(EMAIL_STORAGE_DIR, f"{safe_id}.eml")
                
                insert_data.append((
                    item['message_id'],
                    item['from_addr'],
                    to_addrs_json,
                    item['subject'],
                    date_str,
                    item['size'],
                    1 if item['is_spam'] else 0,
                    item['spam_score'],
                    content_path,
                ))

            # 批量插入
            cursor.executemany("""
                INSERT OR IGNORE INTO emails (
                    message_id, from_addr, to_addrs, subject, date, size,
                    is_spam, spam_score, content_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, insert_data)

            conn.commit()
            conn.close()

            logger.debug(f"批量保存了 {len(batch)} 条邮件元数据")

        except Exception as e:
            logger.error(f"批量保存邮件元数据时出错: {e}")

    def _batch_save_content(self, batch: List[Dict[str, Any]]):
        """批量保存邮件内容"""
        try:
            for item in batch:
                message_id = item['message_id']
                content = item['content']
                
                # 标准化文件名
                safe_id = self._sanitize_message_id(message_id)
                filename = f"{safe_id}.eml"
                filepath = os.path.join(EMAIL_STORAGE_DIR, filename)

                # 检查文件是否已存在
                if os.path.exists(filepath):
                    continue

                # 保存内容
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)

            logger.debug(f"批量保存了 {len(batch)} 个邮件内容文件")

        except Exception as e:
            logger.error(f"批量保存邮件内容时出错: {e}")

    def _sanitize_message_id(self, message_id: str) -> str:
        """标准化邮件ID为安全的文件名"""
        safe_id = message_id.strip().strip("<>").replace("@", "_at_")
        safe_id = re.sub(r'[\\/*?:"<>|]', "_", safe_id)
        return safe_id.strip()

    def save_email_metadata(
        self,
        message_id: str,
        from_addr: str,
        to_addrs: List[str],
        subject: str,
        date: datetime.datetime,
        size: int,
        is_spam: bool = False,
        spam_score: float = 0.0,
    ) -> None:
        """异步保存邮件元数据到队列"""
        metadata_item = {
            'message_id': message_id,
            'from_addr': from_addr,
            'to_addrs': to_addrs,
            'subject': subject,
            'date': date,
            'size': size,
            'is_spam': is_spam,
            'spam_score': spam_score,
        }
        
        try:
            self.metadata_queue.put(metadata_item, timeout=1.0)
            logger.debug(f"邮件元数据已加入队列: {message_id}")
        except queue.Full:
            logger.warning(f"元数据队列已满，丢弃邮件: {message_id}")

    def save_email_content(self, message_id: str, content: str) -> None:
        """异步保存邮件内容到队列"""
        content_item = {
            'message_id': message_id,
            'content': content,
        }
        
        try:
            self.content_queue.put(content_item, timeout=1.0)
            logger.debug(f"邮件内容已加入队列: {message_id}")
        except queue.Full:
            logger.warning(f"内容队列已满，丢弃邮件: {message_id}")

    def get_email_metadata(self, message_id: str) -> Optional[Dict[str, Any]]:
        """获取邮件元数据（同步操作）"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM emails WHERE message_id = ?", (message_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                result = dict(row)
                result["to_addrs"] = json.loads(result["to_addrs"])
                result["is_read"] = bool(result["is_read"])
                result["is_deleted"] = bool(result["is_deleted"])
                result["is_spam"] = bool(result["is_spam"])
                return result

            return None
        except Exception as e:
            logger.error(f"获取邮件元数据时出错: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM emails")
            email_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM sent_emails")
            sent_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'email_count': email_count,
                'sent_count': sent_count,
                'user_count': user_count,
                'metadata_queue_size': self.metadata_queue.qsize(),
                'content_queue_size': self.content_queue.qsize(),
            }
        except Exception as e:
            logger.error(f"获取统计信息时出错: {e}")
            return {}

    def stop(self):
        """停止批量处理器"""
        self.running = False
        if self.batch_thread and self.batch_thread.is_alive():
            self.batch_thread.join(timeout=5.0)
        logger.info("优化数据库处理器已停止")

    def __del__(self):
        """析构函数"""
        self.stop()
