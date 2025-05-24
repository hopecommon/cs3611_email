# -*- coding: utf-8 -*-
"""
重构后的POP3客户端
使用模块化设计，将原来的1371行代码拆分为多个专门的模块
"""

from typing import List, Tuple, Optional, Literal
import datetime

from common.utils import setup_logging
from common.models import Email
from common.config import POP3_SERVER
from client.pop3_connection_manager import POP3ConnectionManager
from client.pop3_email_retriever import POP3EmailRetriever

# 设置日志
logger = setup_logging("pop3_client_refactored")


class POP3ClientRefactored:
    """重构后的POP3客户端类，处理邮件接收"""

    def __init__(
        self,
        host: str = POP3_SERVER["host"],
        port: int = POP3_SERVER["port"],
        use_ssl: bool = POP3_SERVER["use_ssl"],
        username: Optional[str] = None,
        password: Optional[str] = None,
        auth_method: Optional[Literal["BASIC", "APOP", "AUTO"]] = "AUTO",
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        初始化POP3客户端

        Args:
            host: POP3服务器主机名
            port: POP3服务器端口
            use_ssl: 是否使用SSL/TLS
            username: 认证用户名
            password: 认证密码
            auth_method: 认证方法，可选值为"BASIC"、"APOP"或"AUTO"（自动选择）
            timeout: 连接超时时间（秒）
            max_retries: 最大重试次数
        """
        # 创建连接管理器
        self.connection_manager = POP3ConnectionManager(
            host=host,
            port=port,
            use_ssl=use_ssl,
            username=username,
            password=password,
            auth_method=auth_method,
            timeout=timeout,
            max_retries=max_retries,
        )

        # 创建邮件检索器
        self.email_retriever = POP3EmailRetriever(self.connection_manager)

        logger.info(f"POP3客户端已初始化: {host}:{port} (SSL: {use_ssl})")

    def connect(self) -> None:
        """
        连接到POP3服务器

        Raises:
            poplib.error_proto: 连接失败时抛出
        """
        self.connection_manager.connect()

    def disconnect(self) -> None:
        """断开与POP3服务器的连接"""
        self.connection_manager.disconnect()

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connection_manager.is_connected()

    def get_mailbox_status(self) -> Tuple[int, int]:
        """
        获取邮箱状态

        Returns:
            (邮件数量, 邮箱大小(字节))元组
        """
        return self.email_retriever.get_mailbox_status()

    def list_emails(self) -> List[Tuple[int, int]]:
        """
        列出所有邮件

        Returns:
            [(邮件索引, 邮件大小), ...]列表
        """
        return self.email_retriever.list_emails()

    def retrieve_email(self, msg_num: int, delete: bool = False) -> Optional[Email]:
        """
        获取指定邮件

        Args:
            msg_num: 邮件索引
            delete: 获取后是否删除

        Returns:
            Email对象，如果获取失败则返回None
        """
        return self.email_retriever.retrieve_email(msg_num, delete)

    def retrieve_all_emails(
        self,
        delete: bool = False,
        limit: int = None,
        since_date: datetime.datetime = None,
        only_unread: bool = False,
        from_addr: str = None,
        subject_contains: str = None,
    ) -> List[Email]:
        """
        获取所有邮件，支持多种过滤选项

        Args:
            delete: 获取后是否删除
            limit: 最多获取的邮件数量
            since_date: 只获取该日期之后的邮件
            only_unread: 是否只获取未读邮件（注意：POP3协议本身不支持邮件状态，此功能依赖本地数据库）
            from_addr: 只获取来自特定发件人的邮件
            subject_contains: 只获取主题包含特定字符串的邮件

        Returns:
            Email对象列表
        """
        return self.email_retriever.retrieve_all_emails(
            delete=delete,
            limit=limit,
            since_date=since_date,
            only_unread=only_unread,
            from_addr=from_addr,
            subject_contains=subject_contains,
        )

    def delete_email(self, msg_num: int) -> bool:
        """
        删除指定邮件

        Args:
            msg_num: 邮件索引

        Returns:
            删除是否成功
        """
        try:
            connection = self.connection_manager.get_connection()
            connection.dele(msg_num)
            logger.info(f"邮件已标记为删除: {msg_num}")
            return True
        except Exception as e:
            logger.error(f"删除邮件 {msg_num} 失败: {e}")
            return False

    def reset_deletions(self) -> bool:
        """
        重置删除标记（取消所有删除操作）

        Returns:
            重置是否成功
        """
        try:
            connection = self.connection_manager.get_connection()
            connection.rset()
            logger.info("已重置所有删除标记")
            return True
        except Exception as e:
            logger.error(f"重置删除标记失败: {e}")
            return False

    def get_email_headers(self, msg_num: int, lines: int = 0) -> Optional[str]:
        """
        获取邮件头部信息

        Args:
            msg_num: 邮件索引
            lines: 获取邮件体的行数（0表示只获取头部）

        Returns:
            邮件头部字符串，如果获取失败则返回None
        """
        try:
            connection = self.connection_manager.get_connection()
            _, headers, _ = connection.top(msg_num, lines)
            header_content = b"\r\n".join(headers).decode("utf-8", errors="ignore")
            logger.debug(f"已获取邮件 {msg_num} 的头部信息")
            return header_content
        except Exception as e:
            logger.error(f"获取邮件 {msg_num} 头部失败: {e}")
            return None

    def get_unique_id(self, msg_num: int = None) -> Optional[str]:
        """
        获取邮件的唯一标识符

        Args:
            msg_num: 邮件索引，如果为None则获取所有邮件的UIDL

        Returns:
            唯一标识符字符串，如果获取失败则返回None
        """
        try:
            connection = self.connection_manager.get_connection()
            if msg_num is not None:
                _, uidl, _ = connection.uidl(msg_num)
                return uidl.decode("ascii", errors="ignore")
            else:
                _, uidl_list, _ = connection.uidl()
                return [line.decode("ascii", errors="ignore") for line in uidl_list]
        except Exception as e:
            logger.error(f"获取UIDL失败: {e}")
            return None

    def save_email_as_eml(self, email: Email, directory: str) -> str:
        """
        将Email对象保存为.eml格式文件

        Args:
            email: Email对象
            directory: 保存目录

        Returns:
            保存的文件路径
        """
        try:
            import os
            import re
            from pathlib import Path

            # 确保目录存在
            os.makedirs(directory, exist_ok=True)

            # 确保邮件有Message-ID
            if not email.message_id:
                # 如果没有Message-ID，生成一个
                import uuid

                email.message_id = f"<{uuid.uuid4()}@localhost>"
                logger.info(f"为邮件生成Message-ID: {email.message_id}")

            # 清理邮件ID，移除尖括号和特殊字符
            message_id = email.message_id.strip("<>").replace("@", "_at_")
            message_id = re.sub(r'[\\/*?:"<>|]', "_", message_id)

            # 生成文件名和完整路径
            filename = f"{message_id}.eml"
            file_path = os.path.join(directory, filename)

            # 使用SMTP客户端的MIME创建方法来生成标准的.eml内容
            from client.smtp_client import SMTPClient

            smtp_client = SMTPClient()
            mime_msg = smtp_client._create_mime_message(email)

            # 将MIME消息转换为字符串
            eml_content = mime_msg.as_string()

            # 写入文件，使用UTF-8编码
            with open(file_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(eml_content)

            logger.info(f"邮件已保存为EML文件: {file_path}")
            return file_path

        except PermissionError as e:
            logger.error(f"保存EML文件权限错误: {e}")
            logger.error(f"请检查目录权限: {directory}")

            # 尝试使用临时目录
            try:
                import tempfile

                temp_dir = tempfile.gettempdir()
                temp_inbox_dir = os.path.join(temp_dir, "email_inbox")
                os.makedirs(temp_inbox_dir, exist_ok=True)

                temp_file_path = os.path.join(temp_inbox_dir, filename)

                with open(temp_file_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(eml_content)

                logger.info(f"邮件已保存到临时目录: {temp_inbox_dir}")
                return temp_file_path

            except Exception as temp_e:
                logger.error(f"临时目录保存也失败: {temp_e}")
                return ""
        except Exception as e:
            logger.error(f"保存EML文件失败: {e}")
            return ""

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()

    def __del__(self):
        """析构函数，确保连接被关闭"""
        try:
            self.disconnect()
        except:
            pass


# 为了保持向后兼容性，创建一个别名
POP3Client = POP3ClientRefactored
