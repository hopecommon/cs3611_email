#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户管理工具 - 管理Web应用用户账户
"""

import sys
import sqlite3
import hashlib
import secrets
import uuid
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from server.user_auth import UserAuth


class UserManager:
    """用户管理工具"""

    def __init__(self, db_path="data/emails_dev.db"):
        """初始化用户管理器"""
        self.db_path = str(Path(__file__).resolve().parent / db_path)
        print(f"📁 使用数据库: {self.db_path}")

    def _hash_password(self, password, salt=None):
        """
        使用与Web应用相同的密码哈希方法

        Args:
            password: 原始密码
            salt: 盐值，如果为None则生成新的盐值

        Returns:
            (hashed_password, salt)元组
        """
        if salt is None:
            salt = uuid.uuid4().hex

        # 使用与common.utils.hash_password相同的方法
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        return hashed, salt

    def list_users(self):
        """列出所有用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT username, email, full_name, is_active, last_login
                FROM users 
                ORDER BY username
            """
            )

            users = cursor.fetchall()
            conn.close()

            if not users:
                print("📭 数据库中没有用户")
                return

            print(f"\n👥 找到 {len(users)} 个用户:")
            print("-" * 70)
            print(
                f"{'用户名':<15} {'邮箱':<25} {'全名':<15} {'状态':<8} {'最后登录':<12}"
            )
            print("-" * 70)

            for user in users:
                username, email, full_name, is_active, last_login = user
                status = "✅活跃" if is_active else "❌禁用"
                login_date = last_login[:10] if last_login else "从未登录"

                print(
                    f"{username:<15} {email:<25} {(full_name or ''):<15} {status:<8} {login_date:<12}"
                )

            print("-" * 70)

        except Exception as e:
            print(f"❌ 查询用户失败: {e}")
            import traceback

            traceback.print_exc()

    def create_user(self, username, email, password, full_name=""):
        """创建新用户"""
        try:
            user_auth = UserAuth(self.db_path)

            # 检查用户是否已存在
            existing_user = user_auth.get_user_by_username(username)
            if existing_user:
                print(f"❌ 用户名 '{username}' 已存在")
                return False

            # 检查邮箱是否已存在
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                print(f"❌ 邮箱 '{email}' 已被使用")
                conn.close()
                return False
            conn.close()

            # 创建用户
            user_record = user_auth.create_user(username, email, password, full_name)
            if user_record:
                print(f"✅ 用户 '{username}' 创建成功")
                return True
            else:
                print(f"❌ 用户 '{username}' 创建失败")
                return False

        except Exception as e:
            print(f"❌ 创建用户失败: {e}")
            return False

    def reset_password(self, username, new_password):
        """重置用户密码"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 检查用户是否存在（使用username作为主键）
            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if not user:
                print(f"❌ 用户 '{username}' 不存在")
                conn.close()
                return False

            # 使用正确的密码哈希方法
            password_hash, salt = self._hash_password(new_password)

            # 更新密码
            cursor.execute(
                """
                UPDATE users 
                SET password_hash = ?, salt = ?
                WHERE username = ?
            """,
                (password_hash, salt, username),
            )

            conn.commit()
            conn.close()

            print(f"✅ 用户 '{username}' 密码重置成功")
            return True

        except Exception as e:
            print(f"❌ 重置密码失败: {e}")
            return False

    def delete_user(self, username):
        """删除用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 检查用户是否存在（使用username作为主键）
            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if not user:
                print(f"❌ 用户 '{username}' 不存在")
                conn.close()
                return False

            # 删除用户
            cursor.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
            conn.close()

            print(f"✅ 用户 '{username}' 已删除")
            return True

        except Exception as e:
            print(f"❌ 删除用户失败: {e}")
            return False

    def clear_all_users(self):
        """清空所有用户（危险操作）"""
        print("⚠️  这将删除所有用户数据，此操作不可撤销！")
        confirm = input("请输入 'CONFIRM' 来确认操作: ")

        if confirm != "CONFIRM":
            print("❌ 操作已取消")
            return False

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM users")
            conn.commit()
            conn.close()

            print("✅ 所有用户数据已清空")
            return True

        except Exception as e:
            print(f"❌ 清空用户失败: {e}")
            return False


def main():
    """主菜单"""
    manager = UserManager()

    while True:
        print("\n" + "=" * 50)
        print("🔧 用户管理工具")
        print("=" * 50)
        print("1. 查看所有用户")
        print("2. 创建新用户")
        print("3. 重置用户密码")
        print("4. 删除用户")
        print("5. 清空所有用户")
        print("0. 退出")
        print("-" * 50)

        try:
            choice = input("请选择操作 [0-5]: ").strip()

            if choice == "0":
                print("👋 再见！")
                break

            elif choice == "1":
                manager.list_users()

            elif choice == "2":
                print("\n➕ 创建新用户")
                username = input("用户名: ").strip()
                email = input("邮箱: ").strip()
                password = input("密码: ").strip()
                full_name = input("全名 (可选): ").strip()

                if username and email and password:
                    manager.create_user(username, email, password, full_name)
                else:
                    print("❌ 用户名、邮箱和密码不能为空")

            elif choice == "3":
                print("\n🔑 重置用户密码")
                username = input("用户名: ").strip()
                new_password = input("新密码: ").strip()

                if username and new_password:
                    manager.reset_password(username, new_password)
                else:
                    print("❌ 用户名和密码不能为空")

            elif choice == "4":
                print("\n🗑️ 删除用户")
                username = input("用户名: ").strip()

                if username:
                    confirm = (
                        input(f"确定要删除用户 '{username}' 吗？[y/N]: ")
                        .strip()
                        .lower()
                    )
                    if confirm == "y":
                        manager.delete_user(username)
                    else:
                        print("❌ 操作已取消")
                else:
                    print("❌ 用户名不能为空")

            elif choice == "5":
                manager.clear_all_users()

            else:
                print("❌ 无效选择，请重试")

        except KeyboardInterrupt:
            print("\n\n👋 操作已中断，再见！")
            break
        except Exception as e:
            print(f"❌ 操作失败: {e}")


if __name__ == "__main__":
    main()
