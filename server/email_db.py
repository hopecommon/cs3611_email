"""
邮件数据库接口 - 提供简化的数据库操作接口

此模块封装了DatabaseHandler，提供更简洁的API，统一命名风格，
并添加了一些额外功能。主要用于邮件元数据的存储、检索和管理。
"""

import sqlite3
import datetime
from typing import List, Dict, Any, Optional

from common.utils import setup_logging
from common.config import DB_PATH
from server.db_handler import DatabaseHandler

# 设置日志
logger = setup_logging("email_db")


class EmailDB:
    """
    邮件数据库简化接口

    提供统一、简洁的API来操作邮件数据库，包括邮件标记、获取、搜索和保存功能。
    此类封装了DatabaseHandler，使用更一致的命名约定，并添加了一些额外功能。

    主要功能:
    - 邮件标记: 已读/未读、删除、垃圾邮件
    - 邮件获取: 单封邮件、邮件列表
    - 邮件搜索: 关键词搜索、日期搜索
    - 邮件保存: 接收邮件、发送邮件
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        """
        初始化邮件数据库接口

        Args:
            db_path: 数据库文件路径，默认使用配置中的DB_PATH

        Example:
            ```python
            # 使用默认数据库路径
            db = EmailDB()

            # 使用自定义数据库路径
            db = EmailDB("path/to/custom_db.sqlite")
            ```
        """
        self.db = DatabaseHandler(db_path)
        logger.info(f"邮件数据库接口已初始化: {db_path}")

    # 邮件标记方法
    def mark_as_read(self, message_id: str) -> bool:
        """
        将邮件标记为已读

        Args:
            message_id: 邮件ID，格式通常为 "<identifier@domain>"

        Returns:
            bool: 操作是否成功，成功返回True，失败返回False

        Example:
            ```python
            success = db.mark_as_read("<example@domain.com>")
            ```
        """
        return self.db.mark_email_as_read(message_id)

    def mark_as_unread(self, message_id: str) -> bool:
        """
        将邮件标记为未读

        Args:
            message_id: 邮件ID，格式通常为 "<identifier@domain>"

        Returns:
            bool: 操作是否成功

        Example:
            success = db.mark_as_unread("<example@domain.com>")
        """
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE emails SET is_read = 0 WHERE message_id = ?", (message_id,)
            )
            conn.commit()
            conn.close()
            logger.info(f"邮件已标记为未读: {message_id}")
            return True
        except Exception as e:
            logger.error(f"标记邮件为未读时出错: {e}")
            return False

    def mark_as_deleted(self, message_id: str) -> bool:
        """
        将邮件标记为已删除

        Args:
            message_id: 邮件ID，格式通常为 "<identifier@domain>"

        Returns:
            bool: 操作是否成功，成功返回True，失败返回False

        Example:
            ```python
            success = db.mark_as_deleted("<example@domain.com>")
            ```
        """
        return self.db.mark_email_as_deleted(message_id)

    def mark_as_spam(self, message_id: str, spam_score: float = 1.0) -> bool:
        """
        将邮件标记为垃圾邮件

        Args:
            message_id: 邮件ID，格式通常为 "<identifier@domain>"
            spam_score: 垃圾邮件评分，范围0.0-1.0，默认为1.0

        Returns:
            bool: 操作是否成功，成功返回True，失败返回False

        Example:
            ```python
            success = db.mark_as_spam("<example@domain.com>", 0.8)
            ```
        """
        return self.db.mark_email_as_spam(message_id, spam_score)

    # 邮件获取方法
    def get_email(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        获取邮件元数据和内容

        Args:
            message_id: 邮件ID，格式通常为 "<identifier@domain>"

        Returns:
            Optional[Dict[str, Any]]: 邮件元数据和内容的字典，如果不存在则返回None

        Example:
            ```python
            email = db.get_email("<example@domain.com>")
            if email:
                print(f"主题: {email['subject']}")
                print(f"发件人: {email['from_addr']}")
                if 'content' in email:
                    print(f"内容长度: {len(email['content'])}")
            ```
        """
        logger.info(f"获取邮件: {message_id}")

        # 先尝试获取接收邮件的元数据
        metadata = self.db.get_email_metadata(message_id)
        if metadata:
            logger.info(f"找到接收邮件元数据: {message_id}")

            # 如果有content_path，直接从文件读取内容
            if "content_path" in metadata and metadata["content_path"]:
                content_path = metadata["content_path"]
                logger.info(f"尝试从文件读取内容: {content_path}")
                try:
                    with open(content_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        metadata["content"] = content
                        logger.info(f"成功从文件读取内容: {len(content)} 字节")
                except Exception as e:
                    logger.error(f"读取邮件内容文件时出错: {e}")
                    # 尝试使用db_handler的方法获取内容
                    content = self.db.get_email_content(message_id)
                    if content:
                        metadata["content"] = content
                        logger.info(f"成功从数据库获取内容: {len(content)} 字节")
                    else:
                        logger.warning(f"无法从数据库获取内容: {message_id}")
            else:
                logger.info(f"邮件元数据中没有content_path: {message_id}")
                # 尝试使用db_handler的方法获取内容
                content = self.db.get_email_content(message_id)
                if content:
                    metadata["content"] = content
                    logger.info(f"成功从数据库获取内容: {len(content)} 字节")
                else:
                    logger.warning(f"无法从数据库获取内容: {message_id}")
            return metadata

        # 如果不是接收邮件，尝试获取已发送邮件的元数据
        sent_metadata = self.db.get_sent_email_metadata(message_id)
        if sent_metadata:
            logger.info(f"找到已发送邮件元数据: {message_id}")

            # 如果有content_path，直接从文件读取内容
            if "content_path" in sent_metadata and sent_metadata["content_path"]:
                content_path = sent_metadata["content_path"]
                logger.info(f"尝试从文件读取内容: {content_path}")
                try:
                    with open(content_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        sent_metadata["content"] = content
                        logger.info(f"成功从文件读取内容: {len(content)} 字节")
                except Exception as e:
                    logger.error(f"读取邮件内容文件时出错: {e}")
                    # 尝试使用db_handler的方法获取内容
                    content = self.db.get_sent_email_content(message_id)
                    if content:
                        sent_metadata["content"] = content
                        logger.info(f"成功从数据库获取内容: {len(content)} 字节")
                    else:
                        logger.warning(f"无法从数据库获取内容: {message_id}")
            else:
                logger.info(f"邮件元数据中没有content_path: {message_id}")
                # 尝试使用db_handler的方法获取内容
                content = self.db.get_sent_email_content(message_id)
                if content:
                    sent_metadata["content"] = content
                    logger.info(f"成功从数据库获取内容: {len(content)} 字节")
                else:
                    logger.warning(f"无法从数据库获取内容: {message_id}")
            return sent_metadata

        logger.warning(f"未找到邮件元数据: {message_id}")
        return None

    def list_emails(
        self, folder: str = "inbox", limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        列出邮件

        Args:
            folder: 邮件文件夹，可选值为 "inbox" 或 "sent"
            limit: 返回的最大数量
            offset: 偏移量

        Returns:
            List[Dict[str, Any]]: 邮件元数据字典列表

        Example:
            ```python
            # 获取收件箱中的邮件
            inbox_emails = db.list_emails("inbox", limit=10)

            # 获取已发送邮件
            sent_emails = db.list_emails("sent", limit=10)
            ```
        """
        return self.db.get_emails(folder, limit, offset)

    # 搜索方法
    def search(self, query: str, **options) -> List[Dict[str, Any]]:
        """
        搜索邮件的统一接口

        Args:
            query: 搜索关键词
            **options: 搜索选项，可包含以下参数：
                - search_in: 要搜索的字段列表，如['subject', 'from_addr']
                - include_sent: 是否包含已发送邮件
                - include_received: 是否包含接收邮件
                - include_deleted: 是否包含已删除邮件
                - include_spam: 是否包含垃圾邮件
                - search_content: 是否搜索邮件正文内容
                - limit: 返回的最大数量
                - offset: 偏移量

        Returns:
            List[Dict[str, Any]]: 符合条件的邮件元数据字典列表

        Example:
            ```python
            # 搜索主题包含"重要"的邮件
            emails = db.search("重要", search_in=["subject"])

            # 搜索所有来自特定发件人的邮件
            emails = db.search("example@gmail.com", search_in=["from_addr"])

            # 搜索邮件内容
            emails = db.search("关键词", search_content=True)
            ```
        """
        # 如果需要搜索内容，我们需要先获取所有邮件，然后手动搜索内容
        if options.get("search_content"):
            logger.info(f"搜索邮件内容: {query}")

            # 获取所有邮件（不包括内容搜索）
            search_options = options.copy()
            search_options["search_content"] = False

            # 如果没有指定搜索字段，使用所有字段
            if "search_in" not in search_options:
                search_options["search_in"] = ["subject", "from_addr", "to_addrs"]

            # 获取所有邮件
            results = self.db.search_emails(query, **search_options)
            logger.info(f"初步搜索结果: {len(results)}封邮件")

            # 如果没有结果，尝试获取所有邮件
            if not results:
                logger.info("没有初步搜索结果，尝试获取所有邮件")
                # 获取所有已发送邮件
                sent_emails = self.list_emails(folder="sent")
                # 获取所有接收邮件
                received_emails = self.list_emails(folder="inbox")
                # 合并结果
                results = sent_emails + received_emails
                logger.info(f"获取到所有邮件: {len(results)}封")

            # 手动搜索内容
            content_results = []
            for item in results:
                message_id = item.get("message_id")
                if not message_id:
                    continue

                # 获取邮件内容
                email_with_content = self.get_email(message_id)
                if not email_with_content or "content" not in email_with_content:
                    logger.warning(f"无法获取邮件内容: {message_id}")
                    continue

                content = email_with_content.get("content", "")
                if query.lower() in content.lower():
                    logger.info(f"找到匹配内容的邮件: {message_id}")
                    content_results.append(item)

            logger.info(f"内容搜索结果: {len(content_results)}封邮件")
            return content_results
        else:
            # 使用数据库搜索
            return self.db.search_emails(query, **options)

    def search_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """
        按日期搜索邮件

        Args:
            date_str: 日期字符串，格式为 "YYYY-MM-DD"

        Returns:
            List[Dict[str, Any]]: 符合条件的邮件元数据字典列表

        Example:
            ```python
            # 搜索特定日期的邮件
            emails = db.search_by_date("2023-01-01")
            ```
        """
        try:
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            date_str = date.strftime("%Y-%m-%d")
            return self.db.search_emails(date_str, search_in=["date"])
        except ValueError:
            logger.error(f"日期格式无效: {date_str}")
            return []

    # 邮件保存方法
    def save_received_email(self, email_obj: Any, content_path: str) -> bool:
        """
        保存接收的邮件

        Args:
            email_obj: Email对象
            content_path: 邮件内容文件路径

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

            # 保存邮件
            success = db.save_received_email(email, content_path)
            ```
        """
        return self.db.save_received_email_metadata(email_obj, content_path)

    def save_sent_email(self, email_obj: Any, content_path: str) -> bool:
        """
        保存已发送的邮件

        Args:
            email_obj: Email对象
            content_path: 邮件内容文件路径

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

            # 保存邮件
            success = db.save_sent_email(email, content_path)
            ```
        """
        return self.db.save_sent_email_metadata(email_obj, content_path)
