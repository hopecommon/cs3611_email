# -*- coding: utf-8 -*-
"""
邮件内容处理模块
负责提取和处理邮件的文本内容、HTML内容和附件
"""

import base64
import quopri
import re
from typing import List, Tuple
from email.message import EmailMessage

from common.utils import setup_logging
from common.models import Attachment

logger = setup_logging(__name__)


class EmailContentProcessor:
    """邮件内容处理器"""

    DEFAULT_CHARSET = "utf-8"

    @classmethod
    def extract_content_and_attachments(
        cls, msg: EmailMessage
    ) -> Tuple[str, str, List[Attachment]]:
        """
        提取邮件内容和附件

        Args:
            msg: EmailMessage对象

        Returns:
            (text_content, html_content, attachments)
        """
        text_content = ""
        html_content = ""
        attachments = []

        try:
            if msg.is_multipart():
                text_content, html_content = cls._process_multipart_message(
                    msg, attachments
                )
            else:
                text_content, html_content = cls._process_single_part_message(
                    msg, attachments
                )
        except Exception as e:
            logger.error(f"提取邮件内容失败: {e}")

        return text_content, html_content, attachments

    @classmethod
    def _process_multipart_message(
        cls, msg: EmailMessage, attachments: List[Attachment]
    ) -> Tuple[str, str]:
        """处理多部分邮件"""
        text_content = ""
        html_content = ""

        for part in msg.walk():
            if part.is_multipart():
                continue

            content_type = part.get_content_type()
            content_disposition = part.get_content_disposition()

            if content_disposition == "attachment":
                cls._extract_attachment(part, attachments)
            elif content_type == "text/plain" and not text_content:
                text_content = cls._extract_text_content(part)
            elif content_type == "text/html" and not html_content:
                html_content = cls._extract_text_content(part)
            elif content_disposition is None and content_type.startswith("text/"):
                # 内联文本内容
                if content_type == "text/plain" and not text_content:
                    text_content = cls._extract_text_content(part)
                elif content_type == "text/html" and not html_content:
                    html_content = cls._extract_text_content(part)
            else:
                # 其他类型作为附件处理
                cls._extract_attachment(part, attachments)

        return text_content, html_content

    @classmethod
    def _process_single_part_message(
        cls, msg: EmailMessage, attachments: List[Attachment]
    ) -> Tuple[str, str]:
        """处理单部分邮件"""
        text_content = ""
        html_content = ""
        content_type = msg.get_content_type()

        if content_type == "text/plain":
            text_content = cls._extract_text_content(msg)
        elif content_type == "text/html":
            html_content = cls._extract_text_content(msg)
        else:
            # 其他类型作为附件处理
            cls._extract_attachment(msg, attachments)

        return text_content, html_content

    @classmethod
    def _extract_text_content(cls, part: EmailMessage) -> str:
        """提取文本内容"""
        try:
            encoding = part.get("Content-Transfer-Encoding", "").lower()
            charset = part.get_content_charset() or cls.DEFAULT_CHARSET
            payload = part.get_payload()

            # 根据编码类型解码内容
            content = cls._decode_payload(payload, encoding, charset)

            # 智能标准化内容
            content = cls._normalize_content(content, part.get_content_type())

            return content
        except Exception as e:
            logger.error(f"提取文本内容失败: {e}")
            return ""

    @classmethod
    def _decode_payload(cls, payload, encoding: str, charset: str) -> str:
        """解码邮件载荷"""
        if encoding == "base64":
            if isinstance(payload, str):
                try:
                    decoded_bytes = base64.b64decode(payload)
                    return decoded_bytes.decode(charset, errors="replace")
                except Exception as e:
                    logger.warning(f"base64解码失败: {e}")
                    return payload
            else:
                return str(payload)
        elif encoding == "quoted-printable":
            if isinstance(payload, str):
                try:
                    decoded_bytes = quopri.decodestring(payload.encode())
                    return decoded_bytes.decode(charset, errors="replace")
                except Exception as e:
                    logger.warning(f"quoted-printable解码失败: {e}")
                    return payload
            else:
                return str(payload)
        else:
            # 8bit或7bit编码
            if isinstance(payload, bytes):
                return payload.decode(charset, errors="replace")
            else:
                return str(payload)

    @classmethod
    def _extract_attachment(
        cls, part: EmailMessage, attachments: List[Attachment]
    ) -> None:
        """提取附件"""
        try:
            # 获取文件名
            filename = cls._get_attachment_filename(part)

            # 获取内容类型
            content_type = part.get_content_type() or "application/octet-stream"

            # 获取内容
            payload = part.get_payload(decode=True)
            if payload is None:
                logger.warning(f"附件 {filename} 内容为空")
                return

            # 创建附件对象
            attachment = Attachment(
                filename=filename,
                content_type=content_type,
                content=payload,
                size=len(payload),
            )

            attachments.append(attachment)
            logger.debug(f"已提取附件: {filename} ({content_type}, {len(payload)}字节)")

        except Exception as e:
            logger.error(f"提取附件失败: {e}")

    @classmethod
    def _get_attachment_filename(cls, part: EmailMessage) -> str:
        """获取附件文件名"""
        filename = part.get_filename()
        if not filename:
            # 尝试从Content-Disposition中获取
            content_disposition = part.get("Content-Disposition", "")
            if "filename=" in content_disposition:
                filename = content_disposition.split("filename=")[1].strip('"')
            else:
                filename = "attachment"

        # 解码文件名（如果需要）
        # 避免循环导入，直接使用简单的解码逻辑
        try:
            from email.header import decode_header

            parts = decode_header(filename)
            decoded_parts = []
            for part, encoding in parts:
                if isinstance(part, bytes):
                    if encoding:
                        try:
                            decoded_parts.append(part.decode(encoding))
                        except:
                            decoded_parts.append(part.decode("utf-8", errors="replace"))
                    else:
                        decoded_parts.append(part.decode("utf-8", errors="replace"))
                else:
                    decoded_parts.append(str(part))
            return "".join(decoded_parts)
        except:
            return filename


class EmailContentNormalizer:
    """邮件内容标准化器"""

    @classmethod
    def normalize_content(cls, content: str, content_type: str = "text/plain") -> str:
        """
        智能标准化邮件内容

        Args:
            content: 原始内容
            content_type: 内容类型

        Returns:
            标准化后的内容
        """
        if not content:
            return ""

        # 基本清理
        content = content.strip()

        if content_type == "text/html":
            return cls._normalize_html_content(content)
        else:
            return cls._normalize_text_content(content)

    @classmethod
    def _normalize_html_content(cls, content: str) -> str:
        """标准化HTML内容"""
        # 移除HTML内容中的多余换行符，但保留HTML结构
        content = re.sub(r">\s+<", "><", content)

        # 标准化换行符
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        # 移除开头和结尾的空白
        content = content.strip()

        return content

    @classmethod
    def _normalize_text_content(cls, content: str) -> str:
        """标准化纯文本内容"""
        # 标准化换行符
        content = content.replace("\r\n", "\n").replace("\r", "\n")

        # 移除多余的空行（保留单个空行）
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)

        # 移除开头和结尾的空白
        content = content.strip()

        return content


# 为了向后兼容，在EmailContentProcessor中添加normalize方法
EmailContentProcessor._normalize_content = EmailContentNormalizer.normalize_content
