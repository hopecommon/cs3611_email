# -*- coding: utf-8 -*-
"""
MIME消息构建模块
负责从Email对象创建标准的MIME消息
"""

from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio

from common.utils import setup_logging
from common.models import Email
from common.email_header_processor import EmailHeaderBuilder

logger = setup_logging(__name__)


class EmailMimeBuilder:
    """MIME消息构建器"""

    DEFAULT_CHARSET = "utf-8"

    @classmethod
    def create_mime_message(cls, email_obj: Email) -> EmailMessage:
        """
        从Email对象创建标准的MIME消息

        Args:
            email_obj: Email对象

        Returns:
            标准格式的EmailMessage对象
        """
        try:
            # 创建多部分消息
            msg = MIMEMultipart("mixed")

            # 设置基本头部
            EmailHeaderBuilder.set_basic_headers(msg, email_obj)

            # 添加正文内容
            cls._add_body_content(msg, email_obj)

            # 添加附件
            cls._add_attachments(msg, email_obj)

            logger.debug(f"已创建MIME消息: {email_obj.message_id}")
            return msg

        except Exception as e:
            logger.error(f"创建MIME消息失败: {e}")
            raise

    @classmethod
    def _add_body_content(cls, msg: EmailMessage, email_obj: Email) -> None:
        """添加邮件正文内容"""
        # 如果有HTML内容，创建alternative结构
        if email_obj.html_content and email_obj.text_content:
            # 创建alternative容器
            body_container = MIMEMultipart("alternative")

            # 添加纯文本版本
            text_part = MIMEText(email_obj.text_content, "plain", cls.DEFAULT_CHARSET)
            body_container.attach(text_part)

            # 添加HTML版本
            html_part = MIMEText(email_obj.html_content, "html", cls.DEFAULT_CHARSET)
            body_container.attach(html_part)

            msg.attach(body_container)

        elif email_obj.html_content:
            # 只有HTML内容
            html_part = MIMEText(email_obj.html_content, "html", cls.DEFAULT_CHARSET)
            msg.attach(html_part)

        elif email_obj.text_content:
            # 只有纯文本内容
            text_part = MIMEText(email_obj.text_content, "plain", cls.DEFAULT_CHARSET)
            msg.attach(text_part)

    @classmethod
    def _add_attachments(cls, msg: EmailMessage, email_obj: Email) -> None:
        """添加附件"""
        if not email_obj.attachments:
            return

        for attachment in email_obj.attachments:
            try:
                # 创建MIME部分
                part = cls._create_attachment_part(attachment)

                # 设置附件头部
                filename = attachment.filename or "attachment"
                part.add_header("Content-Disposition", "attachment", filename=filename)

                msg.attach(part)
                logger.debug(f"已添加附件: {filename}")

            except Exception as e:
                logger.error(f"添加附件失败: {e}")
                continue

    @classmethod
    def _create_attachment_part(cls, attachment):
        """创建附件MIME部分"""
        # 获取内容类型
        content_type = attachment.content_type or "application/octet-stream"
        main_type, sub_type = content_type.split("/", 1)

        # 根据内容类型创建适当的MIME部分
        if main_type == "text":
            try:
                # 尝试以UTF-8解码
                text_content = attachment.content.decode(cls.DEFAULT_CHARSET)
                return MIMEText(text_content, sub_type, cls.DEFAULT_CHARSET)
            except UnicodeDecodeError:
                # 如果解码失败，作为二进制附件处理
                return MIMEApplication(attachment.content, _subtype=sub_type)
        elif main_type == "image":
            return MIMEImage(attachment.content, _subtype=sub_type)
        elif main_type == "audio":
            return MIMEAudio(attachment.content, _subtype=sub_type)
        else:
            # 默认使用application类型
            return MIMEApplication(attachment.content, _subtype=sub_type)

    @classmethod
    def normalize_headers(cls, raw_content: str) -> str:
        """
        标准化邮件头部格式（向后兼容方法）

        Args:
            raw_content: 原始邮件内容

        Returns:
            标准化后的邮件内容
        """
        return cls._fix_header_format(raw_content)


class EmailFormatter:
    """邮件格式化器"""

    @classmethod
    def format_for_storage(cls, email_obj: Email) -> str:
        """
        将Email对象格式化为标准的.eml格式用于存储

        Args:
            email_obj: Email对象

        Returns:
            标准格式的邮件内容字符串
        """
        try:
            # 创建MIME消息
            mime_msg = EmailMimeBuilder.create_mime_message(email_obj)

            # 转换为字符串格式
            email_content = mime_msg.as_string()

            # 修复头部格式：确保头部字段之间没有多余空行
            email_content = cls._fix_header_format(email_content)

            logger.debug(f"已格式化邮件用于存储: {email_obj.message_id}")
            return email_content

        except Exception as e:
            logger.error(f"格式化邮件失败: {e}")
            raise

    @classmethod
    def _fix_header_format(cls, raw_content: str) -> str:
        """
        修复邮件头部格式，确保符合RFC标准

        Args:
            raw_content: 原始邮件内容

        Returns:
            修复后的邮件内容
        """
        try:
            lines = raw_content.split("\n")
            fixed_lines = []
            header_section = True
            i = 0

            while i < len(lines):
                line = lines[i].rstrip("\r")

                if header_section:
                    if line == "":
                        # 遇到空行，检查是否真的是头部结束
                        # 向前查看，如果下一个非空行不是头部字段，则这是头部结束
                        next_non_empty = None
                        for j in range(i + 1, len(lines)):
                            next_line = lines[j].strip()
                            if next_line:
                                next_non_empty = next_line
                                break

                        if (
                            next_non_empty
                            and ":" in next_non_empty
                            and not next_non_empty.startswith(" ")
                            and not next_non_empty.startswith("\t")
                        ):
                            # 下一个非空行是头部字段，跳过这个空行
                            pass
                        else:
                            # 这是真正的头部结束
                            fixed_lines.append(line)
                            header_section = False
                    elif (
                        ":" in line
                        and not line.startswith(" ")
                        and not line.startswith("\t")
                    ):
                        # 这是一个头部字段
                        key, value = line.split(":", 1)
                        fixed_line = f"{key.strip()}: {value.strip()}"
                        fixed_lines.append(fixed_line)
                    else:
                        # 头部字段的续行
                        fixed_lines.append(line)
                else:
                    # 正文部分，保持原样
                    fixed_lines.append(line)

                i += 1

            return "\n".join(fixed_lines)

        except Exception as e:
            logger.error(f"修复邮件头部格式失败: {e}")
            return raw_content
