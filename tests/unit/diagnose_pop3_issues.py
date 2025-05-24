#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POP3服务器问题诊断脚本
"""

import os
import sys
import json
import sqlite3
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from server.new_db_handler import EmailService as DatabaseHandler
from server.user_auth import UserAuth
from common.utils import setup_logging

# 设置日志
logger = setup_logging("diagnose_pop3")

def diagnose_database_structure():
    """诊断数据库结构"""
    print("=== 数据库结构诊断 ===")
    
    try:
        db_path = "data/email_db.sqlite"
        if not os.path.exists(db_path):
            print("[ERROR] 数据库文件不存在")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表结构
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"[OK] 数据库表: {tables}")
        
        # 检查emails表结构
        cursor.execute("PRAGMA table_info(emails)")
        columns = cursor.fetchall()
        print(f"[OK] emails表字段: {[col[1] for col in columns]}")
        
        # 检查users表结构
        cursor.execute("PRAGMA table_info(users)")
        user_columns = cursor.fetchall()
        print(f"[OK] users表字段: {[col[1] for col in user_columns]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] 数据库结构检查失败: {e}")
        return False

def diagnose_user_data():
    """诊断用户数据"""
    print("\n=== 用户数据诊断 ===")
    
    try:
        user_auth = UserAuth()
        
        # 检查测试用户是否存在
        test_user = user_auth.get_user_by_username("testuser")
        if test_user:
            print(f"[OK] 测试用户存在: {test_user}")
            print(f"     用户名: {test_user['username']}")
            print(f"     邮箱: {test_user['email']}")
            print(f"     活跃状态: {test_user['is_active']}")
        else:
            print("[WARNING] 测试用户不存在，正在创建...")
            success = user_auth.add_user("testuser", "testpass", "testuser@example.com")
            if success:
                print("[OK] 测试用户创建成功")
            else:
                print("[ERROR] 测试用户创建失败")
                return False
        
        # 验证认证
        auth_user = user_auth.authenticate("testuser", "testpass")
        if auth_user:
            print(f"[OK] 用户认证成功: {auth_user['username']}")
        else:
            print("[ERROR] 用户认证失败")
            return False
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 用户数据检查失败: {e}")
        return False

def diagnose_email_data():
    """诊断邮件数据"""
    print("\n=== 邮件数据诊断 ===")
    
    try:
        db = EmailService()
        
        # 检查邮件总数
        all_emails = db.list_emails()
        print(f"[OK] 数据库中总邮件数: {len(all_emails)}")
        
        if all_emails:
            # 显示最新的3封邮件
            print("\n最新的3封邮件:")
            for i, email in enumerate(all_emails[:3], 1):
                print(f"  {i}. ID: {email['message_id']}")
                print(f"     发件人: {email['from_addr']}")
                print(f"     收件人: {email['to_addrs']} (类型: {type(email['to_addrs'])})")
                print(f"     主题: {email['subject']}")
                print(f"     日期: {email['date']}")
                print(f"     大小: {email['size']} bytes")
                print()
        
        # 测试用户邮件查询
        print("=== 用户邮件查询测试 ===")
        test_emails = ["testuser@example.com", "test@example.com", "user@example.com"]
        
        for test_email in test_emails:
            user_emails = db.list_emails(
                user_email=test_email,
                include_deleted=False,
                include_spam=False
            )
            print(f"[INFO] {test_email} 的邮件数量: {len(user_emails)}")
            
            if user_emails:
                print(f"       第一封邮件: {user_emails[0]['message_id']}")
                print(f"       收件人字段: {user_emails[0]['to_addrs']}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 邮件数据检查失败: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        return False

def diagnose_email_matching():
    """诊断邮件匹配逻辑"""
    print("\n=== 邮件匹配逻辑诊断 ===")
    
    try:
        db_path = "data/email_db.sqlite"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 直接查询数据库，检查to_addrs字段的实际格式
        cursor.execute("SELECT message_id, from_addr, to_addrs FROM emails LIMIT 5")
        rows = cursor.fetchall()
        
        print("数据库中to_addrs字段的实际格式:")
        for row in rows:
            message_id, from_addr, to_addrs = row
            print(f"  ID: {message_id}")
            print(f"  发件人: {from_addr}")
            print(f"  收件人原始数据: {to_addrs}")
            print(f"  收件人数据类型: {type(to_addrs)}")
            
            # 尝试解析JSON
            try:
                parsed = json.loads(to_addrs)
                print(f"  解析后数据: {parsed}")
                print(f"  解析后类型: {type(parsed)}")
            except Exception as e:
                print(f"  JSON解析失败: {e}")
            print()
        
        # 测试不同的匹配模式
        test_email = "testuser@example.com"
        print(f"测试邮箱: {test_email}")
        
        # 测试各种匹配模式
        patterns = [
            f'%"address":"{test_email}"%',
            f'%"{test_email}"%',
            f"%<{test_email}>%",
            f"%{test_email}%",
            f'%"email":"{test_email}"%'
        ]
        
        for pattern in patterns:
            cursor.execute("SELECT COUNT(*) FROM emails WHERE to_addrs LIKE ?", (pattern,))
            count = cursor.fetchone()[0]
            print(f"  模式 '{pattern}': {count} 封邮件")
        
        # 测试发件人匹配
        cursor.execute("SELECT COUNT(*) FROM emails WHERE from_addr = ?", (test_email,))
        from_count = cursor.fetchone()[0]
        print(f"  发件人精确匹配: {from_count} 封邮件")
        
        cursor.execute("SELECT COUNT(*) FROM emails WHERE from_addr LIKE ?", (f"%{test_email}%",))
        from_like_count = cursor.fetchone()[0]
        print(f"  发件人模糊匹配: {from_like_count} 封邮件")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] 邮件匹配逻辑检查失败: {e}")
        return False

def diagnose_pop3_methods():
    """诊断POP3服务器调用的方法"""
    print("\n=== POP3方法调用诊断 ===")
    
    try:
        db = EmailService()
        
        # 检查POP3服务器需要的方法是否存在
        required_methods = [
            'list_emails',
            'get_email_content',
            'mark_email_as_deleted'
        ]
        
        for method_name in required_methods:
            if hasattr(db, method_name):
                method = getattr(db, method_name)
                print(f"[OK] 方法 {method_name} 存在")
                print(f"     方法签名: {method.__doc__.split('Args:')[1].split('Returns:')[0].strip() if method.__doc__ and 'Args:' in method.__doc__ else '无文档'}")
            else:
                print(f"[ERROR] 方法 {method_name} 不存在")
        
        # 测试list_emails方法的不同调用方式
        print("\n测试list_emails方法调用:")
        
        # 1. 无参数调用
        try:
            emails1 = db.list_emails()
            print(f"[OK] 无参数调用: 返回 {len(emails1)} 封邮件")
        except Exception as e:
            print(f"[ERROR] 无参数调用失败: {e}")
        
        # 2. 带用户邮箱参数调用
        try:
            emails2 = db.list_emails(user_email="testuser@example.com")
            print(f"[OK] 带用户邮箱调用: 返回 {len(emails2)} 封邮件")
        except Exception as e:
            print(f"[ERROR] 带用户邮箱调用失败: {e}")
        
        # 3. 带所有参数调用（模拟POP3服务器调用）
        try:
            emails3 = db.list_emails(
                user_email="testuser@example.com",
                include_deleted=False,
                include_spam=False
            )
            print(f"[OK] 完整参数调用: 返回 {len(emails3)} 封邮件")
        except Exception as e:
            print(f"[ERROR] 完整参数调用失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] POP3方法调用检查失败: {e}")
        return False

def main():
    """主函数"""
    print("POP3服务器问题诊断")
    print("=" * 50)
    
    results = []
    
    # 运行所有诊断
    results.append(("数据库结构", diagnose_database_structure()))
    results.append(("用户数据", diagnose_user_data()))
    results.append(("邮件数据", diagnose_email_data()))
    results.append(("邮件匹配逻辑", diagnose_email_matching()))
    results.append(("POP3方法调用", diagnose_pop3_methods()))
    
    # 总结结果
    print("\n" + "=" * 50)
    print("诊断结果总结:")
    
    all_passed = True
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n[SUCCESS] 所有诊断通过，POP3服务器应该可以正常工作")
        return 0
    else:
        print("\n[FAILURE] 发现问题，需要修复后才能正常使用POP3服务器")
        return 1

if __name__ == "__main__":
    sys.exit(main())
