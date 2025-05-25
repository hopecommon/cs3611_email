"""
MIME处理模块 - 处理邮件的MIME编码和解码
"""

import os
import base64
import quopri
import mimetypes
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.parser import Parser, BytesParser
from email import policy
from email.utils import decode_rfc2231, encode_rfc2231
from email.header import decode_header, make_header
from typing import List, Dict, Optional, Tuple, BinaryIO, Any, Union
from pathlib import Path

from common.utils import setup_logging, get_file_extension, safe_filename
from common.models import Email, EmailAddress, Attachment

# 设置日志
logger = setup_logging("mime_handler")


class MIMEHandler:
    """MIME编码和解码处理类"""

    @staticmethod
    def encode_attachment(file_path: str) -> Attachment:
        """
        将文件编码为附件

        Args:
            file_path: 文件路径

        Returns:
            Attachment对象

        Raises:
            FileNotFoundError: 文件不存在
            IOError: 读取文件失败
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 获取文件名和MIME类型
        filename = os.path.basename(file_path)
        content_type, _ = mimetypes.guess_type(file_path)

        if content_type is None:
            # 如果无法确定MIME类型，使用通用二进制类型
            content_type = "application/octet-stream"

        # 读取文件内容
        try:
            with open(file_path, "rb") as f:
                content = f.read()
        except IOError as e:
            logger.error(f"读取文件失败: {e}")
            raise

        # 创建附件对象
        attachment = Attachment(
            filename=filename,
            content_type=content_type,
            content=content,
            size=len(content),
        )

        logger.info(f"已编码附件: {filename} ({content_type}, {len(content)}字节)")
        return attachment

    @staticmethod
    def decode_attachment(attachment: Attachment, output_dir: str) -> str:
        """
        将附件解码并保存到文件

        Args:
            attachment: Attachment对象
            output_dir: 输出目录

        Returns:
            保存的文件路径

        Raises:
            IOError: 写入文件失败
        """
        # 确保目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 生成安全的文件名
        safe_name = safe_filename(attachment.filename)
        file_path = os.path.join(output_dir, safe_name)

        # 如果文件已存在，添加数字后缀
        counter = 1
        while os.path.exists(file_path):
            name, ext = os.path.splitext(safe_name)
            file_path = os.path.join(output_dir, f"{name}_{counter}{ext}")
            counter += 1

        # 写入文件
        try:
            with open(file_path, "wb") as f:
                f.write(attachment.content)
        except IOError as e:
            logger.error(f"写入文件失败: {e}")
            raise

        logger.info(f"已解码附件并保存到: {file_path}")
        return file_path

    @staticmethod
    def parse_eml_file(file_path: str) -> Email:
        """
        解析.eml文件为Email对象

        Args:
            file_path: .eml文件路径

        Returns:
            Email对象

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 解析失败
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        try:
            # 读取并解析.eml文件
            with open(file_path, "rb") as f:
                parser = BytesParser(policy=policy.default)
                msg = parser.parse(f)

            # 使用POP3客户端的转换方法
            from client.pop3_client import POP3Client

            pop3_client = POP3Client()
            email_obj = pop3_client._convert_to_email(msg)

            logger.info(f"已解析.eml文件: {file_path}")
            return email_obj
        except Exception as e:
            logger.error(f"解析.eml文件失败: {e}")
            raise ValueError(f"解析.eml文件失败: {e}")

    @staticmethod
    def save_as_eml(email_obj: Email, file_path: str) -> None:
        """
        将Email对象保存为.eml文件

        Args:
            email_obj: Email对象
            file_path: 保存路径

        Raises:
            IOError: 写入文件失败
        """
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        try:
            # 使用统一的格式处理器创建MIME消息
            from common.email_format_handler import EmailFormatHandler

            mime_msg = EmailFormatHandler.create_mime_message(email_obj)

            # 保存为.eml文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(mime_msg.as_string())

            logger.info(f"已将Email对象保存为.eml文件: {file_path}")
        except Exception as e:
            logger.error(f"保存.eml文件失败: {e}")
            raise IOError(f"保存.eml文件失败: {e}")

    @staticmethod
    def decode_header_value(header_value: str) -> str:
        """
        解码邮件头部值

        Args:
            header_value: 编码的头部值

        Returns:
            解码后的头部值
        """
        try:
            parts = decode_header(header_value)
            decoded_parts = []

            for part, encoding in parts:
                if isinstance(part, bytes):
                    if encoding:
                        try:
                            decoded_parts.append(part.decode(encoding))
                        except:
                            # 如果指定的编码失败，尝试使用utf-8
                            decoded_parts.append(part.decode("utf-8", errors="replace"))
                    else:
                        # 如果没有指定编码，尝试使用utf-8
                        decoded_parts.append(part.decode("utf-8", errors="replace"))
                else:
                    decoded_parts.append(part)

            return "".join(decoded_parts)
        except Exception as e:
            logger.warning(f"解码头部值失败: {e}")
            return header_value

    @staticmethod
    def encode_header_value(value: str, charset: str = "utf-8") -> str:
        """
        编码邮件头部值

        Args:
            value: 原始值
            charset: 字符集

        Returns:
            编码后的头部值
        """
        try:
            header = make_header([(value, charset)])
            return str(header)
        except Exception as e:
            logger.warning(f"编码头部值失败: {e}")
            return value

    @staticmethod
    def get_content_type(file_path: str) -> str:
        """
        获取文件的MIME类型

        Args:
            file_path: 文件路径

        Returns:
            MIME类型
        """
        content_type, _ = mimetypes.guess_type(file_path)

        if content_type is None:
            # 根据扩展名判断
            ext = get_file_extension(file_path)

            # 常见类型映射
            type_map = {
                ".txt": "text/plain",
                ".html": "text/html",
                ".htm": "text/html",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".pdf": "application/pdf",
                ".doc": "application/msword",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".xls": "application/vnd.ms-excel",
                ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ".zip": "application/zip",
                ".mp3": "audio/mpeg",
                ".mp4": "video/mp4",
            }

            content_type = type_map.get(ext, "application/octet-stream")

        return content_type
