# -*- coding: utf-8 -*-
"""
重构后的统一邮件格式处理模块
通过模块化设计提供邮件格式处理功能
"""

from typing import Union
from email.message import EmailMessage

from common.utils import setup_logging
from common.models import Email

# 导入各个专门的处理模块
from common.email_parsing_strategies import EmailParsingStrategies, EmailPreprocessor
from common.email_content_processor import EmailContentProcessor
from common.email_header_processor import EmailHeaderProcessor
from common.email_mime_builder import EmailMimeBuilder, EmailFormatter
from common.email_fallback_parser import EmailFallbackParser, EmailFormatValidator

logger = setup_logging(__name__)


class EmailFormatHandler:
    """
    重构后的统一邮件格式处理器

    这是整个邮件系统的格式处理中心，通过模块化设计提供：
    1. 统一邮件格式标准
    2. 处理客户端和服务端的格式兼容性
    3. 提供标准化的邮件创建、解析和存储方法
    """

    # 标准的邮件头部字段
    STANDARD_HEADERS = [
        "Message-ID",
        "Subject",
        "From",
        "To",
        "Cc",
        "Bcc",
        "Date",
        "MIME-Version",
        "Content-Type",
        "Content-Transfer-Encoding",
    ]

    # 默认字符集
    DEFAULT_CHARSET = "utf-8"

    # 邮件格式版本（用于兼容性检查）
    FORMAT_VERSION = "1.0"

    @classmethod
    def create_mime_message(cls, email_obj: Email) -> EmailMessage:
        """
        从Email对象创建标准的MIME消息

        Args:
            email_obj: Email对象

        Returns:
            标准格式的EmailMessage对象
        """
        return EmailMimeBuilder.create_mime_message(email_obj)

    @classmethod
    def parse_mime_message(cls, raw_content: Union[str, bytes]) -> Email:
        """
        解析MIME消息为Email对象，增强对不同邮件服务器格式的兼容性

        Args:
            raw_content: 原始邮件内容

        Returns:
            Email对象
        """
        try:
            # 预处理原始内容以提高兼容性
            processed_content = EmailPreprocessor.preprocess_content(raw_content)

            # 使用增强的解析策略
            msg = EmailParsingStrategies.parse_with_strategies(processed_content)

            # 解析基本信息
            message_id = EmailHeaderProcessor.extract_message_id(msg)

            # 增强的主题解析
            subject = EmailHeaderProcessor.decode_header_value(msg.get("Subject", ""))
            if not subject:
                # 尝试从其他可能的头部获取主题
                subject = msg.get("Subject", "") or ""

            # 增强的发件人解析
            from_addr = EmailHeaderProcessor.parse_address(msg.get("From", ""))
            if not from_addr:
                # 尝试从其他头部获取发件人信息
                sender = msg.get("Sender", "") or msg.get("Reply-To", "")
                if sender:
                    from_addr = EmailHeaderProcessor.parse_address(sender)

                if not from_addr:
                    from common.models import EmailAddress

                    from_addr = EmailAddress("", "unknown@localhost")

            to_addrs = EmailHeaderProcessor.parse_address_list(msg.get("To", ""))
            cc_addrs = EmailHeaderProcessor.parse_address_list(msg.get("Cc", ""))
            bcc_addrs = EmailHeaderProcessor.parse_address_list(msg.get("Bcc", ""))
            date = EmailHeaderProcessor.parse_date(msg.get("Date", ""))

            # 解析内容
            text_content, html_content, attachments = (
                EmailContentProcessor.extract_content_and_attachments(msg)
            )

            # 创建Email对象
            email_obj = Email(
                message_id=message_id,
                subject=subject,
                from_addr=from_addr,
                to_addrs=to_addrs,
                cc_addrs=cc_addrs,
                bcc_addrs=bcc_addrs,
                date=date,
                text_content=text_content,
                html_content=html_content,
                attachments=attachments,
            )

            logger.debug(f"已解析邮件: {message_id}")
            return email_obj

        except Exception as e:
            logger.error(f"解析MIME消息失败: {e}")
            # 尝试使用备用解析方法
            try:
                return EmailFallbackParser.fallback_parse(raw_content)
            except Exception as fallback_e:
                logger.error(f"备用解析也失败: {fallback_e}")
                raise e

    @classmethod
    def format_email_for_storage(cls, email_obj: Email) -> str:
        """
        将Email对象格式化为标准的.eml格式用于存储

        Args:
            email_obj: Email对象

        Returns:
            标准格式的邮件内容字符串
        """
        return EmailFormatter.format_for_storage(email_obj)

    @classmethod
    def normalize_email_headers(cls, raw_content: str) -> str:
        """
        标准化邮件头部格式

        Args:
            raw_content: 原始邮件内容

        Returns:
            标准化后的邮件内容
        """
        return EmailFormatter.normalize_headers(raw_content)

    @classmethod
    def validate_email_format(cls, raw_content: str) -> bool:
        """
        验证邮件格式是否正确

        Args:
            raw_content: 邮件内容

        Returns:
            是否格式正确
        """
        return EmailFormatValidator.validate_format(raw_content)

    @classmethod
    def ensure_proper_format(cls, raw_content: str, metadata=None) -> str:
        """
        确保邮件格式正确，如果格式有问题则自动修复

        Args:
            raw_content: 原始邮件内容
            metadata: 邮件元数据（用于修复缺失的头部）

        Returns:
            格式正确的邮件内容
        """
        try:
            # 1. 首先尝试验证现有格式
            if cls.validate_email_format(raw_content):
                return cls.normalize_email_headers(raw_content)

            # 2. 如果格式有问题，尝试修复
            logger.debug("邮件格式需要修复，开始自动修复")

            # 3. 检查是否有基本的头部信息
            if EmailFormatValidator.has_basic_headers(raw_content):
                # 有头部但格式不正确，标准化处理
                return cls.normalize_email_headers(raw_content)
            else:
                # 缺少头部，返回原内容（避免破坏数据）
                logger.warning("邮件缺少头部且无法修复")
                return raw_content

        except Exception as e:
            logger.error(f"邮件格式修复失败: {e}")
            return raw_content

    @classmethod
    def parse_email_content(cls, content: Union[str, bytes]) -> Email:
        """
        便捷的邮件内容解析方法，自动处理各种格式

        Args:
            content: 邮件内容（字符串或字节）

        Returns:
            Email对象
        """
        return cls.parse_mime_message(content)

    # 为了向后兼容，保留一些常用的内部方法
    @classmethod
    def _decode_header_value(cls, header_value: str) -> str:
        """向后兼容方法"""
        return EmailHeaderProcessor.decode_header_value(header_value)

    @classmethod
    def _parse_address(cls, addr_str: str):
        """向后兼容方法"""
        return EmailHeaderProcessor.parse_address(addr_str)

    @classmethod
    def _parse_address_list(cls, addr_str: str):
        """向后兼容方法"""
        return EmailHeaderProcessor.parse_address_list(addr_str)

    @classmethod
    def _parse_date(cls, date_str: str):
        """向后兼容方法"""
        return EmailHeaderProcessor.parse_date(date_str)

    @classmethod
    def _extract_message_id(cls, msg):
        """向后兼容方法"""
        return EmailHeaderProcessor.extract_message_id(msg)

    @classmethod
    def _extract_content_and_attachments(cls, msg):
        """向后兼容方法"""
        return EmailContentProcessor.extract_content_and_attachments(msg)

    @classmethod
    def _fallback_parse(cls, raw_content):
        """向后兼容方法"""
        return EmailFallbackParser.fallback_parse(raw_content)

    @classmethod
    def _preprocess_raw_content(cls, raw_content):
        """向后兼容方法"""
        return EmailPreprocessor.preprocess_content(raw_content)
