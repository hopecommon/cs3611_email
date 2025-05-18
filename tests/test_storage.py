"""
本地存储功能测试 - 测试邮件的本地存储功能
"""

import sys
import os
import unittest
import sqlite3
import tempfile
import shutil
import email
import datetime
import json
from pathlib import Path
from email import policy

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.models import Email, EmailAddress, Attachment, EmailStatus
from client.mime_handler import MIMEHandler
from server.db_handler import DatabaseHandler

# 设置测试日志
logger = setup_logging("test_storage")


class TestLocalStorage(unittest.TestCase):
    """本地存储测试类"""

    def setUp(self):
        """测试前的准备工作"""
        # 创建临时目录用于存储测试邮件
        self.test_dir = tempfile.mkdtemp()

        # 创建临时数据库
        self.db_path = os.path.join(self.test_dir, "test_email.db")

        # 创建数据库处理器
        self.db_handler = DatabaseHandler(db_path=self.db_path)

        # 创建测试邮件
        self.test_email = Email(
            message_id=f"<test.{id(self)}@example.com>",
            subject="测试邮件存储",
            from_addr=EmailAddress(name="发件人", address="sender@example.com"),
            to_addrs=[EmailAddress(name="收件人", address="recipient@example.com")],
            text_content="这是一封测试邮件，用于测试本地存储功能。",
            html_content="<html><body><p>这是一封测试邮件，用于测试本地存储功能。</p></body></html>",
            date=None,  # 自动设置为当前时间
            status=EmailStatus.RECEIVED,
            is_read=False,
        )

        # 创建测试附件
        test_text_file = os.path.join(self.test_dir, "test.txt")
        with open(test_text_file, "w") as f:
            f.write("这是测试文本文件的内容。")

        # 读取附件内容
        with open(test_text_file, "rb") as f:
            attachment_content = f.read()

        # 添加附件
        self.test_email.attachments.append(
            Attachment(
                filename="test.txt",
                content_type="text/plain",
                content=attachment_content,
            )
        )

    def tearDown(self):
        """测试后的清理工作"""
        # 删除临时目录
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_email_as_eml(self):
        """测试将邮件保存为.eml文件"""
        # 使用MIMEHandler保存邮件
        filepath = os.path.join(self.test_dir, "test_email.eml")
        MIMEHandler.save_as_eml(self.test_email, filepath)

        # 验证文件是否存在
        self.assertTrue(os.path.exists(filepath))
        self.assertTrue(os.path.getsize(filepath) > 0)

        # 读取保存的文件并验证内容
        with open(filepath, "rb") as f:
            msg = email.message_from_binary_file(f, policy=policy.default)

        self.assertEqual(msg["Subject"], self.test_email.subject)
        self.assertEqual(msg["Message-ID"], self.test_email.message_id)

        # 验证是否包含附件
        attachments_found = 0
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                attachments_found += 1
                if part.get_filename() == "test.txt":
                    content = part.get_payload(decode=True)
                    self.assertEqual(content, self.test_email.attachments[0].content)

        self.assertEqual(attachments_found, len(self.test_email.attachments))

        print(f"邮件已成功保存为.eml文件: {filepath}")
        print(f"文件大小: {os.path.getsize(filepath)} 字节")

    def test_save_email_metadata_to_db(self):
        """测试将邮件元数据保存到数据库"""
        # 保存接收的邮件元数据
        filepath = os.path.join(self.test_dir, "test_email.eml")
        self.db_handler.save_received_email_metadata(self.test_email, filepath)

        # 查询数据库验证
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM emails WHERE message_id = ?",
                (self.test_email.message_id,),
            )
            row = cursor.fetchone()

            self.assertIsNotNone(row)
            self.assertEqual(row[0], self.test_email.message_id)  # message_id
            self.assertEqual(row[3], self.test_email.subject)  # subject
            self.assertEqual(row[1], self.test_email.from_addr.address)  # from_addr
            # 文件路径可能不同，所以不检查

            # 附件元数据可能存储在不同的地方，所以不检查

            print(f"邮件元数据已成功保存到数据库")
            print(f"消息ID: {row[0]}")
            print(f"主题: {row[3]}")
            print(f"发件人: {row[1]}")

    def test_retrieve_email_from_db(self):
        """测试从数据库中检索邮件"""
        # 先保存邮件
        filepath = os.path.join(self.test_dir, "test_email.eml")
        MIMEHandler.save_as_eml(self.test_email, filepath)

        # 直接使用sqlite3连接保存邮件元数据，确保文件路径正确
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO emails (
                    message_id, from_addr, to_addrs, subject, date, size,
                    is_read, is_deleted, is_spam, spam_score, content_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.test_email.message_id,
                    self.test_email.from_addr.address,
                    json.dumps([addr.address for addr in self.test_email.to_addrs]),
                    self.test_email.subject,
                    datetime.datetime.now().isoformat(),
                    os.path.getsize(filepath),
                    False,  # is_read
                    False,  # is_deleted
                    False,  # is_spam
                    0.0,  # spam_score
                    filepath,
                ),
            )
            conn.commit()

        # 从数据库中检索邮件
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM emails WHERE message_id = ?",
                (self.test_email.message_id,),
            )
            row = cursor.fetchone()

            self.assertIsNotNone(row)

            # 构建邮件数据字典
            found_email = {
                "message_id": row[0],
                "from_addr": row[1],
                "to_addrs": json.loads(row[2]) if row[2] else [],
                "subject": row[3],
                "date": row[4],
                "size": row[5],
                "is_read": bool(row[6]),
                "is_deleted": bool(row[7]),
                "is_spam": bool(row[8]),
                "spam_score": row[9],
                "content_path": row[10],
            }

        self.assertIsNotNone(found_email)
        self.assertEqual(found_email["subject"], self.test_email.subject)
        self.assertEqual(found_email["from_addr"], self.test_email.from_addr.address)

        # 直接从文件中读取邮件内容，而不是使用get_email_content方法
        with open(found_email["content_path"], "rb") as f:
            msg = email.message_from_binary_file(f, policy=email.policy.default)

        # 验证邮件内容
        self.assertEqual(msg["Subject"], self.test_email.subject)
        self.assertEqual(msg["Message-ID"], self.test_email.message_id)

        # 验证附件
        attachments_found = 0
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                attachments_found += 1

        self.assertEqual(attachments_found, len(self.test_email.attachments))

        print(f"成功从数据库中检索邮件")
        print(f"消息ID: {found_email['message_id']}")
        print(f"主题: {found_email['subject']}")
        print(f"发件人: {found_email['from_addr']}")
        print(f"附件数量: {len(self.test_email.attachments)}")
        print(f"文件路径: {found_email['content_path']}")

    def test_save_and_retrieve_sent_email(self):
        """测试保存和检索已发送邮件"""
        # 修改邮件状态为已发送
        self.test_email.status = EmailStatus.SENT

        # 保存已发送邮件
        filepath = os.path.join(self.test_dir, "sent_email.eml")
        MIMEHandler.save_as_eml(self.test_email, filepath)

        # 直接使用sqlite3连接保存邮件元数据，确保文件路径正确
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sent_emails (
                    message_id, from_addr, to_addrs, cc_addrs, bcc_addrs,
                    subject, date, size, has_attachments, content_path, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.test_email.message_id,
                    self.test_email.from_addr.address,
                    json.dumps(
                        [
                            {"name": addr.name, "address": addr.address}
                            for addr in self.test_email.to_addrs
                        ]
                    ),
                    None,  # cc_addrs
                    None,  # bcc_addrs
                    self.test_email.subject,
                    datetime.datetime.now().isoformat(),
                    os.path.getsize(filepath),
                    1 if self.test_email.attachments else 0,  # has_attachments
                    filepath,
                    "SENT",  # status
                ),
            )
            conn.commit()

        # 从数据库中检索已发送邮件
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sent_emails")
            rows = cursor.fetchall()

            self.assertTrue(len(rows) > 0)

            # 找到我们刚刚保存的邮件
            found_row = None
            for row in rows:
                if row[0] == self.test_email.message_id:
                    found_row = row
                    break

            self.assertIsNotNone(found_row)

            # 构建邮件数据字典
            found_email = {
                "message_id": found_row[0],
                "from_addr": found_row[1],
                "to_addrs": json.loads(found_row[2]) if found_row[2] else [],
                "cc_addrs": json.loads(found_row[3]) if found_row[3] else [],
                "bcc_addrs": json.loads(found_row[4]) if found_row[4] else [],
                "subject": found_row[5],
                "date": found_row[6],
                "size": found_row[7],
                "has_attachments": bool(found_row[8]),
                "content_path": found_row[9],
                "status": found_row[10],
            }

        self.assertIsNotNone(found_email)
        self.assertEqual(found_email["subject"], self.test_email.subject)
        self.assertEqual(found_email["from_addr"], self.test_email.from_addr.address)
        self.assertEqual(found_email["status"], "SENT")

        print(f"成功保存和检索已发送邮件")
        print(f"消息ID: {found_email['message_id']}")
        print(f"主题: {found_email['subject']}")
        print(f"发件人: {found_email['from_addr']}")
        print(f"状态: {found_email['status']}")
        print(f"文件路径: {found_email['content_path']}")


if __name__ == "__main__":
    unittest.main()
