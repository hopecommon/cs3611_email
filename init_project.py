"""
项目初始化脚本 - 创建必要的目录和文件
"""

import os
import sys
import sqlite3
import secrets
import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common.utils import setup_logging
from common.config import (
    DATA_DIR,
    EMAIL_STORAGE_DIR,
    DB_PATH,
    SSL_CERT_FILE,
    SSL_KEY_FILE,
)
from server.user_auth import UserAuth
from server.db_handler import DatabaseHandler

# 设置日志
logger = setup_logging("init_project")


def create_directories():
    """创建必要的目录"""
    directories = [
        DATA_DIR,
        EMAIL_STORAGE_DIR,
        os.path.join("logs"),
        os.path.join("certs"),
        os.path.join("data", "emails"),
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"已创建目录: {directory}")


def create_database():
    """创建并初始化数据库"""
    # 创建数据库处理器（会自动创建表）
    db_handler = DatabaseHandler(DB_PATH)
    logger.info(f"已创建数据库: {DB_PATH}")

    # 创建用户认证
    user_auth = UserAuth(DB_PATH)

    # 创建测试用户
    test_users = [
        ("admin", "admin@example.com", "admin123", "Administrator"),
        ("user1", "user1@example.com", "user123", "Test User 1"),
        ("user2", "user2@example.com", "user123", "Test User 2"),
    ]

    for username, email, password, full_name in test_users:
        user = user_auth.create_user(
            username=username, email=email, password=password, full_name=full_name
        )
        if user:
            logger.info(f"已创建用户: {username}")
        else:
            logger.warning(f"创建用户失败: {username}")


def create_ssl_certificates():
    """创建自签名SSL证书"""
    from OpenSSL import crypto

    # 确保目录存在
    cert_dir = os.path.dirname(SSL_CERT_FILE)
    os.makedirs(cert_dir, exist_ok=True)

    # 创建密钥
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)

    # 创建自签名证书
    cert = crypto.X509()
    cert.get_subject().C = "CN"
    cert.get_subject().ST = "State"
    cert.get_subject().L = "City"
    cert.get_subject().O = "Organization"
    cert.get_subject().OU = "Organizational Unit"
    cert.get_subject().CN = "localhost"
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10 * 365 * 24 * 60 * 60)  # 10年有效期
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.sign(key, "sha256")

    # 保存证书和密钥
    with open(SSL_CERT_FILE, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

    with open(SSL_KEY_FILE, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))

    logger.info(f"已创建SSL证书: {SSL_CERT_FILE}")
    logger.info(f"已创建SSL密钥: {SSL_KEY_FILE}")


def create_env_file():
    """创建.env文件"""
    env_content = """# SMTP服务器设置
SMTP_HOST=smtp.qq.com
SMTP_PORT=587
SMTP_USE_SSL=True
SMTP_SSL_PORT=465
SMTP_USERNAME=admin@example.com
SMTP_PASSWORD=password

# POP3服务器设置
POP3_HOST=pop.qq.com
POP3_PORT=110
POP3_USE_SSL=True
POP3_SSL_PORT=995
POP3_USERNAME=admin@example.com
POP3_PASSWORD=password

# 邮件默认设置
EMAIL_FROM_NAME=Administrator
EMAIL_FROM_ADDRESS=admin@example.com
EMAIL_DEFAULT_TO=user@example.com

# 本地存储设置
EMAIL_DB_PATH=data/db/emails.db
EMAIL_STORAGE_PATH=data/emails

# 安全配置
AUTH_REQUIRED=True
SSL_CERT_FILE=certs/server.crt
SSL_KEY_FILE=certs/server.key

# 并发配置
MAX_CONNECTIONS=10
CONNECTION_TIMEOUT=60

# 日志配置
LOG_LEVEL=INFO

# Web界面配置
WEB_HOST=localhost
WEB_PORT=5000
SECRET_KEY={}

# 扩展功能
SPAM_FILTER_ENABLED=True
SPAM_KEYWORDS=viagra,casino,lottery,prize,winner
SPAM_THRESHOLD=0.7

PGP_ENABLED=True
PGP_HOME=pgp

RECALL_ENABLED=True
RECALL_TIMEOUT=3600
""".format(
        secrets.token_hex(16)
    )

    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)

    logger.info("已创建.env文件")


def create_test_emails():
    """创建测试邮件"""
    db_handler = DatabaseHandler(DB_PATH)

    # 测试邮件
    test_emails = [
        {
            "from_addr": "admin@example.com",
            "to_addrs": ["user1@example.com"],
            "subject": "Welcome to Email System",
            "content": """From: admin@example.com
To: user1@example.com
Subject: Welcome to Email System
Date: {}
Message-ID: <test1@localhost>

Hello User1,

Welcome to our email system! This is a test message.

Best regards,
Admin
""".format(
                datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
            ),
        },
        {
            "from_addr": "user2@example.com",
            "to_addrs": ["user1@example.com"],
            "subject": "Hello from User2",
            "content": """From: user2@example.com
To: user1@example.com
Subject: Hello from User2
Date: {}
Message-ID: <test2@localhost>

Hi User1,

This is a test message from User2.

Regards,
User2
""".format(
                datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
            ),
        },
    ]

    for email in test_emails:
        message_id = f"<test{secrets.token_hex(8)}@localhost>"

        # 保存邮件元数据
        db_handler.save_email_metadata(
            message_id=message_id,
            from_addr=email["from_addr"],
            to_addrs=email["to_addrs"],
            subject=email["subject"],
            date=datetime.datetime.now(),
            size=len(email["content"]),
        )

        # 保存邮件内容
        db_handler.save_email_content(message_id=message_id, content=email["content"])

        logger.info(f"已创建测试邮件: {message_id}")


def main():
    """主函数"""
    try:
        print("开始初始化项目...")

        # 创建目录
        create_directories()

        # 创建数据库
        create_database()

        # 创建SSL证书
        try:
            create_ssl_certificates()
        except ImportError:
            logger.warning("未安装OpenSSL，跳过创建SSL证书")

        # 创建.env文件
        create_env_file()

        # 创建测试邮件
        create_test_emails()

        print("项目初始化完成！")
    except Exception as e:
        logger.exception(f"初始化项目时出错: {e}")
        print(f"初始化失败: {e}")


if __name__ == "__main__":
    main()
