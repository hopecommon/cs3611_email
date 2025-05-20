"""
工具函数模块 - 提供各种通用功能
"""

import os
import logging
import uuid
import hashlib
import datetime
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from common.config import LOG_LEVEL, LOG_FILE


# 设置日志
def setup_logging(
    name: str, level: Optional[str] = None, verbose: bool = False
) -> logging.Logger:
    """
    设置并返回一个配置好的日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别，如果为None则使用配置文件中的级别
        verbose: 是否启用详细日志，如果为True则使用DEBUG级别

    Returns:
        配置好的日志记录器
    """
    if level is None:
        level = LOG_LEVEL

    # 如果verbose为True，使用DEBUG级别
    if verbose:
        level = "DEBUG"

    # 确保日志目录存在
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))

    # 如果logger已经有处理器，不再添加
    if logger.handlers:
        return logger

    # 文件处理器 - 使用UTF-8编码
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(getattr(logging, level))

    # 控制台处理器 - 处理编码错误
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level))

    # 自定义格式化器，处理编码错误
    class SafeFormatter(logging.Formatter):
        def format(self, record):
            # 确保所有字符串都能安全地编码
            try:
                return super().format(record)
            except UnicodeEncodeError:
                # 将无法编码的字符替换为问号或其他可显示字符
                result = super().format(record)
                return result.encode("gbk", errors="replace").decode("gbk")

    # 格式化器
    formatter = SafeFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# 创建一个全局日志记录器
logger = setup_logging("email_app")


def generate_message_id(domain: str = "localhost") -> str:
    """
    生成唯一的邮件ID

    Args:
        domain: 域名部分

    Returns:
        格式为<uuid@domain>的邮件ID
    """
    unique_id = str(uuid.uuid4().hex)
    return f"<{unique_id}@{domain}>"


def generate_timestamp() -> str:
    """
    生成RFC 2822格式的时间戳

    Returns:
        格式化的时间戳字符串
    """
    now = datetime.datetime.now()
    return now.strftime("%a, %d %b %Y %H:%M:%S %z")


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    对密码进行哈希处理

    Args:
        password: 原始密码
        salt: 盐值，如果为None则生成新的盐值

    Returns:
        (hashed_password, salt)元组
    """
    if salt is None:
        salt = uuid.uuid4().hex

    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return hashed, salt


def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """
    验证密码是否匹配

    Args:
        password: 待验证的密码
        hashed_password: 存储的哈希密码
        salt: 盐值

    Returns:
        密码是否匹配
    """
    calculated_hash, _ = hash_password(password, salt)
    return calculated_hash == hashed_password


def safe_filename(filename: str) -> str:
    """
    确保文件名安全（移除不安全字符）

    Args:
        filename: 原始文件名

    Returns:
        安全的文件名
    """
    # 移除路径分隔符和其他不安全字符
    unsafe_chars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
    for char in unsafe_chars:
        filename = filename.replace(char, "_")
    return filename


def get_file_extension(filename: str) -> str:
    """
    获取文件扩展名

    Args:
        filename: 文件名

    Returns:
        文件扩展名（包括点）
    """
    _, ext = os.path.splitext(filename)
    return ext.lower()


def is_valid_email(email: str) -> bool:
    """
    简单验证邮箱地址格式

    Args:
        email: 邮箱地址

    Returns:
        是否为有效的邮箱地址
    """
    # 简单验证，实际应用中可以使用email-validator库进行更严格的验证
    return "@" in email and "." in email.split("@")[1]


def safe_print(text, end="\n"):
    """安全地打印文本，处理编码错误"""
    try:
        print(text, end=end)
    except UnicodeEncodeError:
        # 将无法编码的字符替换为可显示字符
        encoded_text = text.encode(sys.stdout.encoding, errors="replace").decode(
            sys.stdout.encoding
        )
        print(encoded_text, end=end)
