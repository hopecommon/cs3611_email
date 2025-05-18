"""
通过ID查看邮件 - 使用邮件ID而不是文件路径查看邮件内容
"""

import os
import sys
import argparse
import sqlite3
from pathlib import Path
from email import policy
from email.parser import BytesParser
import datetime
import re
import html
from email.header import decode_header

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging, safe_print
from server.db_handler import DatabaseHandler
from tools.view_email import (
    decode_str,
    decode_header_str,
    print_headers,
    print_text_content,
    print_html_content,
    print_attachments,
    extract_attachments,
    print_email_summary,
)

# 设置日志
logger = setup_logging("view_email_by_id")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="通过ID查看邮件")
    parser.add_argument("message_id", type=str, help="邮件ID或ID的一部分")
    parser.add_argument(
        "--type",
        choices=["sent", "received", "all"],
        default="all",
        help="邮件类型：已发送(sent)、已接收(received)或全部(all)",
    )
    parser.add_argument("--raw", action="store_true", help="显示原始内容")
    parser.add_argument("--html", action="store_true", help="显示HTML内容")
    parser.add_argument("--text", action="store_true", help="显示纯文本内容")
    parser.add_argument("--headers", action="store_true", help="只显示邮件头")
    parser.add_argument("--attachments", action="store_true", help="只显示附件信息")
    parser.add_argument("--extract", type=str, help="提取附件到指定目录")
    parser.add_argument("--list", action="store_true", help="列出所有匹配的邮件")
    return parser.parse_args()


def find_emails_by_id(db_handler, message_id_part, email_type="all"):
    """根据ID的一部分查找邮件"""
    results = []

    # 查找已接收邮件
    if email_type in ["all", "received"]:
        try:
            # 使用数据库连接
            conn = sqlite3.connect(db_handler.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM emails WHERE message_id LIKE ?",
                (f"%{message_id_part}%",),
            )

            for row in cursor.fetchall():
                item = dict(row)
                item["type"] = "received"
                results.append(item)

            conn.close()

        except Exception as e:
            logger.error(f"查找已接收邮件时出错: {e}")

    # 查找已发送邮件
    if email_type in ["all", "sent"]:
        try:
            # 使用数据库连接
            conn = sqlite3.connect(db_handler.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM sent_emails WHERE message_id LIKE ?",
                (f"%{message_id_part}%",),
            )

            for row in cursor.fetchall():
                item = dict(row)
                item["type"] = "sent"
                results.append(item)

            conn.close()

        except Exception as e:
            logger.error(f"查找已发送邮件时出错: {e}")

    return results


def print_email_list(emails):
    """打印邮件列表"""
    if not emails:
        print("没有找到匹配的邮件")
        return

    print(f"找到{len(emails)}封匹配的邮件:")
    print("ID\t类型\t日期\t\t\t主题")
    print("-" * 80)

    for email in emails:
        # 格式化日期
        date = datetime.datetime.fromisoformat(email["date"]).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # 格式化主题
        subject = email["subject"] if email["subject"] else "(无主题)"
        if len(subject) > 40:
            subject = subject[:37] + "..."

        # 邮件类型
        email_type = "已发送" if email["type"] == "sent" else "已接收"

        # 显示邮件ID（只显示前20个字符）
        message_id = email["message_id"]
        if len(message_id) > 20:
            message_id = message_id[:17] + "..."

        safe_print(f"{message_id}\t{email_type}\t{date}\t{subject}")


def main():
    """主函数"""
    args = parse_args()

    # 创建数据库处理器
    db_handler = DatabaseHandler()

    # 查找匹配的邮件
    emails = find_emails_by_id(db_handler, args.message_id, args.type)

    # 如果只是列出邮件
    if args.list or len(emails) > 1:
        print_email_list(emails)

        if len(emails) > 1 and not args.list:
            print(
                "\n找到多个匹配的邮件，请使用更具体的ID或添加--list参数查看所有匹配项"
            )
        return

    # 如果没有找到邮件
    if not emails:
        print(f"没有找到ID包含 '{args.message_id}' 的邮件")
        return

    # 获取邮件内容
    email = emails[0]
    email_type = email["type"]
    content_path = email["content_path"]

    # 检查文件是否存在
    if not os.path.exists(content_path):
        print(f"邮件文件不存在: {content_path}")
        return

    try:
        # 解析.eml文件
        with open(content_path, "rb") as f:
            parser = BytesParser(policy=policy.default)
            msg = parser.parse(f)

        # 根据参数显示不同内容
        if args.raw:
            # 显示原始内容
            with open(content_path, "r", encoding="utf-8", errors="replace") as f:
                print(f.read())
        elif args.headers:
            # 只显示邮件头
            print_headers(msg)
        elif args.text:
            # 只显示纯文本内容
            print_text_content(msg)
        elif args.html:
            # 只显示HTML内容
            print_html_content(msg)
        elif args.attachments:
            # 只显示附件信息
            print_attachments(msg)
        elif args.extract:
            # 提取附件
            extract_attachments(msg, args.extract)
        else:
            # 显示摘要和内容
            print(f"邮件类型: {'已发送' if email_type == 'sent' else '已接收'}")
            print(f"邮件ID: {email['message_id']}")
            print(f"文件路径: {content_path}")
            print()
            print_email_summary(msg)
            print_text_content(msg)
            print_attachments(msg)

    except Exception as e:
        logger.error(f"查看邮件失败: {e}")
        print(f"查看邮件失败: {e}")


if __name__ == "__main__":
    main()
