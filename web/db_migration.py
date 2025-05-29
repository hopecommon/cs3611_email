#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移脚本 - 为Web邮箱客户端功能添加数据库字段
"""

import sys
import os
import sqlite3
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging

logger = setup_logging("db_migration")


def migrate_users_table(db_path):
    """
    为users表添加邮箱配置相关字段

    Args:
        db_path: 数据库文件路径
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 检查表结构
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]

        # 需要添加的新字段
        new_columns = [
            ("mail_display_name", "TEXT DEFAULT ''"),
            ("smtp_server", "TEXT DEFAULT ''"),
            ("smtp_port", "INTEGER DEFAULT 587"),
            ("smtp_use_tls", "INTEGER DEFAULT 1"),
            ("smtp_username", "TEXT DEFAULT ''"),
            ("encrypted_smtp_password", "TEXT DEFAULT ''"),
            ("pop3_server", "TEXT DEFAULT ''"),
            ("pop3_port", "INTEGER DEFAULT 995"),
            ("pop3_use_ssl", "INTEGER DEFAULT 1"),
            ("pop3_username", "TEXT DEFAULT ''"),
            ("encrypted_pop3_password", "TEXT DEFAULT ''"),
            ("smtp_configured", "INTEGER DEFAULT 0"),
            ("pop3_configured", "INTEGER DEFAULT 0"),
        ]

        migrations_applied = 0

        for column_name, column_def in new_columns:
            if column_name not in columns:
                sql = f"ALTER TABLE users ADD COLUMN {column_name} {column_def}"
                logger.info(f"执行迁移: {sql}")
                cursor.execute(sql)
                migrations_applied += 1
                print(f"✅ 添加字段: {column_name}")
            else:
                print(f"⚠️  字段已存在: {column_name}")

        conn.commit()
        conn.close()

        if migrations_applied > 0:
            print(f"\n🎉 数据库迁移完成！共应用 {migrations_applied} 个迁移")
        else:
            print("\n📋 数据库已是最新版本，无需迁移")

        return True

    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        print(f"❌ 数据库迁移失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 开始数据库迁移...")

    # 确定数据库路径
    project_root = Path(__file__).resolve().parent.parent
    dev_db_path = project_root / "data" / "emails_dev.db"

    if not dev_db_path.exists():
        print(f"❌ 数据库文件不存在: {dev_db_path}")
        print("请先运行 python create_test_user.py 创建开发数据库")
        return False

    print(f"🗄️  使用数据库: {dev_db_path}")

    # 执行迁移
    success = migrate_users_table(str(dev_db_path))

    if success:
        print("\n✨ 迁移完成！现在可以在Web界面中配置真实邮箱账户了")
    else:
        print("\n💥 迁移失败，请检查错误信息")

    return success


if __name__ == "__main__":
    main()
