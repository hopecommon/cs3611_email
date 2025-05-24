# -*- coding: utf-8 -*-
"""
邮件头部处理模块
负责邮件头部的解析、编码、解码和格式化
"""

import datetime
from typing import List, Optional
from email.header import decode_header, Header
from email.utils import formataddr, parseaddr, parsedate_to_datetime, formatdate

from common.utils import setup_logging
from common.models import EmailAddress

logger = setup_logging(__name__)


class EmailHeaderProcessor:
    """邮件头部处理器"""

    DEFAULT_CHARSET = "utf-8"

    @classmethod
    def extract_message_id(cls, msg) -> str:
        """提取Message-ID"""
        message_id = msg.get("Message-ID", "")
        if message_id:
            # 去除尖括号
            message_id = message_id.strip("<>")
        return message_id

    @classmethod
    def decode_header_value(cls, header_value: str) -> str:
        """
        RFC 2047标准合规的邮件头部值解码

        Args:
            header_value: 头部值

        Returns:
            解码后的字符串
        """
        if not header_value:
            return ""

        try:
            # 使用Python标准库的decode_header，它完全符合RFC 2047标准
            parts = decode_header(header_value)
            decoded_parts = []

            for part, encoding in parts:
                if isinstance(part, bytes):
                    if encoding:
                        try:
                            # 使用指定的编码解码
                            decoded_parts.append(part.decode(encoding))
                        except (UnicodeDecodeError, LookupError) as e:
                            logger.warning(f"使用编码 {encoding} 解码失败: {e}")
                            # 按照RFC标准，如果指定编码失败，尝试UTF-8
                            try:
                                decoded_parts.append(part.decode("utf-8"))
                            except UnicodeDecodeError:
                                # 最后的回退：使用替换错误处理
                                decoded_parts.append(
                                    part.decode("utf-8", errors="replace")
                                )
                    else:
                        # 没有指定编码，按照RFC标准默认为ASCII，但我们宽松处理为UTF-8
                        try:
                            decoded_parts.append(part.decode("ascii"))
                        except UnicodeDecodeError:
                            decoded_parts.append(part.decode("utf-8", errors="replace"))
                else:
                    # 已经是字符串，直接添加
                    decoded_parts.append(str(part))

            # 按照RFC 2047标准，正确处理编码词之间的空白
            # 根据RFC 2047: 相邻编码词之间的线性空白应该被忽略
            result = ""
            for i, (part, encoding) in enumerate(parts):
                if isinstance(part, bytes):
                    if encoding:
                        try:
                            decoded_part = part.decode(encoding)
                        except (UnicodeDecodeError, LookupError):
                            decoded_part = part.decode("utf-8", errors="replace")
                    else:
                        decoded_part = part.decode("ascii", errors="replace")
                else:
                    decoded_part = str(part)

                # 添加到结果中
                if i > 0:
                    # 检查是否需要在部分之间添加空格
                    prev_part, prev_encoding = parts[i - 1]

                    # 如果前一个部分和当前部分都是编码词，则不添加空格
                    # 如果其中一个不是编码词，则保留原始的空格
                    if prev_encoding is None or encoding is None:
                        # 至少有一个不是编码词，检查原始字符串中是否有空格
                        # 这里简化处理，直接连接
                        pass

                result += decoded_part

            # 标准化空白字符
            import re

            result = re.sub(r"\s+", " ", result).strip()

            return result

        except Exception as e:
            logger.error(f"RFC 2047解码失败: {e}, 原始值: {header_value}")
            # 如果标准解码完全失败，返回原始值
            return header_value

    @classmethod
    def _preprocess_header_value(cls, header_value: str) -> str:
        """
        预处理头部值，修复常见格式问题

        Args:
            header_value: 原始头部值

        Returns:
            预处理后的头部值
        """
        if not header_value:
            return header_value

        # 移除多余的空白
        header_value = header_value.strip()

        # 修复编码段之间的空白问题
        import re

        # 合并相邻的编码段
        header_value = re.sub(r"\?=\s+=\?", "?==?", header_value)

        return header_value

    @classmethod
    def parse_address(cls, addr_str: str) -> Optional[EmailAddress]:
        """
        改进的邮件地址解析

        Args:
            addr_str: 地址字符串

        Returns:
            EmailAddress对象或None
        """
        if not addr_str or not addr_str.strip():
            return None

        try:
            # 预处理地址字符串
            addr_str = addr_str.strip()

            # 解码可能的编码头部
            addr_str = cls.decode_header_value(addr_str)

            name, address = parseaddr(addr_str)

            # 进一步解码名称部分
            if name:
                name = cls.decode_header_value(name)

            # 验证地址格式
            if address and "@" in address:
                return EmailAddress(name=name or "", address=address)
            elif addr_str and "@" in addr_str:
                # 如果parseaddr失败，尝试直接使用原始字符串
                return EmailAddress(name="", address=addr_str)
            else:
                return None

        except Exception as e:
            logger.warning(f"解析邮件地址失败: {e}, 原始值: {addr_str}")
            # 尝试创建一个基本的地址对象
            if addr_str and "@" in addr_str:
                return EmailAddress(name="", address=addr_str)
            return None

    @classmethod
    def parse_address_list(cls, addr_str: str) -> List[EmailAddress]:
        """
        解析邮件地址列表

        Args:
            addr_str: 地址列表字符串

        Returns:
            EmailAddress对象列表
        """
        if not addr_str:
            return []

        try:
            addresses = []
            # 分割多个地址
            addr_parts = addr_str.split(",")
            for part in addr_parts:
                part = part.strip()
                if part:
                    addr = cls.parse_address(part)
                    if addr:
                        addresses.append(addr)
            return addresses
        except Exception as e:
            logger.warning(f"解析邮件地址列表失败: {e}")
            return []

    @classmethod
    def parse_date(cls, date_str: str) -> Optional[datetime.datetime]:
        """
        解析邮件日期

        Args:
            date_str: 日期字符串

        Returns:
            datetime对象或None
        """
        if not date_str:
            return None

        try:
            return parsedate_to_datetime(date_str)
        except Exception as e:
            logger.warning(f"解析邮件日期失败: {e}")
            return None

    @classmethod
    def format_message_id(cls, message_id: str) -> str:
        """
        格式化Message-ID

        Args:
            message_id: 原始Message-ID

        Returns:
            格式化后的Message-ID
        """
        if not message_id:
            return message_id

        message_id = message_id.strip()
        if not message_id.startswith("<"):
            message_id = f"<{message_id}>"
        if not message_id.endswith(">"):
            message_id = f"{message_id}>"
        return message_id

    @classmethod
    def format_address_list(cls, addresses: List[EmailAddress]) -> str:
        """
        格式化地址列表

        Args:
            addresses: EmailAddress对象列表

        Returns:
            格式化的地址字符串
        """
        if not addresses:
            return ""

        formatted_addrs = []
        for addr in addresses:
            name = addr.name or ""
            address = addr.address or ""
            formatted_addrs.append(formataddr((name, address)))

        return ", ".join(formatted_addrs)

    @classmethod
    def create_header(cls, value: str, charset: str = None) -> Header:
        """
        创建邮件头部

        Args:
            value: 头部值
            charset: 字符集

        Returns:
            Header对象
        """
        charset = charset or cls.DEFAULT_CHARSET
        return Header(value, charset)

    @classmethod
    def format_date(cls, date: datetime.datetime = None) -> str:
        """
        格式化邮件日期

        Args:
            date: 日期对象，None表示当前时间

        Returns:
            格式化的日期字符串
        """
        if date:
            return formatdate(date.timestamp(), localtime=True)
        else:
            return formatdate(localtime=True)


class EmailHeaderBuilder:
    """邮件头部构建器"""

    @classmethod
    def set_basic_headers(cls, msg, email_obj) -> None:
        """
        设置基本邮件头部

        Args:
            msg: MIME消息对象
            email_obj: Email对象
        """
        processor = EmailHeaderProcessor

        # Message-ID
        if email_obj.message_id:
            msg["Message-ID"] = processor.format_message_id(email_obj.message_id)

        # Subject
        if email_obj.subject:
            msg["Subject"] = processor.create_header(email_obj.subject)

        # From
        if email_obj.from_addr:
            msg["From"] = processor.format_address_list([email_obj.from_addr])

        # To
        if email_obj.to_addrs:
            msg["To"] = processor.format_address_list(email_obj.to_addrs)

        # Cc
        if email_obj.cc_addrs:
            msg["Cc"] = processor.format_address_list(email_obj.cc_addrs)

        # Date
        msg["Date"] = processor.format_date(email_obj.date)
