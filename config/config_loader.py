"""
配置加载模块 - 用于加载配置文件或环境变量
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent


def load_json_config(config_path: str) -> Dict[str, Any]:
    """
    从JSON文件加载配置

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典

    Raises:
        FileNotFoundError: 配置文件不存在
        json.JSONDecodeError: JSON解析错误
    """
    # 如果是相对路径，则相对于项目根目录
    if not os.path.isabs(config_path):
        config_path = os.path.join(ROOT_DIR, config_path)

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    return config


def load_env_config(env_path: Optional[str] = None) -> Dict[str, Any]:
    """
    从.env文件加载配置

    Args:
        env_path: .env文件路径，如果为None则尝试加载默认的.env文件

    Returns:
        配置字典
    """
    # 如果指定了.env文件路径
    if env_path:
        # 如果是相对路径，则相对于项目根目录
        if not os.path.isabs(env_path):
            env_path = os.path.join(ROOT_DIR, env_path)

        # 加载.env文件
        load_dotenv(env_path)
    else:
        # 尝试加载默认的.env文件
        load_dotenv()

    # 构建配置字典
    config = {
        "smtp": {
            "host": os.getenv("SMTP_HOST", "smtp.qq.com"),
            "port": int(os.getenv("SMTP_PORT", "465")),
            "use_ssl": os.getenv("SMTP_USE_SSL", "False").lower() == "true",
            "ssl_port": int(os.getenv("SMTP_SSL_PORT", "465")),
            "username": os.getenv("SMTP_USERNAME", ""),
            "password": os.getenv("SMTP_PASSWORD", ""),
        },
        "pop3": {
            "host": os.getenv("POP3_HOST", "pop.qq.com"),
            "port": int(os.getenv("POP3_PORT", "110")),
            "use_ssl": os.getenv("POP3_USE_SSL", "False").lower() == "true",
            "ssl_port": int(os.getenv("POP3_SSL_PORT", "995")),
            "username": os.getenv("POP3_USERNAME", ""),
            "password": os.getenv("POP3_PASSWORD", ""),
        },
        "email": {
            "from_name": os.getenv("EMAIL_FROM_NAME", ""),
            "from_address": os.getenv("EMAIL_FROM_ADDRESS", ""),
            "default_to": os.getenv("EMAIL_DEFAULT_TO", ""),
        },
        "storage": {
            "db_path": os.getenv("EMAIL_DB_PATH", "data/db/emails.db"),
            "storage_path": os.getenv("EMAIL_STORAGE_PATH", "data/emails"),
        },
    }

    return config


def get_smtp_config(config_source: str = "env") -> Dict[str, Any]:
    """
    获取SMTP配置

    Args:
        config_source: 配置来源，可以是"env"或JSON配置文件路径

    Returns:
        SMTP配置字典
    """
    if config_source == "env":
        config = load_env_config()
    else:
        config = load_json_config(config_source)

    return config.get("smtp", {})


def get_email_config(config_source: str = "env") -> Dict[str, Any]:
    """
    获取邮件配置

    Args:
        config_source: 配置来源，可以是"env"或JSON配置文件路径

    Returns:
        邮件配置字典
    """
    if config_source == "env":
        config = load_env_config()
    else:
        config = load_json_config(config_source)

    return config.get("email", {})


def get_pop3_config(config_source: str = "env") -> Dict[str, Any]:
    """
    获取POP3配置

    Args:
        config_source: 配置来源，可以是"env"或JSON配置文件路径

    Returns:
        POP3配置字典
    """
    if config_source == "env":
        config = load_env_config()
    else:
        config = load_json_config(config_source)

    return config.get("pop3", {})


def get_storage_config(config_source: str = "env") -> Dict[str, Any]:
    """
    获取存储配置

    Args:
        config_source: 配置来源，可以是"env"或JSON配置文件路径

    Returns:
        存储配置字典
    """
    if config_source == "env":
        config = load_env_config()
    else:
        config = load_json_config(config_source)

    return config.get("storage", {})
