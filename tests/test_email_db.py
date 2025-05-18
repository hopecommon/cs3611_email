#!/usr/bin/env python
"""
单元测试 - EmailDB 类
"""

import os
import sys
import unittest
import tempfile
import datetime
import sqlite3
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.email_db import EmailDB
from common.models import Email, EmailAddress, Attachment, EmailStatus


class TestEmailDB(unittest.TestCase):
    """EmailDB类的单元测试"""

    def setUp(self):
        """测试前的准备工作"""
        # 创建临时数据库文件
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".sqlite")

        # 创建临时邮件存储目录
        self.temp_dir = tempfile.mkdtemp()

        # 初始化EmailDB实例
        self.db = EmailDB(self.temp_db_path)

        # 创建测试邮件
        self.test_email = Email(
            message_id="<test@example.com>",
            subject="Test Email",
            from_addr=EmailAddress(name="Sender", address="sender@example.com"),
            to_addrs=[EmailAddress(name="Recipient", address="recipient@example.com")],
            text_content="This is a test email.",
            date=datetime.datetime.now(),
            status=EmailStatus.SENT,
        )

        # 创建测试邮件内容文件
        self.content_path = os.path.join(self.temp_dir, "test.eml")
        with open(self.content_path, "w", encoding="utf-8") as f:
            f.write("From: Sender <sender@example.com>\r\n")
            f.write("To: Recipient <recipient@example.com>\r\n")
            f.write("Subject: Test Email\r\n")
            f.write(
                "Date: "
                + datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
                + "\r\n"
            )
            f.write("\r\n")
            f.write("This is a test email.")

    def tearDown(self):
        """测试后的清理工作"""
        # 关闭临时文件
        os.close(self.temp_db_fd)

        # 删除临时文件和目录
        os.unlink(self.temp_db_path)

        # 删除临时邮件内容文件
        if os.path.exists(self.content_path):
            os.unlink(self.content_path)

        # 删除临时目录中的所有文件
        for filename in os.listdir(self.temp_dir):
            file_path = os.path.join(self.temp_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"删除文件时出错: {e}")

        # 删除临时目录
        try:
            os.rmdir(self.temp_dir)
        except OSError as e:
            print(f"删除临时目录时出错: {e}")

    def test_save_and_get_email(self):
        """测试保存和获取邮件"""
        # 保存已发送邮件
        result = self.db.save_sent_email(self.test_email, self.content_path)
        self.assertTrue(result, "保存已发送邮件应该成功")

        # 修改数据库中的content_path字段，使其指向正确的文件路径
        try:
            conn = sqlite3.connect(self.temp_db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE sent_emails SET content_path = ? WHERE message_id = ?
                """,
                (self.content_path, self.test_email.message_id),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            self.fail(f"更新content_path时出错: {e}")

        # 获取邮件元数据
        email = self.db.get_email(self.test_email.message_id)
        self.assertIsNotNone(email, "应该能够获取到邮件")
        self.assertEqual(
            email["message_id"], self.test_email.message_id, "邮件ID应该匹配"
        )
        self.assertEqual(email["subject"], self.test_email.subject, "邮件主题应该匹配")
        self.assertEqual(
            email["from_addr"], self.test_email.from_addr.address, "发件人地址应该匹配"
        )

        # 检查邮件内容
        self.assertIn("content", email, "应该包含邮件内容")
        self.assertIn("This is a test email.", email["content"], "邮件内容应该匹配")

    def test_list_emails(self):
        """测试列出邮件"""
        # 保存已发送邮件
        result = self.db.save_sent_email(self.test_email, self.content_path)
        self.assertTrue(result, "保存已发送邮件应该成功")

        # 列出已发送邮件
        emails = self.db.list_emails(folder="sent")
        self.assertEqual(len(emails), 1, "应该有一封已发送邮件")
        self.assertEqual(
            emails[0]["message_id"], self.test_email.message_id, "邮件ID应该匹配"
        )

        # 列出收件箱邮件（应该为空）
        emails = self.db.list_emails(folder="inbox")
        self.assertEqual(len(emails), 0, "收件箱应该为空")

    def test_mark_as_read_and_unread(self):
        """测试标记邮件为已读和未读"""
        # 创建接收邮件
        received_email = Email(
            message_id="<received@example.com>",
            subject="Received Email",
            from_addr=EmailAddress(name="Sender", address="sender@example.com"),
            to_addrs=[EmailAddress(name="Me", address="me@example.com")],
            text_content="This is a received email.",
            date=datetime.datetime.now(),
            status=EmailStatus.RECEIVED,
        )

        # 保存接收邮件
        received_content_path = os.path.join(self.temp_dir, "received.eml")
        with open(received_content_path, "w", encoding="utf-8") as f:
            f.write("From: Sender <sender@example.com>\r\n")
            f.write("To: Me <me@example.com>\r\n")
            f.write("Subject: Received Email\r\n")
            f.write(
                "Date: "
                + datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
                + "\r\n"
            )
            f.write("\r\n")
            f.write("This is a received email.")

        result = self.db.save_received_email(received_email, received_content_path)
        self.assertTrue(result, "保存接收邮件应该成功")

        # 修改数据库中的content_path字段，使其指向正确的文件路径
        try:
            conn = sqlite3.connect(self.temp_db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE emails SET content_path = ? WHERE message_id = ?
                """,
                (received_content_path, received_email.message_id),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            self.fail(f"更新content_path时出错: {e}")

        # 标记为已读
        result = self.db.mark_as_read(received_email.message_id)
        self.assertTrue(result, "标记为已读应该成功")

        # 获取邮件，检查是否已读
        email = self.db.get_email(received_email.message_id)
        self.assertTrue(email["is_read"], "邮件应该被标记为已读")

        # 标记为未读
        result = self.db.mark_as_unread(received_email.message_id)
        self.assertTrue(result, "标记为未读应该成功")

        # 获取邮件，检查是否未读
        email = self.db.get_email(received_email.message_id)
        self.assertFalse(email["is_read"], "邮件应该被标记为未读")

        # 清理
        if os.path.exists(received_content_path):
            os.unlink(received_content_path)

    def test_mark_as_deleted(self):
        """测试标记邮件为已删除"""
        # 保存接收邮件
        received_email = Email(
            message_id="<deleted@example.com>",
            subject="To Be Deleted",
            from_addr=EmailAddress(name="Sender", address="sender@example.com"),
            to_addrs=[EmailAddress(name="Me", address="me@example.com")],
            text_content="This email will be deleted.",
            date=datetime.datetime.now(),
            status=EmailStatus.RECEIVED,
        )

        # 保存接收邮件
        deleted_content_path = os.path.join(self.temp_dir, "deleted.eml")
        with open(deleted_content_path, "w", encoding="utf-8") as f:
            f.write("From: Sender <sender@example.com>\r\n")
            f.write("To: Me <me@example.com>\r\n")
            f.write("Subject: To Be Deleted\r\n")
            f.write(
                "Date: "
                + datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
                + "\r\n"
            )
            f.write("\r\n")
            f.write("This email will be deleted.")

        result = self.db.save_received_email(received_email, deleted_content_path)
        self.assertTrue(result, "保存接收邮件应该成功")

        # 修改数据库中的content_path字段，使其指向正确的文件路径
        try:
            conn = sqlite3.connect(self.temp_db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE emails SET content_path = ? WHERE message_id = ?
                """,
                (deleted_content_path, received_email.message_id),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            self.fail(f"更新content_path时出错: {e}")

        # 标记为已删除
        result = self.db.mark_as_deleted(received_email.message_id)
        self.assertTrue(result, "标记为已删除应该成功")

        # 获取邮件，检查是否已删除
        email = self.db.get_email(received_email.message_id)
        self.assertTrue(email["is_deleted"], "邮件应该被标记为已删除")

        # 列出邮件（默认不包含已删除邮件）
        emails = self.db.list_emails()
        deleted_emails = [
            e for e in emails if e["message_id"] == received_email.message_id
        ]
        self.assertEqual(len(deleted_emails), 0, "已删除邮件不应该出现在默认列表中")

        # 清理
        if os.path.exists(deleted_content_path):
            os.unlink(deleted_content_path)

    def test_search(self):
        """测试搜索邮件"""
        # 保存多封邮件
        emails = [
            Email(
                message_id=f"<test{i}@example.com>",
                subject=f"Test Email {i}",
                from_addr=EmailAddress(name="Sender", address="sender@example.com"),
                to_addrs=[
                    EmailAddress(name="Recipient", address="recipient@example.com")
                ],
                text_content=f"This is test email {i}.",
                date=datetime.datetime.now(),
                status=EmailStatus.SENT,
            )
            for i in range(5)
        ]

        # 添加一封特殊邮件
        special_email = Email(
            message_id="<special@example.com>",
            subject="Special Subject",
            from_addr=EmailAddress(name="Special", address="special@example.com"),
            to_addrs=[EmailAddress(name="Recipient", address="recipient@example.com")],
            text_content="This is a special email with important content.",
            date=datetime.datetime.now(),
            status=EmailStatus.SENT,
        )
        emails.append(special_email)

        # 保存所有邮件
        for i, email in enumerate(emails):
            content_path = os.path.join(self.temp_dir, f"email{i}.eml")
            with open(content_path, "w", encoding="utf-8") as f:
                # 添加必要的MIME头部信息
                f.write(f"From: {email.from_addr.name} <{email.from_addr.address}>\r\n")
                f.write(
                    f"To: {email.to_addrs[0].name} <{email.to_addrs[0].address}>\r\n"
                )
                f.write(f"Subject: {email.subject}\r\n")
                f.write(
                    "Date: " + email.date.strftime("%a, %d %b %Y %H:%M:%S %z") + "\r\n"
                )
                f.write("MIME-Version: 1.0\r\n")
                f.write("Content-Type: text/plain; charset=utf-8\r\n")
                f.write("Content-Transfer-Encoding: 7bit\r\n")
                f.write("\r\n")
                f.write(email.text_content)

            result = self.db.save_sent_email(email, content_path)
            self.assertTrue(result, f"保存邮件 {i} 应该成功")

            # 修改数据库中的content_path字段，使其指向正确的文件路径
            try:
                conn = sqlite3.connect(self.temp_db_path)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE sent_emails SET content_path = ? WHERE message_id = ?
                    """,
                    (content_path, email.message_id),
                )
                conn.commit()
                conn.close()
            except Exception as e:
                self.fail(f"更新content_path时出错: {e}")

        # 搜索主题
        results = self.db.search("Special", search_in=["subject"])
        self.assertEqual(len(results), 1, "应该找到一封主题包含'Special'的邮件")
        self.assertEqual(
            results[0]["message_id"], special_email.message_id, "找到的邮件ID应该匹配"
        )

        # 搜索发件人
        results = self.db.search("special@example.com", search_in=["from_addr"])
        self.assertEqual(
            len(results), 1, "应该找到一封发件人为'special@example.com'的邮件"
        )

        # 搜索内容
        print("\n测试搜索邮件内容...")

        # 先检查特殊邮件的内容是否正确
        special_email_data = self.db.get_email("<special@example.com>")
        if special_email_data:
            print(f"特殊邮件内容: {special_email_data.get('content', '无内容')}")
        else:
            print("无法获取特殊邮件")

        # 搜索内容
        results = self.db.search("important", search_content=True)
        print(f"搜索结果数量: {len(results)}")
        if results:
            for i, result in enumerate(results):
                print(
                    f"结果 {i+1}: {result.get('message_id')} - {result.get('subject')}"
                )

        self.assertEqual(len(results), 1, "应该找到一封内容包含'important'的邮件")

        # 清理
        for i in range(len(emails)):
            content_path = os.path.join(self.temp_dir, f"email{i}.eml")
            if os.path.exists(content_path):
                os.unlink(content_path)


if __name__ == "__main__":
    unittest.main()
