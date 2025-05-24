# -*- coding: utf-8 -*-
"""
邮件备用解析模块
当标准解析失败时提供备用解析方案
"""

import datetime
from typing import Union, Dict, Any

from common.utils import setup_logging
from common.models import Email, EmailAddress
from common.email_header_processor import EmailHeaderProcessor

logger = setup_logging(__name__)


class EmailFallbackParser:
    """邮件备用解析器"""

    @classmethod
    def fallback_parse(cls, raw_content: Union[str, bytes]) -> Email:
        """
        备用解析方法，用于处理格式异常的邮件

        Args:
            raw_content: 原始邮件内容

        Returns:
            Email对象
        """
        try:
            # 转换为字符串
            if isinstance(raw_content, bytes):
                content = cls._decode_with_fallback(raw_content)
            else:
                content = raw_content

            # 简单的头部解析
            headers, body_content = cls._parse_headers_and_body(content)

            # 提取基本信息
            email_info = cls._extract_basic_info(headers)

            # 创建Email对象
            email_obj = Email(
                message_id=email_info["message_id"],
                subject=email_info["subject"],
                from_addr=email_info["from_addr"],
                to_addrs=email_info["to_addrs"],
                cc_addrs=[],
                bcc_addrs=[],
                date=email_info["date"],
                text_content=body_content,
                html_content="",
                attachments=[],
            )

            logger.info(f"使用备用方法成功解析邮件: {email_info['message_id']}")
            return email_obj

        except Exception as e:
            logger.error(f"备用解析方法失败: {e}")
            # 创建一个最基本的Email对象
            return cls._create_minimal_email(raw_content)

    @classmethod
    def _parse_headers_and_body(cls, content: str) -> tuple:
        """解析头部和正文"""
        lines = content.split("\n")
        headers = {}
        body_start = 0

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                body_start = i + 1
                break
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        # 提取正文
        body_content = "\n".join(lines[body_start:])

        return headers, body_content

    @classmethod
    def _extract_basic_info(cls, headers: Dict[str, str]) -> Dict[str, Any]:
        """从头部提取基本信息"""
        processor = EmailHeaderProcessor

        # 提取基本信息
        message_id = headers.get(
            "Message-ID",
            f"<fallback-{datetime.datetime.now().timestamp()}@localhost>",
        )

        subject = headers.get("Subject", "")
        if not subject:
            subject = "(无主题)"

        from_addr_str = headers.get("From", "unknown@localhost")
        to_addr_str = headers.get("To", "")
        date_str = headers.get("Date", "")

        # 解析地址
        from_addr = processor.parse_address(from_addr_str) or EmailAddress(
            "", "unknown@localhost"
        )
        to_addrs = processor.parse_address_list(to_addr_str)

        # 解析日期
        date = processor.parse_date(date_str)

        return {
            "message_id": message_id.strip("<>"),
            "subject": subject,
            "from_addr": from_addr,
            "to_addrs": to_addrs,
            "date": date,
        }

    @classmethod
    def _create_minimal_email(cls, raw_content: Union[str, bytes]) -> Email:
        """创建最基本的Email对象"""
        return Email(
            message_id=f"<error-{datetime.datetime.now().timestamp()}@localhost>",
            subject="(解析失败)",
            from_addr=EmailAddress("", "unknown@localhost"),
            to_addrs=[],
            cc_addrs=[],
            bcc_addrs=[],
            date=datetime.datetime.now(),
            text_content=(
                str(raw_content)[:1000] + "..."
                if len(str(raw_content)) > 1000
                else str(raw_content)
            ),
            html_content="",
            attachments=[],
        )

    @classmethod
    def _decode_with_fallback(cls, content_bytes: bytes) -> str:
        """
        使用多种编码尝试解码字节内容

        Args:
            content_bytes: 字节内容

        Returns:
            解码后的字符串
        """
        encodings = ["utf-8", "gbk", "gb2312", "big5", "iso-8859-1", "windows-1252"]

        for encoding in encodings:
            try:
                return content_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue

        # 如果所有编码都失败，使用utf-8并忽略错误
        return content_bytes.decode("utf-8", errors="replace")


class EmailFormatValidator:
    """邮件格式验证器"""

    @classmethod
    def validate_format(cls, raw_content: str) -> bool:
        """
        验证邮件格式是否正确

        Args:
            raw_content: 邮件内容

        Returns:
            是否格式正确
        """
        try:
            from email.parser import Parser
            from email import policy

            # 尝试解析邮件
            parser = Parser(policy=policy.default)
            msg = parser.parsestr(raw_content)

            # 根据RFC 5322，只有From和Date是必需的头部字段
            required_headers = ["From", "Date"]
            for header in required_headers:
                if not msg.get(header):
                    logger.warning(f"缺少必需的头部字段: {header}")
                    return False

            # Message-ID是可选的，但建议包含
            if not msg.get("Message-ID"):
                logger.info("邮件缺少Message-ID头部（可选字段），建议添加以提高兼容性")

            return True

        except Exception as e:
            logger.error(f"验证邮件格式失败: {e}")
            return False

    @classmethod
    def has_basic_headers(cls, content: str) -> bool:
        """检查是否有基本的头部信息"""
        lines = content.split("\n")[:20]  # 只检查前20行

        header_count = 0
        for line in lines:
            if ":" in line and not line.startswith(" ") and not line.startswith("\t"):
                header_count += 1

        return header_count >= 3  # 至少有3个头部字段
