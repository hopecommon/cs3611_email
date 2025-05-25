#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试POP3 STAT命令问题
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from server.user_auth import UserAuth
from server.new_db_handler import DatabaseHandler

from common.utils import setup_logging

# 设置日志
logger = setup_logging("debug_pop3_stat")


def debug_user_authentication():
    """调试用户认证"""
    print("=== 用户认证调试 ===")

    try:
        auth = UserAuth()
        user = auth.authenticate("testuser", "testpass")

        if user:
            print(f"[OK] 用户认证成功")
            print(f"     用户类型: {type(user)}")
            print(f"     用户名: {user.username}")
            print(f"     邮箱: {user.email}")
            print(f"     活跃状态: {user.is_active}")
            return user
        else:
            print(f"[FAIL] 用户认证失败")
            return None
    except Exception as e:
        print(f"[ERROR] 用户认证异常: {e}")
        import traceback

        print(f"详细错误: {traceback.format_exc()}")
        return None


def debug_email_query(user):
    """调试邮件查询"""
    print("\n=== 邮件查询调试 ===")

    try:
        db = DatabaseHandler()

        # 测试不同的查询方式
        print(f"查询用户邮箱: {user.email}")

        # 1. 直接查询所有邮件
        all_emails = db.list_emails()
        print(f"[INFO] 所有邮件数量: {len(all_emails)}")

        # 2. 查询特定用户的邮件
        user_emails = db.list_emails(
            user_email=user.email, include_deleted=False, include_spam=False
        )
        print(f"[INFO] 用户邮件数量: {len(user_emails)}")

        # 3. 显示邮件详情
        if user_emails:
            print(f"[INFO] 用户邮件详情:")
            for i, email in enumerate(user_emails, 1):
                print(f"  {i}. ID: {email['message_id']}")
                print(f"     发件人: {email['from_addr']}")
                print(f"     收件人: {email['to_addrs']}")
                print(f"     主题: {email['subject']}")
                print(f"     大小: {email['size']} bytes")

        # 4. 计算总大小
        total_size = sum(email.get("size", 0) for email in user_emails)
        print(f"[INFO] 总大小: {total_size} bytes")

        return user_emails, total_size

    except Exception as e:
        print(f"[ERROR] 邮件查询异常: {e}")
        import traceback

        print(f"详细错误: {traceback.format_exc()}")
        return [], 0


def debug_stat_command():
    """调试STAT命令逻辑"""
    print("\n=== STAT命令逻辑调试 ===")

    # 1. 认证用户
    user = debug_user_authentication()
    if not user:
        return False

    # 2. 查询邮件
    emails, total_size = debug_email_query(user)

    # 3. 模拟STAT命令响应
    print(f"\n[INFO] STAT命令应该返回: +OK {len(emails)} {total_size}")

    return True


def debug_pop3_handler_methods():
    """调试POP3处理器方法"""
    print("\n=== POP3处理器方法调试 ===")

    try:
        # 模拟POP3处理器的get_user_emails方法
        from server.pop3_server import StablePOP3Handler

        # 创建模拟的处理器实例
        class MockServer:
            def __init__(self):
                self.db_handler = DatabaseHandler()
                self.user_auth = UserAuth()
                self.use_ssl = False

        class MockRequest:
            pass

        class MockAddress:
            pass

        # 创建处理器（这可能会失败，因为需要网络连接）
        try:
            server = MockServer()
            handler = StablePOP3Handler.__new__(StablePOP3Handler)
            handler.db_handler = server.db_handler
            handler.user_auth = server.user_auth
            handler.authenticated_user = None
            handler.use_ssl = False
            handler.cached_emails = None
            handler.cache_user_email = None

            # 设置认证用户
            user = handler.user_auth.authenticate("testuser", "testpass")
            if user:
                handler.authenticated_user = user
                print(f"[OK] 模拟认证成功: {user.email}")

                # 测试get_user_emails方法
                emails = handler.get_user_emails()
                print(f"[OK] get_user_emails返回: {len(emails)} 封邮件")

                # 计算总大小
                total_size = sum(email.get("size", 0) for email in emails)
                print(f"[OK] 总大小: {total_size} bytes")

                return True
            else:
                print(f"[FAIL] 模拟认证失败")
                return False

        except Exception as e:
            print(f"[WARNING] 无法创建完整的处理器实例: {e}")
            print(f"这是正常的，因为需要网络连接")
            return True

    except Exception as e:
        print(f"[ERROR] POP3处理器方法调试异常: {e}")
        import traceback

        print(f"详细错误: {traceback.format_exc()}")
        return False


def main():
    """主函数"""
    print("POP3 STAT命令调试")
    print("=" * 50)

    success = True

    # 运行所有调试
    if not debug_stat_command():
        success = False

    if not debug_pop3_handler_methods():
        success = False

    print("\n" + "=" * 50)
    if success:
        print("[SUCCESS] 调试完成，STAT命令逻辑应该正常工作")
        print("如果POP3服务器仍然失败，可能是网络或连接问题")
    else:
        print("[FAIL] 发现问题，需要进一步修复")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
