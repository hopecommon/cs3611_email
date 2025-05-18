"""
用户认证模块 - 处理用户认证和权限
"""
import os
import sqlite3
import datetime
import secrets
import hashlib
from typing import Dict, List, Optional, Tuple, Any

from common.utils import setup_logging, hash_password, verify_password
from common.config import DB_PATH
from common.models import User

# 设置日志
logger = setup_logging('user_auth')

class UserAuth:
    """用户认证类，处理用户管理和认证"""
    
    def __init__(self, db_path: str = DB_PATH):
        """
        初始化用户认证
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        logger.info(f"用户认证已初始化: {db_path}")
    
    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str = ""
    ) -> Optional[User]:
        """
        创建新用户
        
        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            full_name: 全名
            
        Returns:
            创建的User对象，如果失败则返回None
        """
        try:
            # 检查用户名是否已存在
            if self.get_user_by_username(username):
                logger.warning(f"用户名已存在: {username}")
                return None
            
            # 检查邮箱是否已存在
            if self.get_user_by_email(email):
                logger.warning(f"邮箱已存在: {email}")
                return None
            
            # 哈希密码
            password_hash, salt = hash_password(password)
            
            # 创建用户对象
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                salt=salt,
                full_name=full_name,
                is_active=True,
                created_at=datetime.datetime.now()
            )
            
            # 保存到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            INSERT INTO users (
                username, email, password_hash, salt, full_name,
                is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user.username, user.email, user.password_hash, user.salt,
                user.full_name, 1 if user.is_active else 0,
                user.created_at.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"用户已创建: {username}")
            return user
        except Exception as e:
            logger.error(f"创建用户时出错: {e}")
            return None
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        验证用户凭据
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            验证成功返回User对象，失败返回None
        """
        try:
            # 获取用户
            user = self.get_user_by_username(username)
            if not user:
                logger.warning(f"用户不存在: {username}")
                return None
            
            # 检查用户是否激活
            if not user.is_active:
                logger.warning(f"用户未激活: {username}")
                return None
            
            # 验证密码
            if verify_password(password, user.password_hash, user.salt):
                # 更新最后登录时间
                self.update_last_login(username)
                
                logger.info(f"用户认证成功: {username}")
                return user
            else:
                logger.warning(f"密码错误: {username}")
                return None
        except Exception as e:
            logger.error(f"认证用户时出错: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        通过用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            User对象，如果不存在则返回None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM users WHERE username = ?
            ''', (username,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                # 转换为User对象
                return self._row_to_user(row)
            
            return None
        except Exception as e:
            logger.error(f"获取用户时出错: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        通过邮箱获取用户
        
        Args:
            email: 邮箱
            
        Returns:
            User对象，如果不存在则返回None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM users WHERE email = ?
            ''', (email,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                # 转换为User对象
                return self._row_to_user(row)
            
            return None
        except Exception as e:
            logger.error(f"获取用户时出错: {e}")
            return None
    
    def update_last_login(self, username: str) -> bool:
        """
        更新用户最后登录时间
        
        Args:
            username: 用户名
            
        Returns:
            操作是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.datetime.now().isoformat()
            
            cursor.execute('''
            UPDATE users SET last_login = ? WHERE username = ?
            ''', (now, username))
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"更新最后登录时间时出错: {e}")
            return False
    
    def change_password(self, username: str, new_password: str) -> bool:
        """
        修改用户密码
        
        Args:
            username: 用户名
            new_password: 新密码
            
        Returns:
            操作是否成功
        """
        try:
            # 哈希新密码
            password_hash, salt = hash_password(new_password)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE users SET password_hash = ?, salt = ? WHERE username = ?
            ''', (password_hash, salt, username))
            
            conn.commit()
            conn.close()
            
            logger.info(f"用户密码已修改: {username}")
            return True
        except Exception as e:
            logger.error(f"修改密码时出错: {e}")
            return False
    
    def deactivate_user(self, username: str) -> bool:
        """
        停用用户
        
        Args:
            username: 用户名
            
        Returns:
            操作是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE users SET is_active = 0 WHERE username = ?
            ''', (username,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"用户已停用: {username}")
            return True
        except Exception as e:
            logger.error(f"停用用户时出错: {e}")
            return False
    
    def activate_user(self, username: str) -> bool:
        """
        激活用户
        
        Args:
            username: 用户名
            
        Returns:
            操作是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            UPDATE users SET is_active = 1 WHERE username = ?
            ''', (username,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"用户已激活: {username}")
            return True
        except Exception as e:
            logger.error(f"激活用户时出错: {e}")
            return False
    
    def list_users(self) -> List[User]:
        """
        列出所有用户
        
        Returns:
            User对象列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT * FROM users ORDER BY username
            ''')
            
            users = []
            for row in cursor.fetchall():
                users.append(self._row_to_user(row))
            
            conn.close()
            return users
        except Exception as e:
            logger.error(f"列出用户时出错: {e}")
            return []
    
    def _row_to_user(self, row: sqlite3.Row) -> User:
        """
        将数据库行转换为User对象
        
        Args:
            row: 数据库行
            
        Returns:
            User对象
        """
        # 解析日期
        created_at = datetime.datetime.fromisoformat(row['created_at'])
        last_login = None
        if row['last_login']:
            last_login = datetime.datetime.fromisoformat(row['last_login'])
        
        # 创建User对象
        return User(
            username=row['username'],
            email=row['email'],
            password_hash=row['password_hash'],
            salt=row['salt'],
            full_name=row['full_name'] or "",
            is_active=bool(row['is_active']),
            created_at=created_at,
            last_login=last_login
        )
