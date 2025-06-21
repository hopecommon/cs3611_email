#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import sqlite3
sys.path.append('.')

def fix_spam_content():
    """修复垃圾邮件内容处理问题"""
    print("=== 修复垃圾邮件内容处理问题 ===\n")
    
    try:
        # 1. 直接在数据库中更新明显的垃圾邮件
        print("1. 直接更新数据库中的垃圾邮件状态:")
        
        conn = sqlite3.connect("data/email_db.sqlite")
        cursor = conn.cursor()
        
        # 查找包含垃圾关键词的邮件
        spam_keywords = ["奖金发放", "中奖", "恭喜", "领取", "免费", "促销"]
        updated_count = 0
        
        for keyword in spam_keywords:
            cursor.execute(
                "SELECT message_id, subject, is_spam FROM emails WHERE subject LIKE ? AND is_spam = 0", 
                (f"%{keyword}%",)
            )
            matching_emails = cursor.fetchall()
            
            if matching_emails:
                print(f"   处理包含'{keyword}'的邮件:")
                for msg_id, subject, is_spam in matching_emails:
                    print(f"     - 更新: {subject[:40]}...")
                    cursor.execute(
                        "UPDATE emails SET is_spam = 1, spam_score = 3.0 WHERE message_id = ?", 
                        (msg_id,)
                    )
                    updated_count += 1
        
        conn.commit()
        print(f"   ✅ 共更新了 {updated_count} 封邮件")
        
        # 2. 验证更新结果
        print("\n2. 验证更新结果:")
        cursor.execute("SELECT COUNT(*) FROM emails WHERE is_spam = 1")
        spam_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM emails")
        total_count = cursor.fetchone()[0]
        
        print(f"   总邮件数: {total_count}")
        print(f"   垃圾邮件数: {spam_count}")
        print(f"   垃圾邮件比例: {spam_count/total_count*100:.1f}%" if total_count > 0 else "   垃圾邮件比例: 0%")
        
        # 3. 显示垃圾邮件列表
        print("\n3. 当前垃圾邮件列表:")
        cursor.execute("SELECT subject, spam_score FROM emails WHERE is_spam = 1")
        spam_emails = cursor.fetchall()
        
        for subject, spam_score in spam_emails:
            print(f"   - {subject[:50]}... [评分:{spam_score}]")
        
        conn.close()
        
        print("\n=== 修复完成 ===")
        print("\n💡 现在你可以测试过滤功能:")
        print("   1. 运行 python cli.py")
        print("   2. 选择 '收件箱'")
        print("   3. 选择 '2. 仅显示正常邮件' - 应该不显示垃圾邮件")
        print("   4. 选择 '3. 仅显示垃圾邮件' - 应该只显示垃圾邮件")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_spam_content()
