#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
邮件元数据测试脚本
用于测试数据库中邮件元数据的存储情况
"""

import sys
import os
import json
import sqlite3
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from server.db_handler import DatabaseHandler
from common.config import DB_PATH, EMAIL_STORAGE_DIR


def print_hr(width=60):
    """打印水平分隔线"""
    print("=" * width)


def test_email_database():
    """测试数据库中的邮件元数据"""
    print_hr()
    print("测试数据库中的邮件元数据")
    print_hr()

    # 创建数据库处理器
    db = DatabaseHandler()

    # 获取所有邮件
    emails = db.list_emails()
    print(f"数据库中共有 {len(emails)} 封邮件")

    # 遍历所有邮件
    for i, email in enumerate(emails, 1):
        print(f"\n邮件 {i}/{len(emails)}:")
        print_hr()
        print(f"Message-ID: {email.get('message_id', '')}")
        print(f"主题: {email.get('subject', '')}")
        print(f"发件人: {email.get('from_addr', '')}")

        # 处理收件人
        to_addrs = email.get("to_addrs", [])
        if isinstance(to_addrs, list):
            to_addr_str = ", ".join(to_addrs)
        else:
            to_addr_str = str(to_addrs)
        print(f"收件人: {to_addr_str}")

        print(f"日期: {email.get('date', '')}")
        print(f"大小: {email.get('size', 0)} 字节")
        print(f"内容路径: {email.get('content_path', '')}")

        # 检查邮件文件是否存在
        content_path = email.get("content_path", "")
        if content_path and os.path.exists(content_path):
            print(f"邮件文件存在: {content_path}")
            # 读取文件内容的前几行
            try:
                with open(content_path, "r", encoding="utf-8") as f:
                    headers = []
                    for _ in range(10):
                        line = f.readline().strip()
                        if not line:
                            break
                        headers.append(line)
                print("\n邮件头:")
                for header in headers:
                    print(f"  {header}")
            except Exception as e:
                print(f"读取邮件文件时出错: {e}")
        else:
            print(f"邮件文件不存在: {content_path}")

        print_hr(30)


def test_raw_database():
    """直接查询SQLite数据库"""
    print_hr()
    print("直接查询SQLite数据库")
    print_hr()

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 查询emails表的结构
        cursor.execute("PRAGMA table_info(emails)")
        columns = cursor.fetchall()
        print("emails表结构:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        print()

        # 查询邮件数据
        cursor.execute(
            "SELECT message_id, from_addr, to_addrs, subject, date FROM emails"
        )
        rows = cursor.fetchall()
        print(f"数据库中共有 {len(rows)} 封邮件")

        for i, row in enumerate(rows, 1):
            print(f"\n邮件 {i}/{len(rows)} (原始数据):")
            print(f"Message-ID: {row[0]}")
            print(f"发件人: {row[1]}")
            print(f"收件人 (raw): {row[2]}")
            try:
                to_addrs = json.loads(row[2])
                if isinstance(to_addrs, list):
                    if to_addrs and isinstance(to_addrs[0], dict):
                        to_addr_str = ", ".join(
                            addr.get("address", "") for addr in to_addrs
                        )
                    else:
                        to_addr_str = ", ".join(to_addrs)
                else:
                    to_addr_str = str(to_addrs)
                print(f"收件人 (parsed): {to_addr_str}")
            except Exception as e:
                print(f"解析to_addrs时出错: {e}")

            print(f"主题: {row[3]}")
            print(f"日期: {row[4]}")
            print_hr(30)

        conn.close()
    except Exception as e:
        print(f"查询数据库时出错: {e}")


if __name__ == "__main__":
    test_email_database()
    print("\n")
    test_raw_database()
