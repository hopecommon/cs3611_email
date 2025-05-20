"""
数据库处理模块 - 管理邮件元数据和用户信息
"""

import os
import sqlite3
import json
import datetime
import time
import re
from typing import List, Dict, Optional, Tuple, Any, Union, Callable
from pathlib import Path

from common.utils import setup_logging
from common.config import DB_PATH, EMAIL_STORAGE_DIR

# 设置日志
logger = setup_logging("db_handler")


class DatabaseHandler:
    """数据库处理类，管理SQLite数据库"""

    def __init__(self, db_path: str = DB_PATH) -> None:
        """
        初始化数据库处理器

        Args:
            db_path: 数据库文件路径。默认使用配置中的DB_PATH。

        Returns:
            None

        Example:
            ```python
            # 使用默认数据库路径
            db = DatabaseHandler()

            # 使用自定义数据库路径
            db = DatabaseHandler("path/to/custom_db.sqlite")
            ```
        """
        self.db_path = db_path

        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # 初始化数据库
        self.init_db()

        logger.info(f"数据库处理器已初始化: {db_path}")

    def _get_connection(self, timeout: float = 30.0) -> sqlite3.Connection:
        """
        获取数据库连接，带有超时和重试机制

        Args:
            timeout: 连接超时时间（秒）。默认为30秒。

        Returns:
            sqlite3.Connection: 数据库连接对象

        Raises:
            sqlite3.OperationalError: 当连接失败或超时时抛出

        Example:
            ```python
            try:
                conn = db._get_connection()
                # 使用连接...
                conn.close()
            except sqlite3.OperationalError as e:
                print(f"连接数据库失败: {e}")
            ```
        """
        # 设置超时和重试
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

    def init_db(self) -> None:
        """
        初始化数据库表

        创建必要的数据库表，包括用户表、接收邮件元数据表和已发送邮件元数据表。
        如果表已存在，则不会重新创建。

        Returns:
            None

        Raises:
            Exception: 初始化数据库表时可能抛出的异常

        Example:
            ```python
            db = DatabaseHandler()
            # 数据库表已在初始化时创建

            # 手动重新初始化
            db.init_db()
            ```
        """
        try:
            conn = self._get_connection()
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

    def save_received_email_metadata(self, email_obj: Any, content_path: str) -> bool:
        """
        保存接收的邮件元数据

        Args:
            email_obj: Email对象，包含邮件的基本信息（message_id, from_addr, to_addrs, subject, date等）
            content_path: 邮件内容文件路径，指向保存邮件内容的.eml文件

        Returns:
            bool: 操作是否成功，成功返回True，失败返回False

        Example:
            ```python
            from common.models import Email, EmailAddress

            # 创建邮件对象
            email = Email(
                message_id="<example@domain.com>",
                from_addr=EmailAddress(name="Sender", address="sender@example.com"),
                to_addrs=[EmailAddress(name="Recipient", address="recipient@example.com")],
                subject="Test Email",
                date=datetime.datetime.now()
            )

            # 保存邮件内容
            content_path = "data/emails/example.eml"
            with open(content_path, "w") as f:
                f.write("邮件内容...")

            # 保存元数据
            result = db.save_received_email_metadata(email, content_path)
            if result:
                print("邮件元数据保存成功")
            else:
                print("邮件元数据保存失败")
            ```
        """
        try:
            # 将收件人地址列表转换为字符串列表
            to_addrs = [addr.address for addr in email_obj.to_addrs]

            # 计算邮件大小
            try:
                size = os.path.getsize(content_path)
            except:
                size = 0

            # 使用save_email_metadata方法保存元数据
            self.save_email_metadata(
                message_id=email_obj.message_id,
                from_addr=email_obj.from_addr.address,
                to_addrs=to_addrs,
                subject=email_obj.subject,
                date=email_obj.date if email_obj.date else datetime.datetime.now(),
                size=size,
                is_spam=False,
                spam_score=0.0,
            )

            return True
        except Exception as e:
            logger.error(f"保存接收邮件元数据时出错: {e}")
            return False

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
        """
        保存邮件元数据

        Args:
            message_id: 邮件ID
            from_addr: 发件人地址
            to_addrs: 收件人地址列表
            subject: 邮件主题
            date: 邮件日期
            size: 邮件大小（字节）
            is_spam: 是否为垃圾邮件
            spam_score: 垃圾邮件评分（0.0-1.0）
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 转换to_addrs为JSON字符串
            to_addrs_json = json.dumps(to_addrs)

            # 转换日期为ISO格式
            date_str = date.isoformat()

            # 确保邮件ID不包含非法字符
            # 标准化处理：移除两端空格，去掉<>，@替换为_at_
            safe_id = message_id.strip().strip("<>").replace("@", "_at_")
            # 移除Windows文件系统不允许的字符
            safe_id = re.sub(r'[\\/*?:"<>|]', "_", safe_id)
            # 确保没有前导或尾随空格
            safe_id = safe_id.strip()

            # 构建邮件内容路径
            content_path = os.path.join(EMAIL_STORAGE_DIR, f"{safe_id}.eml")

            # 插入数据
            cursor.execute(
                """
            INSERT INTO emails (
                message_id, from_addr, to_addrs, subject, date, size,
                is_spam, spam_score, content_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    message_id,
                    from_addr,
                    to_addrs_json,
                    subject,
                    date_str,
                    size,
                    1 if is_spam else 0,
                    spam_score,
                    content_path,
                ),
            )

            conn.commit()
            conn.close()

            logger.info(f"已保存邮件元数据: {message_id}")
        except sqlite3.IntegrityError:
            # 如果是主键冲突（邮件ID已存在），则忽略
            logger.info(f"邮件元数据已存在（主键冲突），跳过保存: {message_id}")
        except Exception as e:
            logger.error(f"保存邮件元数据时出错: {e}")
            raise

    def save_email_content(self, message_id: str, content: str) -> None:
        """
        保存邮件内容

        Args:
            message_id: 邮件ID
            content: 邮件内容
        """
        try:
            # 确保目录存在
            os.makedirs(EMAIL_STORAGE_DIR, exist_ok=True)

            # 尝试从邮件内容中提取Message-ID
            import email

            try:
                msg = email.message_from_string(content)
                extracted_message_id = msg.get("Message-ID")
                if extracted_message_id:
                    logger.info(f"从邮件内容中提取到Message-ID: {extracted_message_id}")
                    # 使用提取的Message-ID而非传入的message_id
                    message_id = extracted_message_id
            except Exception as e:
                logger.warning(f"从邮件内容中提取Message-ID失败: {e}")

            # 确保邮件ID不包含非法字符
            # 标准化处理：移除两端空格，去掉<>，@替换为_at_
            safe_id = message_id.strip().strip("<>").replace("@", "_at_")
            # 移除Windows文件系统不允许的字符
            safe_id = re.sub(r'[\\/*?:"<>|]', "_", safe_id)
            # 确保没有前导或尾随空格
            safe_id = safe_id.strip()

            # 与客户端保持一致的命名方式，使用Message-ID作为文件名
            filename = f"{safe_id}.eml"
            filepath = os.path.join(EMAIL_STORAGE_DIR, filename)

            # 检查文件是否已存在
            if os.path.exists(filepath):
                logger.info(f"邮件文件已存在，跳过保存: {filepath}")
                return

            # 保存内容
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"已保存邮件内容: {filepath}")
        except Exception as e:
            logger.error(f"保存邮件内容时出错: {e}")
            raise

    def get_email_metadata(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        获取邮件元数据

        Args:
            message_id: 邮件ID

        Returns:
            邮件元数据字典，如果不存在则返回None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询数据
            cursor.execute(
                """
            SELECT * FROM emails WHERE message_id = ?
            """,
                (message_id,),
            )

            row = cursor.fetchone()
            conn.close()

            if row:
                # 转换为字典
                result = dict(row)

                # 解析JSON字段
                result["to_addrs"] = json.loads(result["to_addrs"])

                # 转换布尔值
                result["is_read"] = bool(result["is_read"])
                result["is_deleted"] = bool(result["is_deleted"])
                result["is_spam"] = bool(result["is_spam"])

                return result

            return None
        except Exception as e:
            logger.error(f"获取邮件元数据时出错: {e}")
            return None

    def get_email_content(self, message_id: str) -> Optional[str]:
        """
        获取邮件内容

        根据邮件ID从文件系统中读取邮件内容。首先获取邮件元数据以找到内容文件路径，
        然后读取该文件的内容并返回。如果邮件不存在或读取失败，则返回None。

        Args:
            message_id: 邮件ID，格式通常为 "<identifier@domain>"

        Returns:
            Optional[str]: 邮件内容的字符串表示，如果不存在或读取失败则返回None。
        """
        try:
            # 获取元数据
            metadata = self.get_email_metadata(message_id)
            if not metadata:
                logger.warning(f"未找到邮件元数据: {message_id}")
                return None

            # 尝试使用metadata中的content_path
            if metadata.get("content_path") and os.path.exists(
                metadata["content_path"]
            ):
                try:
                    with open(metadata["content_path"], "r", encoding="utf-8") as f:
                        content = f.read()
                    logger.debug(f"从内容路径读取邮件内容: {metadata['content_path']}")
                    return content
                except Exception as e:
                    logger.error(f"读取邮件内容时出错: {e}")

            # 尝试使用标准化的ID查找文件
            # 标准化处理：移除两端空格，去掉<>，@替换为_at_
            safe_id = message_id.strip().strip("<>").replace("@", "_at_")
            # 移除Windows文件系统不允许的字符
            safe_id = re.sub(r'[\\/*?:"<>|]', "_", safe_id)
            # 确保没有前导或尾随空格
            safe_id = safe_id.strip()

            # 尝试打开文件
            try:
                filepath = os.path.join(EMAIL_STORAGE_DIR, f"{safe_id}.eml")
                if os.path.exists(filepath):
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                    logger.debug(f"从标准化ID路径读取邮件内容: {filepath}")
                    return content
            except Exception as e:
                logger.error(f"读取邮件内容时出错: {e}")

            # 如果所有尝试都失败，尝试从数据库中重新生成邮件内容
            try:
                # 提取关键信息，确保适当的错误处理
                subject = metadata.get("subject", "")
                from_addr = metadata.get("from_addr", "")

                # 处理to_addrs，它可能是字符串、列表或JSON字符串
                to_addrs = metadata.get("to_addrs", [])
                if isinstance(to_addrs, str):
                    try:
                        to_addrs = json.loads(to_addrs)
                    except (json.JSONDecodeError, TypeError):
                        to_addrs = [to_addrs]

                # 格式化收件人列表
                if isinstance(to_addrs, list):
                    if (
                        to_addrs
                        and isinstance(to_addrs[0], dict)
                        and "address" in to_addrs[0]
                    ):
                        to_addr_str = ", ".join(
                            addr["address"] for addr in to_addrs if "address" in addr
                        )
                    else:
                        to_addr_str = ", ".join(str(addr) for addr in to_addrs)
                else:
                    to_addr_str = str(to_addrs)

                # 获取并格式化日期
                date_str = metadata.get("date", "")
                if date_str:
                    try:
                        date = datetime.datetime.fromisoformat(date_str)
                        date_formatted = date.strftime("%a, %d %b %Y %H:%M:%S %z")
                    except (ValueError, TypeError):
                        date_formatted = date_str
                else:
                    date_formatted = datetime.datetime.now().strftime(
                        "%a, %d %b %Y %H:%M:%S %z"
                    )

                # 构建符合RFC标准的邮件内容
                placeholder_content = f"""From: {from_addr}
To: {to_addr_str}
Subject: {subject}
Message-ID: {message_id}
Date: {date_formatted}
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"

[此邮件的原始内容不可用，这是根据元数据生成的占位内容]
"""
                # 记录信息并返回
                logger.warning(f"未找到邮件文件，返回生成的占位内容: {message_id}")
                return placeholder_content
            except Exception as e:
                logger.error(f"生成占位邮件内容时出错: {e}")
                import traceback

                logger.error(f"异常详情: {traceback.format_exc()}")

            # 如果所有尝试都失败
            logger.error(
                f"未找到邮件内容文件: {message_id}, 尝试的路径: {metadata.get('content_path')}, {os.path.join(EMAIL_STORAGE_DIR, f'{safe_id}.eml')}"
            )
            return None
        except Exception as e:
            logger.error(f"获取邮件内容时出错: {e}")
            import traceback

            logger.error(f"异常详情: {traceback.format_exc()}")
            return None

    def get_emails(
        self, folder: str = "inbox", limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取邮件列表

        Args:
            folder: 邮件文件夹，可选值为 "inbox" 或 "sent"
            limit: 返回的最大数量
            offset: 偏移量

        Returns:
            邮件元数据字典列表
        """
        if folder == "sent":
            return self.list_sent_emails(limit=limit, offset=offset)
        else:
            return self.list_emails(limit=limit, offset=offset)

    def list_emails(
        self,
        user_email: Optional[str] = None,
        include_deleted: bool = False,
        include_spam: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        列出邮件

        Args:
            user_email: 用户邮箱（如果指定，则只返回发给该用户的邮件）
            include_deleted: 是否包含已删除的邮件
            include_spam: 是否包含垃圾邮件
            limit: 返回的最大数量
            offset: 偏移量

        Returns:
            邮件元数据字典列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 构建查询
            query = "SELECT * FROM emails WHERE 1=1"
            params = []

            # 用户过滤 - 使用更宽松的匹配方式，确保能找到邮件
            if user_email:
                # 使用多种匹配方式，确保能找到所有相关邮件
                query += """ AND (
                    to_addrs LIKE ? OR
                    to_addrs LIKE ? OR
                    to_addrs LIKE ? OR
                    to_addrs LIKE ? OR
                    to_addrs LIKE ? OR
                    from_addr = ? OR
                    from_addr LIKE ?
                )"""
                params.extend(
                    [
                        f'%"address":"{user_email}"%',  # 匹配JSON中的address字段
                        f'%"{user_email}"%',  # 匹配JSON中的简单字符串
                        f"%<{user_email}>%",  # 匹配尖括号格式
                        f"%{user_email}%",  # 宽松匹配
                        f'%"email":"{user_email}"%',  # 匹配可能的email字段
                        user_email,  # 精确匹配发件人
                        f"%{user_email}%",  # 宽松匹配发件人
                    ]
                )
                logger.info(f"查询邮件，用户邮箱: {user_email}")

                # 添加调试日志
                logger.debug(f"SQL查询: {query}")
                logger.debug(f"参数: {params}")

            # 删除状态过滤
            if not include_deleted:
                query += " AND is_deleted = 0"

            # 垃圾邮件过滤
            if not include_spam:
                query += " AND is_spam = 0"

            # 排序和分页
            query += " ORDER BY date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            # 执行查询
            cursor.execute(query, params)

            # 获取结果
            results = []
            for row in cursor.fetchall():
                # 转换为字典
                item = dict(row)

                # 解析JSON字段，处理多种可能的格式
                try:
                    to_addrs_raw = item["to_addrs"]
                    # 尝试解析为JSON
                    to_addrs = json.loads(to_addrs_raw)

                    # 判断解析结果的类型并处理
                    if isinstance(to_addrs, list):
                        # 可能是简单字符串列表，也可能是对象列表
                        if (
                            to_addrs
                            and isinstance(to_addrs[0], dict)
                            and "address" in to_addrs[0]
                        ):
                            # 转换为简单地址列表以便统一处理
                            to_addrs = [
                                addr["address"]
                                for addr in to_addrs
                                if "address" in addr
                            ]
                    elif isinstance(to_addrs, dict):
                        # 单个地址对象
                        to_addrs = (
                            [to_addrs["address"]] if "address" in to_addrs else []
                        )

                    item["to_addrs"] = to_addrs
                except (json.JSONDecodeError, TypeError, KeyError):
                    # 如果JSON解析失败，尝试其他格式处理，或保持原始值
                    logger.warning(f"解析to_addrs字段失败: {to_addrs_raw}")
                    # 保持原始值
                    item["to_addrs"] = [to_addrs_raw]

                # 转换布尔值
                item["is_read"] = bool(item["is_read"])
                item["is_deleted"] = bool(item["is_deleted"])
                item["is_spam"] = bool(item["is_spam"])

                results.append(item)

            conn.close()
            return results
        except Exception as e:
            logger.error(f"列出邮件时出错: {e}")
            import traceback

            logger.error(f"异常详情: {traceback.format_exc()}")
            return []

    def mark_email_as_read(self, message_id: str) -> bool:
        """
        将邮件标记为已读

        更新数据库中指定邮件的已读状态。此操作将邮件的 is_read 字段设置为 1（True）。

        Args:
            message_id: 邮件ID，格式通常为 "<identifier@domain>"

        Returns:
            bool: 操作是否成功，成功返回True，失败返回False

        Example:
            ```python
            # 标记邮件为已读
            success = db.mark_email_as_read("<example@domain.com>")
            if success:
                print("邮件已标记为已读")
            else:
                print("标记邮件为已读失败")
            ```

        Note:
            此方法只更新数据库中的状态，不会修改邮件文件本身。
            如果邮件不存在，操作将失败并返回False。
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
            UPDATE emails SET is_read = 1 WHERE message_id = ?
            """,
                (message_id,),
            )

            conn.commit()
            conn.close()

            logger.info(f"邮件已标记为已读: {message_id}")
            return True
        except Exception as e:
            logger.error(f"标记邮件为已读时出错: {e}")
            return False

    def mark_email_as_deleted(self, message_id: str) -> bool:
        """
        将邮件标记为已删除

        更新数据库中指定邮件的删除状态。此操作将邮件的 is_deleted 字段设置为 1（True）。
        注意，这只是标记邮件为已删除状态，并不会从数据库或文件系统中实际删除邮件。
        要完全删除邮件，请使用 delete_email_metadata 方法。

        Args:
            message_id: 邮件ID，格式通常为 "<identifier@domain>"

        Returns:
            bool: 操作是否成功，成功返回True，失败返回False

        Example:
            ```python
            # 标记邮件为已删除
            success = db.mark_email_as_deleted("<example@domain.com>")
            if success:
                print("邮件已标记为已删除")
            else:
                print("标记邮件为已删除失败")
            ```

        Note:
            此方法只更新数据库中的状态，不会删除邮件文件本身。
            标记为已删除的邮件默认不会出现在邮件列表中，除非明确包含已删除邮件。
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
            UPDATE emails SET is_deleted = 1 WHERE message_id = ?
            """,
                (message_id,),
            )

            conn.commit()
            conn.close()

            logger.info(f"邮件已标记为已删除: {message_id}")
            return True
        except Exception as e:
            logger.error(f"标记邮件为已删除时出错: {e}")
            return False

    def mark_email_as_spam(self, message_id: str, spam_score: float = 1.0) -> bool:
        """
        将邮件标记为垃圾邮件

        更新数据库中指定邮件的垃圾邮件状态。此操作将邮件的 is_spam 字段设置为 1（True），
        并设置相应的垃圾邮件评分。

        Args:
            message_id: 邮件ID，格式通常为 "<identifier@domain>"
            spam_score: 垃圾邮件评分，范围0.0-1.0，默认为1.0

        Returns:
            bool: 操作是否成功，成功返回True，失败返回False

        Example:
            ```python
            # 标记邮件为垃圾邮件
            success = db.mark_email_as_spam("<example@domain.com>", 0.8)
            ```
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
            UPDATE emails SET is_spam = 1, spam_score = ? WHERE message_id = ?
            """,
                (spam_score, message_id),
            )

            conn.commit()
            conn.close()

            logger.info(f"邮件已标记为垃圾邮件: {message_id}")
            return True
        except Exception as e:
            logger.error(f"标记邮件为垃圾邮件时出错: {e}")
            return False

    def delete_email_metadata(self, message_id: str) -> bool:
        """
        删除邮件元数据

        从数据库中永久删除指定邮件的元数据。注意，此操作不会删除邮件内容文件，
        只会从数据库中删除元数据记录。

        Args:
            message_id: 邮件ID，格式通常为 "<identifier@domain>"

        Returns:
            bool: 操作是否成功，成功返回True，失败返回False

        Example:
            ```python
            # 删除邮件元数据
            success = db.delete_email_metadata("<example@domain.com>")
            ```

        Note:
            此方法与 mark_email_as_deleted 不同，mark_email_as_deleted 只是标记邮件为已删除状态，
            而此方法会从数据库中永久删除邮件记录。
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 删除邮件元数据
            cursor.execute(
                """
                DELETE FROM emails WHERE message_id = ?
                """,
                (message_id,),
            )

            conn.commit()
            conn.close()

            logger.info(f"已删除邮件元数据: {message_id}")
            return True
        except Exception as e:
            logger.error(f"删除邮件元数据时出错: {e}")
            return False

    def save_sent_email_metadata(self, email_obj: Any, content_path: str) -> bool:
        """
        保存已发送邮件的元数据

        将已发送邮件的元数据保存到数据库中。此方法会将Email对象的属性转换为适合存储的格式，
        并将其保存到sent_emails表中。

        Args:
            email_obj: Email对象，包含邮件的基本信息（message_id, from_addr, to_addrs, subject, date等）
            content_path: 邮件内容文件路径，指向保存邮件内容的.eml文件

        Returns:
            bool: 操作是否成功，成功返回True，失败返回False

        Example:
            ```python
            from common.models import Email, EmailAddress

            # 创建邮件对象
            email = Email(
                message_id="<example@domain.com>",
                from_addr=EmailAddress(name="Sender", address="sender@example.com"),
                to_addrs=[EmailAddress(name="Recipient", address="recipient@example.com")],
                subject="Test Email",
                date=datetime.datetime.now()
            )

            # 保存邮件内容
            content_path = "data/emails/example.eml"

            # 保存元数据
            success = db.save_sent_email_metadata(email, content_path)
            ```
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 将收件人列表转换为JSON字符串
            to_addrs_json = json.dumps([addr.to_dict() for addr in email_obj.to_addrs])
            cc_addrs_json = (
                json.dumps([addr.to_dict() for addr in email_obj.cc_addrs])
                if email_obj.cc_addrs
                else None
            )
            bcc_addrs_json = (
                json.dumps([addr.to_dict() for addr in email_obj.bcc_addrs])
                if email_obj.bcc_addrs
                else None
            )

            # 格式化日期
            if email_obj.date:
                date_str = email_obj.date.isoformat()
            else:
                # 如果日期为None，使用当前时间
                date_str = datetime.datetime.now().isoformat()

            # 计算邮件大小
            try:
                size = os.path.getsize(content_path)
            except:
                size = 0

            # 插入数据
            cursor.execute(
                """
            INSERT INTO sent_emails (
                message_id, from_addr, to_addrs, cc_addrs, bcc_addrs,
                subject, date, size, has_attachments, content_path, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    email_obj.message_id,
                    email_obj.from_addr.address,
                    to_addrs_json,
                    cc_addrs_json,
                    bcc_addrs_json,
                    email_obj.subject,
                    date_str,
                    size,
                    1 if email_obj.attachments else 0,
                    content_path,
                    email_obj.status.value,
                ),
            )

            conn.commit()
            conn.close()

            logger.info(f"已保存已发送邮件元数据: {email_obj.message_id}")
            return True
        except Exception as e:
            logger.error(f"保存已发送邮件元数据时出错: {e}")
            return False

    def list_sent_emails(
        self, from_addr: Optional[str] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        列出已发送邮件

        从数据库中获取已发送邮件的列表，可以按发件人过滤，并支持分页。
        结果按日期降序排序（最新的邮件在前）。

        Args:
            from_addr: 发件人地址（如果指定，则只返回该发件人发送的邮件）
            limit: 返回的最大数量，默认为100
            offset: 偏移量，用于分页，默认为0

        Returns:
            List[Dict[str, Any]]: 已发送邮件元数据字典列表，每个字典包含邮件的所有属性

        Example:
            ```python
            # 获取所有已发送邮件
            emails = db.list_sent_emails()

            # 获取特定发件人的邮件
            emails = db.list_sent_emails(from_addr="sender@example.com")

            # 分页获取邮件
            first_page = db.list_sent_emails(limit=10, offset=0)
            second_page = db.list_sent_emails(limit=10, offset=10)
            ```
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 构建查询
            query = "SELECT * FROM sent_emails WHERE 1=1"
            params = []

            # 发件人过滤
            if from_addr:
                query += " AND from_addr = ?"
                params.append(from_addr)

            # 排序和分页
            query += " ORDER BY date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            # 执行查询
            cursor.execute(query, params)

            # 获取结果
            results = []
            for row in cursor.fetchall():
                # 转换为字典
                item = dict(row)

                # 解析JSON字段
                item["to_addrs"] = json.loads(item["to_addrs"])
                if item["cc_addrs"]:
                    item["cc_addrs"] = json.loads(item["cc_addrs"])
                if item["bcc_addrs"]:
                    item["bcc_addrs"] = json.loads(item["bcc_addrs"])

                # 转换布尔值
                item["has_attachments"] = bool(item["has_attachments"])

                results.append(item)

            conn.close()
            return results
        except Exception as e:
            logger.error(f"列出已发送邮件时出错: {e}")
            return []

    def get_sent_email_metadata(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        获取已发送邮件元数据

        Args:
            message_id: 邮件ID

        Returns:
            已发送邮件元数据字典，如果不存在则返回None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 查询数据
            cursor.execute(
                """
            SELECT * FROM sent_emails WHERE message_id = ?
            """,
                (message_id,),
            )

            row = cursor.fetchone()
            conn.close()

            if row:
                # 转换为字典
                result = dict(row)

                # 解析JSON字段
                result["to_addrs"] = json.loads(result["to_addrs"])
                if result["cc_addrs"]:
                    result["cc_addrs"] = json.loads(result["cc_addrs"])
                if result["bcc_addrs"]:
                    result["bcc_addrs"] = json.loads(result["bcc_addrs"])

                # 转换布尔值
                result["has_attachments"] = bool(result["has_attachments"])

                return result

            return None
        except Exception as e:
            logger.error(f"获取已发送邮件元数据时出错: {e}")
            return None

    def get_sent_email_content(self, message_id: str) -> Optional[str]:
        """
        获取已发送邮件内容

        Args:
            message_id: 邮件ID

        Returns:
            邮件内容，如果不存在则返回None
        """
        try:
            # 获取元数据
            metadata = self.get_sent_email_metadata(message_id)
            if not metadata or not metadata["content_path"]:
                return None

            # 读取内容
            with open(metadata["content_path"], "r", encoding="utf-8") as f:
                content = f.read()

            return content
        except Exception as e:
            logger.error(f"获取已发送邮件内容时出错: {e}")
            return None

    def delete_sent_email_metadata(self, message_id: str) -> bool:
        """
        删除已发送邮件元数据

        Args:
            message_id: 邮件ID

        Returns:
            操作是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 删除邮件元数据
            cursor.execute(
                """
                DELETE FROM sent_emails WHERE message_id = ?
                """,
                (message_id,),
            )

            conn.commit()
            conn.close()

            logger.info(f"已删除已发送邮件元数据: {message_id}")
            return True
        except Exception as e:
            logger.error(f"删除已发送邮件元数据时出错: {e}")
            return False

    def search_emails(
        self,
        query: str,
        search_in: Optional[List[str]] = None,
        include_sent: bool = True,
        include_received: bool = True,
        include_deleted: bool = False,
        include_spam: bool = False,
        search_content: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        搜索邮件

        在数据库中搜索符合条件的邮件。可以指定搜索范围、包含的邮件类型和其他过滤条件。
        结果按日期降序排序（最新的邮件在前）。

        Args:
            query: 搜索关键词，将在指定字段中查找包含此关键词的邮件
            search_in: 要搜索的字段列表，如['subject', 'from_addr', 'to_addrs']
                       如果为None，则默认搜索主题、发件人和收件人
            include_sent: 是否包含已发送邮件，默认为True
            include_received: 是否包含接收邮件，默认为True
            include_deleted: 是否包含已删除邮件，默认为False
            include_spam: 是否包含垃圾邮件，默认为False
            search_content: 是否搜索邮件正文内容（会降低搜索速度），默认为False
            limit: 返回的最大数量，默认为100

        Returns:
            List[Dict[str, Any]]: 符合条件的邮件元数据字典列表，每个字典包含一个额外的'type'字段，
            表示邮件类型（'sent'或'received'）

        Example:
            ```python
            # 基本搜索
            emails = db.search_emails("important")

            # 只搜索主题
            emails = db.search_emails("meeting", search_in=["subject"])

            # 只搜索已发送邮件
            emails = db.search_emails("report", include_received=False)

            # 搜索邮件内容
            emails = db.search_emails("confidential", search_content=True)

            # 包含已删除邮件
            emails = db.search_emails("old", include_deleted=True)
            ```
        """
        if not query:
            return []

        # 默认搜索字段
        if not search_in:
            search_in = ["subject", "from_addr", "to_addrs"]

        results = []

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 搜索已接收邮件
            if include_received:
                # 构建查询
                query_parts = []
                params = []

                # 添加搜索条件
                for field in search_in:
                    if field in ["subject", "from_addr"]:
                        query_parts.append(f"{field} LIKE ?")
                        params.append(f"%{query}%")
                    elif field == "to_addrs":
                        query_parts.append(f"{field} LIKE ?")
                        params.append(f"%{query}%")

                if not query_parts:
                    # 如果没有有效的搜索字段，跳过搜索
                    pass
                else:
                    # 构建完整查询
                    sql_query = f"""
                    SELECT *, 'received' as type FROM emails
                    WHERE ({' OR '.join(query_parts)})
                    """

                    # 添加删除和垃圾邮件过滤
                    if not include_deleted:
                        sql_query += " AND is_deleted = 0"
                    if not include_spam:
                        sql_query += " AND is_spam = 0"

                    # 添加排序和限制
                    sql_query += " ORDER BY date DESC LIMIT ?"
                    params.append(limit)

                    # 执行查询
                    cursor.execute(sql_query, params)

                    # 处理结果
                    for row in cursor.fetchall():
                        item = dict(row)

                        # 解析JSON字段
                        item["to_addrs"] = json.loads(item["to_addrs"])

                        # 转换布尔值
                        item["is_read"] = bool(item["is_read"])
                        item["is_deleted"] = bool(item["is_deleted"])
                        item["is_spam"] = bool(item["is_spam"])

                        results.append(item)

            # 搜索已发送邮件
            if include_sent:
                # 构建查询
                query_parts = []
                params = []

                # 添加搜索条件
                for field in search_in:
                    if field in ["subject", "from_addr"]:
                        query_parts.append(f"{field} LIKE ?")
                        params.append(f"%{query}%")
                    elif field == "to_addrs":
                        query_parts.append(f"{field} LIKE ?")
                        params.append(f"%{query}%")

                if not query_parts:
                    # 如果没有有效的搜索字段，跳过搜索
                    pass
                else:
                    # 构建完整查询
                    sql_query = f"""
                    SELECT *, 'sent' as type FROM sent_emails
                    WHERE ({' OR '.join(query_parts)})
                    """

                    # 添加排序和限制
                    sql_query += " ORDER BY date DESC LIMIT ?"
                    params.append(limit)

                    # 执行查询
                    cursor.execute(sql_query, params)

                    # 处理结果
                    for row in cursor.fetchall():
                        item = dict(row)

                        # 解析JSON字段
                        item["to_addrs"] = json.loads(item["to_addrs"])
                        if item["cc_addrs"]:
                            item["cc_addrs"] = json.loads(item["cc_addrs"])
                        if item["bcc_addrs"]:
                            item["bcc_addrs"] = json.loads(item["bcc_addrs"])

                        # 转换布尔值
                        item["has_attachments"] = bool(item["has_attachments"])

                        results.append(item)

            conn.close()

            # 如果需要搜索邮件正文内容
            if search_content and results:
                # 创建一个新的结果列表，用于存储匹配正文内容的邮件
                content_results = []

                # 导入必要的模块
                from email import policy
                from email.parser import BytesParser

                # 遍历所有结果
                for item in results:
                    content_path = item.get("content_path")
                    if not content_path or not os.path.exists(content_path):
                        continue

                    try:
                        # 解析.eml文件
                        with open(content_path, "rb") as f:
                            parser = BytesParser(policy=policy.default)
                            msg = parser.parse(f)

                        # 提取纯文本内容
                        text_content = ""

                        # 如果是简单邮件
                        if msg.get_content_type() == "text/plain":
                            text_content = msg.get_content()
                        else:
                            # 遍历所有部分
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    text_content += part.get_content()

                        # 如果正文包含搜索关键词，则添加到结果中
                        if query.lower() in text_content.lower():
                            content_results.append(item)
                    except Exception as e:
                        logger.error(f"搜索邮件正文时出错: {e}")

                # 如果没有搜索到正文内容，则使用原始结果
                if content_results:
                    # 合并结果（去重）
                    seen_ids = set()
                    merged_results = []

                    # 先添加正文匹配的结果
                    for item in content_results:
                        if item["message_id"] not in seen_ids:
                            seen_ids.add(item["message_id"])
                            merged_results.append(item)

                    # 再添加其他结果
                    for item in results:
                        if item["message_id"] not in seen_ids:
                            seen_ids.add(item["message_id"])
                            merged_results.append(item)

                    results = merged_results

            # 按日期排序结果
            results.sort(key=lambda x: x["date"], reverse=True)

            # 限制结果数量
            if len(results) > limit:
                results = results[:limit]

            return results
        except Exception as e:
            logger.error(f"搜索邮件时出错: {e}")
            return []
