"""
新的EmailService API演示脚本
展示重构后的数据库处理器如何简化邮件操作
"""

import os
import sys
import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.new_db_handler import EmailService


def demo_basic_operations():
    """演示基本操作"""
    print("=" * 50)
    print("基本操作演示")
    print("=" * 50)

    # 初始化邮件服务
    email_service = EmailService()

    # 1. 保存邮件 - 新的统一接口
    print("\n1. 保存邮件（新API）:")
    success = email_service.save_email(
        message_id="<demo@example.com>",
        from_addr="demo@example.com",
        to_addrs=["user@example.com"],
        subject="演示邮件",
        content="这是一个演示邮件的内容。",
        date=datetime.datetime.now(),
    )
    print(f"   保存结果: {'成功' if success else '失败'}")

    # 2. 获取邮件 - 简洁的API
    print("\n2. 获取邮件（新API）:")
    email = email_service.get_email("<demo@example.com>", include_content=True)
    if email:
        print(f"   主题: {email['subject']}")
        print(f"   发件人: {email['from_addr']}")
        print(f"   收件人: {email['to_addrs']}")
        print(f"   内容长度: {len(email.get('content', ''))}")

    # 3. 更新邮件状态 - 统一的更新接口
    print("\n3. 更新邮件状态（新API）:")
    success = email_service.update_email("<demo@example.com>", is_read=True)
    print(f"   标记为已读: {'成功' if success else '失败'}")

    # 4. 列出邮件 - 简化的参数
    print("\n4. 列出邮件（简化参数）:")
    emails = email_service.list_emails(limit=3)
    print(f"   获取到 {len(emails)} 封邮件")
    for i, email in enumerate(emails, 1):
        print(f"   {i}. {email['subject']} - {email['from_addr']}")


def demo_compatibility():
    """演示兼容性"""
    print("\n" + "=" * 50)
    print("兼容性演示 - 旧方法仍然可用")
    print("=" * 50)

    email_service = EmailService()

    # 使用旧的方法名
    print("\n1. 使用兼容性方法:")

    # 旧方法仍然可用
    metadata = email_service.get_email_metadata("<demo@example.com>")
    if metadata:
        print(f"   get_email_metadata(): 成功")

    content = email_service.get_email_content("<demo@example.com>")
    if content:
        print(f"   get_email_content(): 成功 (长度: {len(content)})")

    success = email_service.mark_email_as_read("<demo@example.com>")
    print(f"   mark_email_as_read(): {'成功' if success else '失败'}")


def demo_advanced_features():
    """演示高级功能"""
    print("\n" + "=" * 50)
    print("高级功能演示")
    print("=" * 50)

    email_service = EmailService()

    # 1. 邮件搜索
    print("\n1. 邮件搜索:")
    search_results = email_service.search_emails("演示", limit=5)
    print(f"   搜索'演示'找到 {len(search_results)} 个结果")

    # 2. 邮件计数
    print("\n2. 邮件统计:")
    total_count = email_service.get_email_count()
    unread_count = email_service.get_unread_count()
    print(f"   总邮件数: {total_count}")
    print(f"   未读邮件数: {unread_count}")

    # 3. 已发送邮件操作
    print("\n3. 已发送邮件操作:")
    sent_emails = email_service.list_sent_emails(limit=3)
    print(f"   已发送邮件: {len(sent_emails)} 封")


def demo_error_fixes():
    """演示错误修复"""
    print("\n" + "=" * 50)
    print("错误修复演示 - 原本不存在的方法现在可用")
    print("=" * 50)

    email_service = EmailService()

    # 这些方法在原来的DatabaseHandler中不存在，但现在可用
    print("\n修复的方法调用:")

    # 原来CLI中的错误调用，现在可以正常工作
    emails = email_service.get_emails("inbox")
    print(f"   get_emails('inbox'): 获取到 {len(emails)} 封邮件")

    sent_emails = email_service.get_sent_emails()
    print(f"   get_sent_emails(): 获取到 {len(sent_emails)} 封已发送邮件")


def compare_old_vs_new():
    """对比旧方式与新方式"""
    print("\n" + "=" * 50)
    print("新旧API对比")
    print("=" * 50)

    print("\n旧方式（复杂）:")
    print("   # 保存邮件需要两步")
    print(
        "   db.save_email_metadata(id, from_addr, to_addrs, subject, date, size, False, 0.0)"
    )
    print("   db.save_email_content(id, content)")
    print("")
    print("   # 更新状态需要特定方法")
    print("   db.mark_email_as_read(id)")
    print("   db.mark_email_as_deleted(id)")
    print("   db.mark_email_as_spam(id, 0.8)")

    print("\n新方式（简洁）:")
    print("   # 保存邮件一步完成")
    print("   email_service.save_email(id, from_addr, to_addrs, subject, content)")
    print("")
    print("   # 统一的更新接口")
    print("   email_service.update_email(id, is_read=True)")
    print("   email_service.update_email(id, is_deleted=True)")
    print("   email_service.update_email(id, is_spam=True, spam_score=0.8)")

    print("\n优势:")
    print("   ✓ 更少的参数")
    print("   ✓ 统一的接口")
    print("   ✓ 更好的默认值")
    print("   ✓ 更强的类型安全")
    print("   ✓ 模块化设计")


def main():
    """主函数"""
    print("邮件服务API演示")
    print("展示重构后的数据库处理器优势")

    try:
        demo_basic_operations()
        demo_compatibility()
        demo_advanced_features()
        demo_error_fixes()
        compare_old_vs_new()

        print("\n" + "=" * 50)
        print("演示完成！")
        print("=" * 50)
        print("\n总结:")
        print("1. 新API更简洁易用")
        print("2. 保持完全向后兼容")
        print("3. 修复了原有的错误调用")
        print("4. 提供了更好的开发体验")
        print("5. 模块化设计更易维护")

    except Exception as e:
        print(f"演示过程中出错: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
