"""
POP3测试数据模块 - 为POP3服务器创建测试用户和测试邮件
"""

import logging
import datetime
import traceback
from typing import List, Dict, Any

from common.utils import setup_logging
from server.db_handler import DatabaseHandler
from server.user_auth import UserAuth

# 设置日志
logger = setup_logging("pop3_test_data")


class POP3TestDataGenerator:
    """POP3测试数据生成器，用于创建测试用户和测试邮件"""

    def __init__(self, db_handler: DatabaseHandler, user_auth: UserAuth):
        """
        初始化测试数据生成器

        Args:
            db_handler: 数据库处理器
            user_auth: 用户认证对象
        """
        self.db_handler = db_handler
        self.user_auth = user_auth
        logger.info("POP3测试数据生成器已初始化")

    def ensure_test_users_exist(self) -> None:
        """确保测试用户存在"""
        try:
            # 测试用户信息
            test_users = [
                {
                    "username": "testuser",
                    "password": "testpass",
                    "email": "testuser@example.com",
                },
                {
                    "username": "user1",
                    "password": "user123",
                    "email": "user1@example.com",
                },
                {
                    "username": "user2",
                    "password": "user123",
                    "email": "user2@example.com",
                },
                {
                    "username": "admin",
                    "password": "admin123",
                    "email": "admin@example.com",
                },
            ]

            for user_info in test_users:
                # 检查用户是否存在
                user = self.user_auth.get_user_by_username(user_info["username"])
                if not user:
                    # 如果用户不存在，则创建
                    self.user_auth.add_user(
                        user_info["username"], user_info["password"], user_info["email"]
                    )
                    logger.info(
                        f"已创建测试用户: {user_info['username']} ({user_info['email']})"
                    )
                else:
                    logger.debug(
                        f"测试用户已存在: {user_info['username']} ({user.email})"
                    )

            # 创建测试邮件
            self.create_test_emails()

        except Exception as e:
            logger.error(f"创建测试用户时出错: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")

    def create_test_emails(self) -> None:
        """创建测试邮件"""
        try:
            # 检查是否已经有测试邮件
            test_emails_exist = False
            try:
                # 查询特定的测试邮件ID
                test_email = self.db_handler.get_email_metadata("<test1@example.com>")
                if test_email:
                    test_emails_exist = True
                    logger.info("测试邮件已存在，跳过创建")
                    return
            except Exception as e:
                logger.debug(f"检查测试邮件时出错: {e}")

            # 即使数据库中有其他邮件，也创建测试邮件
            logger.info("创建新的测试邮件")

            # 创建测试邮件
            test_emails = [
                {
                    "message_id": "<test1@example.com>",
                    "from_addr": "admin@example.com",
                    "to_addrs": ["user1@example.com"],
                    "subject": "测试邮件1 - 欢迎使用POP3服务器",
                    "content_body": "这是一封测试邮件，用于测试POP3服务器的功能。\r\n\r\n祝您使用愉快！\r\n管理员",
                },
                {
                    "message_id": "<test2@example.com>",
                    "from_addr": "admin@example.com",
                    "to_addrs": ["user2@example.com"],
                    "subject": "测试邮件2 - POP3服务器使用指南",
                    "content_body": "这是POP3服务器的使用指南。\r\n\r\n1. 使用POP3客户端连接到服务器\r\n2. 输入用户名和密码\r\n3. 接收邮件\r\n\r\n如有问题，请联系管理员。",
                },
                {
                    "message_id": "<test3@example.com>",
                    "from_addr": "user2@example.com",
                    "to_addrs": ["user1@example.com"],
                    "subject": "测试邮件3 - 来自用户2的问候",
                    "content_body": "你好，用户1！\r\n\r\n这是一封来自用户2的测试邮件。\r\n\r\n祝好！\r\n用户2",
                },
                {
                    "message_id": "<test4@example.com>",
                    "from_addr": "user1@example.com",
                    "to_addrs": ["user2@example.com"],
                    "subject": "测试邮件4 - 回复：来自用户2的问候",
                    "content_body": "你好，用户2！\r\n\r\n收到你的邮件了，谢谢问候！\r\n\r\n祝好！\r\n用户1",
                },
                {
                    "message_id": "<test5@example.com>",
                    "from_addr": "testuser@example.com",
                    "to_addrs": ["user1@example.com", "user2@example.com"],
                    "subject": "测试邮件5 - 群发邮件",
                    "content_body": "大家好！\r\n\r\n这是一封群发的测试邮件。\r\n\r\n祝好！\r\nTest User",
                },
            ]

            # 保存测试邮件
            for email in test_emails:
                # 生成当前日期时间
                now = datetime.datetime.now()
                date_str = now.strftime("%a, %d %b %Y %H:%M:%S %z")

                # 构建完整的邮件内容，包含头部
                to_str = ", ".join(email["to_addrs"])

                # 构建符合RFC标准的邮件内容
                full_content = f"""From: {email["from_addr"]}
To: {to_str}
Subject: {email["subject"]}
Message-ID: {email["message_id"]}
Date: {date_str}
MIME-Version: 1.0
Content-Type: text/plain; charset="utf-8"

{email["content_body"]}
"""
                # 保存邮件内容
                self.db_handler.save_email_content(email["message_id"], full_content)

                # 保存邮件元数据
                self.db_handler.save_email_metadata(
                    message_id=email["message_id"],
                    from_addr=email["from_addr"],
                    to_addrs=email["to_addrs"],
                    subject=email["subject"],
                    date=now,
                    size=len(full_content),
                )

            logger.info(f"已创建 {len(test_emails)} 封测试邮件")
        except Exception as e:
            logger.error(f"创建测试邮件时出错: {e}")
            logger.error(f"异常详情: {traceback.format_exc()}")
