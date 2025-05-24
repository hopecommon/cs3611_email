#!/usr/bin/env python
"""
示例：搜索邮件

此脚本演示如何使用邮件客户端搜索邮件。
"""

import sys
import os
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from server.new_db_handler import EmailService as DatabaseHandler

# 设置日志
logger = setup_logging("example_search")


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="搜索邮件")
    parser.add_argument("query", help="搜索关键词")
    parser.add_argument(
        "--fields",
        help="搜索字段，逗号分隔 (subject,sender,recipients)",
        default="subject,sender,recipients",
    )
    parser.add_argument("--content", action="store_true", help="搜索邮件内容")
    parser.add_argument("--sent-only", action="store_true", help="只搜索已发送邮件")
    parser.add_argument("--received-only", action="store_true", help="只搜索已接收邮件")
    parser.add_argument("--include-deleted", action="store_true", help="包含已删除邮件")
    parser.add_argument("--limit", type=int, default=100, help="最大结果数量")

    args = parser.parse_args()

    # 创建数据库处理器
    db_handler = DatabaseHandler()

    # 解析搜索字段
    search_in = args.fields.split(",") if args.fields else None

    # 设置搜索参数
    include_sent = not args.received_only
    include_received = not args.sent_only

    # 搜索邮件
    try:
        print(f"正在搜索: {args.query}")
        emails = db_handler.search_emails(
            query=args.query,
            search_in=search_in,
            include_sent=include_sent,
            include_received=include_received,
            include_deleted=args.include_deleted,
            search_content=args.content,
            limit=args.limit,
        )

        if not emails:
            print("未找到匹配的邮件")
            return

        # 显示搜索结果
        print(f"\n找到 {len(emails)} 封匹配的邮件:")
        print(f"{'ID':<5} {'文件夹':<8} {'日期':<20} {'发件人':<30} {'主题':<40}")
        print("-" * 100)

        for i, email in enumerate(emails):
            folder = "已发送" if email.get("folder") == "sent" else "收件箱"
            date = email.get("date", "")
            sender = email.get("sender", "")
            subject = email.get("subject", "")

            print(f"{i+1:<5} {folder:<8} {date:<20} {sender:<30} {subject:<40}")

        # 询问是否查看邮件详情
        while True:
            choice = input("\n请输入要查看的邮件ID (或按回车退出): ")
            if not choice:
                break

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(emails):
                    email = emails[idx]

                    print("\n===== 邮件详情 =====")
                    print(f"ID: {email.get('id')}")
                    print(f"主题: {email.get('subject', '')}")
                    print(f"发件人: {email.get('sender', '')}")
                    print(f"收件人: {email.get('recipients', '')}")
                    print(f"日期: {email.get('date', '')}")
                    print(
                        f"文件夹: {'已发送' if email.get('folder') == 'sent' else '收件箱'}"
                    )

                    # 获取邮件内容
                    email_content = db_handler.get_email_content(email.get("id"))

                    if email_content:
                        print("\n----- 邮件正文 -----")
                        if email_content.get("html_content"):
                            print("[HTML内容可用]")
                            view_html = (
                                input("是否查看HTML内容? (y/n): ").lower() == "y"
                            )
                            if view_html:
                                print("\n" + email_content.get("html_content"))
                            else:
                                print(
                                    "\n"
                                    + (
                                        email_content.get("text_content")
                                        or "无纯文本内容"
                                    )
                                )
                        else:
                            print(
                                "\n" + (email_content.get("text_content") or "无内容")
                            )

                        # 显示附件信息
                        attachments = email_content.get("attachments", [])
                        if attachments:
                            print("\n----- 附件 -----")
                            for i, attachment in enumerate(attachments):
                                print(
                                    f"{i+1}. {attachment.get('filename')} ({attachment.get('content_type')})"
                                )
                    else:
                        print("\n无法获取邮件内容")
                else:
                    print("无效的ID")
            except ValueError:
                print("请输入有效的数字")
    except Exception as e:
        print(f"搜索邮件时出错: {e}")


if __name__ == "__main__":
    main()
