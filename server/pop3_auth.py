"""
POP3认证模块 - 处理POP3服务器的用户认证
"""

import logging
from typing import Dict, Optional, Tuple

from common.utils import setup_logging
from server.user_auth import UserAuth

# 设置日志
logger = setup_logging("pop3_auth")


class POP3Authenticator:
    """POP3认证器，处理POP3服务器的用户认证"""

    def __init__(self, user_auth: UserAuth, users: Optional[Dict[str, str]] = None):
        """
        初始化POP3认证器

        Args:
            user_auth: 用户认证对象
            users: 用户名到密码的映射，用于简单认证
        """
        self.user_auth = user_auth
        self.users = users or {}
        logger.info(f"POP3认证器已初始化，加载了 {len(self.users)} 个用户")

    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """
        验证用户凭据

        Args:
            username: 用户名
            password: 密码

        Returns:
            (认证是否成功, 用户邮箱地址)
        """
        authenticated = False
        user_email = None
        
        logger.debug(f"开始认证用户: {username}")

        # 尝试使用UserAuth进行认证
        try:
            user = self.user_auth.authenticate(username, password)
            if user:
                authenticated = True
                # 保存用户邮箱地址，用于后续查询邮件
                user_email = user.email
                logger.info(f"用户 {username} 通过UserAuth认证成功 (邮箱: {user_email})")
        except Exception as e:
            logger.error(f"UserAuth认证出错: {e}")
            import traceback
            logger.error(f"异常详情: {traceback.format_exc()}")

        # 如果UserAuth认证失败，尝试使用本地用户字典
        if not authenticated and username in self.users:
            # 检查密码是否匹配
            if self.users[username] == password:
                authenticated = True
                # 如果使用简单认证，假设用户名就是邮箱前缀
                user_email = f"{username}@example.com"
                logger.info(f"用户 {username} 通过本地用户字典认证成功 (默认邮箱: {user_email})")

        if not authenticated:
            logger.warning(f"用户 {username} 认证失败")
            
        return authenticated, user_email

    def get_users(self) -> Dict[str, str]:
        """
        获取用户列表

        Returns:
            用户名到密码的映射
        """
        return self.users

    def load_users_from_user_auth(self) -> Dict[str, str]:
        """
        从UserAuth加载用户列表

        Returns:
            用户名到密码的映射
        """
        try:
            # 从数据库获取用户列表
            users = {}
            user_list = self.user_auth.list_users()

            # 将用户列表转换为字典
            for user in user_list:
                # 注意：这里我们不存储实际密码，而是在认证时使用UserAuth
                # 这里只是为了兼容现有代码，存储一个占位符
                users[user.username] = "password_placeholder"

            # 如果没有用户，添加默认测试用户
            if not users:
                users = {"admin": "admin123", "user1": "user123", "user2": "user123"}
                logger.warning("未找到用户，使用默认测试用户")

            logger.info(f"已加载 {len(users)} 个用户")
            self.users = users
            return users
        except Exception as e:
            logger.error(f"获取用户列表时出错: {e}")
            # 返回默认测试用户
            default_users = {"admin": "admin123", "user1": "user123", "user2": "user123"}
            self.users = default_users
            return default_users
