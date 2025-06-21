#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import sqlite3
sys.path.append('.')

def check_spam_status():
    print("=== 检查邮件垃圾状态 ===\n")
    
    try:
        conn = sqlite3.connect("data/email_db.sqlite")
        cursor = conn.cursor()
        
        # 1. 检查所有邮件的垃圾状态
        print("1. 所有邮件的垃圾状态:")
        cursor.execute("SELECT message_id, subject, is_spam, spam_score FROM emails ORDER BY rowid DESC")
        emails = cursor.fetchall()
        
        spam_count = 0
        normal_count = 0
        
        for msg_id, subject, is_spam, spam_score in emails:
            status = "垃圾" if is_spam else "正常"
            print(f"   - {subject[:40]}... [{status}] 评分:{spam_score}")
            
            if is_spam:
                spam_count += 1
            else:
                normal_count += 1
        
        print(f"\n   统计: 总计{len(emails)}封, 垃圾邮件{spam_count}封, 正常邮件{normal_count}封")
        
        # 2. 检查包含垃圾关键词的邮件
        print("\n2. 包含垃圾关键词但未标记为垃圾的邮件:")
        spam_keywords = ["奖金发放", "中奖", "恭喜", "领取", "免费", "促销"]
        
        found_issues = False
        for keyword in spam_keywords:
            cursor.execute("SELECT message_id, subject, is_spam, spam_score FROM emails WHERE subject LIKE ? AND is_spam = 0", (f"%{keyword}%",))
            matching_emails = cursor.fetchall()
            
            if matching_emails:
                found_issues = True
                print(f"   包含'{keyword}'但未标记为垃圾的邮件:")
                for msg_id, subject, is_spam, spam_score in matching_emails:
                    print(f"     - {subject} [评分:{spam_score}]")
        
        if not found_issues:
            print("   ✅ 没有发现明显的问题")
        
        # 3. 测试垃圾过滤器对现有邮件的判断
        print("\n3. 测试垃圾过滤器对现有邮件的判断:")
        
        from spam_filter.spam_filter import KeywordSpamFilter
        spam_filter = KeywordSpamFilter()
        
        # 检查前几封邮件
        cursor.execute("SELECT message_id, subject, from_addr, is_spam, spam_score FROM emails ORDER BY rowid DESC LIMIT 5")
        test_emails = cursor.fetchall()
        
        for msg_id, subject, from_addr, current_is_spam, current_score in test_emails:
            # 模拟垃圾过滤器分析（注意：这里没有邮件内容，只能基于主题和发件人）
            test_data = {
                "from_addr": from_addr,
                "subject": subject,
                "content": ""  # 没有内容数据
            }
            
            result = spam_filter.analyze_email(test_data)
            predicted_is_spam = result["is_spam"]
            predicted_score = result["score"]
            
            status_current = "垃圾" if current_is_spam else "正常"
            status_predicted = "垃圾" if predicted_is_spam else "正常"
            
            match = "✅" if current_is_spam == predicted_is_spam else "❌"
            
            print(f"   {match} {subject[:30]}...")
            print(f"      当前状态: [{status_current}] 评分:{current_score}")
            print(f"      预测状态: [{status_predicted}] 评分:{predicted_score:.1f}")
            if result["matched_keywords"]:
                print(f"      匹配关键词: {result['matched_keywords']}")
            print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_spam_status()
