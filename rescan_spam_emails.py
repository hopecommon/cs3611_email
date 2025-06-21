#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import sqlite3
sys.path.append('.')

def rescan_spam_emails():
    """重新扫描所有邮件的垃圾状态"""
    print("=== 重新扫描邮件垃圾状态 ===\n")
    
    try:
        # 1. 初始化垃圾过滤器和数据库处理器
        from spam_filter.spam_filter import KeywordSpamFilter
        from server.new_db_handler import DatabaseHandler
        
        spam_filter = KeywordSpamFilter()
        db_handler = DatabaseHandler()
        
        print("✅ 垃圾过滤器和数据库处理器初始化成功")
        
        # 2. 获取所有邮件
        all_emails = db_handler.list_emails(limit=1000, include_spam=True)
        print(f"📊 找到 {len(all_emails)} 封邮件需要重新扫描")
        
        if not all_emails:
            print("📭 没有邮件需要扫描")
            return
        
        # 3. 逐个重新评估邮件
        updated_count = 0
        spam_found = 0
        normal_found = 0
        
        print("\n🔍 开始重新扫描...")
        print("-" * 60)
        
        for i, email in enumerate(all_emails, 1):
            try:
                message_id = email.get('message_id', '')
                subject = email.get('subject', '')
                from_addr = email.get('from_addr', '')
                current_is_spam = email.get('is_spam', False)
                current_spam_score = email.get('spam_score', 0.0)
                
                print(f"[{i}/{len(all_emails)}] 处理: {subject[:40]}...")
                
                # 获取邮件内容用于分析
                email_with_content = db_handler.get_email(message_id, include_content=True)
                content = ""
                if email_with_content:
                    content = email_with_content.get('content', '')
                
                # 使用垃圾过滤器重新分析
                analysis_data = {
                    "from_addr": from_addr,
                    "subject": subject,
                    "content": content
                }
                
                result = spam_filter.analyze_email(analysis_data)
                new_is_spam = result["is_spam"]
                new_spam_score = result["score"]
                
                # 检查是否需要更新
                if new_is_spam != current_is_spam or abs(new_spam_score - current_spam_score) > 0.1:
                    # 更新数据库
                    success = db_handler.update_email(
                        message_id, 
                        is_spam=new_is_spam, 
                        spam_score=new_spam_score
                    )
                    
                    if success:
                        updated_count += 1
                        status_old = "垃圾" if current_is_spam else "正常"
                        status_new = "垃圾" if new_is_spam else "正常"
                        print(f"  ✅ 更新: [{status_old}→{status_new}] 评分:{current_spam_score:.1f}→{new_spam_score:.1f}")
                        
                        if result["matched_keywords"]:
                            print(f"     匹配关键词: {result['matched_keywords']}")
                    else:
                        print(f"  ❌ 更新失败")
                else:
                    # 状态没有变化
                    status = "垃圾" if current_is_spam else "正常"
                    print(f"  ➡️  无变化: [{status}] 评分:{current_spam_score:.1f}")
                
                # 统计
                if new_is_spam:
                    spam_found += 1
                else:
                    normal_found += 1
                    
            except Exception as e:
                print(f"  ❌ 处理邮件时出错: {e}")
                continue
        
        # 4. 显示结果统计
        print("\n" + "=" * 60)
        print("📊 重新扫描结果统计:")
        print(f"  总邮件数: {len(all_emails)}")
        print(f"  更新邮件数: {updated_count}")
        print(f"  垃圾邮件数: {spam_found}")
        print(f"  正常邮件数: {normal_found}")
        print(f"  垃圾邮件比例: {spam_found/len(all_emails)*100:.1f}%")
        
        if updated_count > 0:
            print(f"\n✅ 成功更新了 {updated_count} 封邮件的垃圾状态")
        else:
            print(f"\n📝 所有邮件的垃圾状态都是最新的")
        
        # 5. 验证过滤功能
        print("\n🧪 验证过滤功能...")
        
        # 测试仅显示正常邮件
        normal_emails = db_handler.list_emails(include_spam=False, is_spam=False, limit=100)
        print(f"  仅正常邮件查询: {len(normal_emails)} 封")
        
        # 测试仅显示垃圾邮件
        spam_emails = db_handler.list_emails(include_spam=True, is_spam=True, limit=100)
        print(f"  仅垃圾邮件查询: {len(spam_emails)} 封")
        
        # 验证过滤结果
        if normal_emails:
            has_spam_in_normal = any(email.get('is_spam', False) for email in normal_emails)
            if has_spam_in_normal:
                print("  ❌ 正常邮件查询中包含垃圾邮件")
            else:
                print("  ✅ 正常邮件查询结果正确")
        
        if spam_emails:
            has_normal_in_spam = any(not email.get('is_spam', True) for email in spam_emails)
            if has_normal_in_spam:
                print("  ❌ 垃圾邮件查询中包含正常邮件")
            else:
                print("  ✅ 垃圾邮件查询结果正确")
        
        print("\n=== 重新扫描完成 ===")
        
    except Exception as e:
        print(f"❌ 重新扫描失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    rescan_spam_emails()
