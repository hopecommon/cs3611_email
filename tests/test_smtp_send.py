"""
邮件发送功能测试 - 测试SMTP客户端的邮件发送功能
"""

import sys
import os
import unittest
from pathlib import Path
import tempfile
import shutil

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.models import Email, EmailAddress, Attachment, EmailStatus
from client.smtp_client import SMTPClient
from tests.test_config import TEST_ACCOUNT

# 设置测试日志
logger = setup_logging("test_smtp_send")


class TestSMTPSend(unittest.TestCase):
    """SMTP发送测试类"""

    def setUp(self):
        """测试前的准备工作"""
        # 创建临时目录用于存储测试邮件
        self.test_dir = tempfile.mkdtemp()

        # 创建SMTP客户端
        self.smtp_client = SMTPClient(
            host=TEST_ACCOUNT["smtp_host"],
            port=TEST_ACCOUNT["smtp_port"],
            use_ssl=TEST_ACCOUNT["smtp_ssl"],
            username=TEST_ACCOUNT["username"],
            password=TEST_ACCOUNT["password"],
            auth_method="AUTO",
            save_sent_emails=True,
            sent_emails_dir=self.test_dir,
        )

    def tearDown(self):
        """测试后的清理工作"""
        # 断开SMTP连接
        if self.smtp_client.connection:
            self.smtp_client.disconnect()

        # 删除临时目录
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_send_text_email(self):
        """测试发送纯文本邮件"""
        # 创建测试邮件
        email = Email(
            message_id=f"<test.{id(self)}.text@example.com>",  # 添加唯一的消息ID
            subject="测试纯文本邮件",
            from_addr=EmailAddress(name="发件人", address=TEST_ACCOUNT["username"]),
            to_addrs=[EmailAddress(name="收件人", address=TEST_ACCOUNT["recipient"])],
            text_content="这是一封测试纯文本邮件。\n这是第二行。",
            date=None,  # 自动设置为当前时间
            status=EmailStatus.DRAFT,
        )

        # 发送邮件
        try:
            result = self.smtp_client.send_email(email)
            self.assertTrue(result)
            self.assertEqual(email.status, EmailStatus.SENT)

            # 检查是否保存了已发送邮件
            sent_dir = os.path.join(self.test_dir, "sent")
            files = os.listdir(sent_dir)
            self.assertTrue(len(files) > 0)

            print(f"纯文本邮件发送成功，已保存到: {os.path.join(sent_dir, files[0])}")
        except Exception as e:
            self.fail(f"发送纯文本邮件失败: {e}")

    def test_send_html_email(self):
        """测试发送HTML邮件"""
        # 创建测试邮件
        email = Email(
            message_id=f"<test.{id(self)}.html@example.com>",  # 添加唯一的消息ID
            subject="测试HTML邮件",
            from_addr=EmailAddress(name="发件人", address=TEST_ACCOUNT["username"]),
            to_addrs=[EmailAddress(name="收件人", address=TEST_ACCOUNT["recipient"])],
            text_content="这是一封测试HTML邮件。",
            html_content="<html><body><h1>测试HTML邮件</h1><p>这是一封<b>HTML格式</b>的测试邮件。</p></body></html>",
            date=None,  # 自动设置为当前时间
            status=EmailStatus.DRAFT,
        )

        # 发送邮件
        try:
            result = self.smtp_client.send_email(email)
            self.assertTrue(result)
            self.assertEqual(email.status, EmailStatus.SENT)

            # 检查是否保存了已发送邮件
            sent_dir = os.path.join(self.test_dir, "sent")
            files = os.listdir(sent_dir)
            self.assertTrue(len(files) > 0)

            print(f"HTML邮件发送成功，已保存到: {os.path.join(sent_dir, files[0])}")
        except Exception as e:
            self.fail(f"发送HTML邮件失败: {e}")

    def test_send_email_with_attachments(self):
        """测试发送带附件的邮件"""
        # 创建测试附件
        test_text_file = os.path.join(self.test_dir, "test.txt")
        with open(test_text_file, "w") as f:
            f.write("这是测试文本文件的内容。")

        # 读取附件内容
        with open(test_text_file, "rb") as f:
            attachment_content = f.read()

        # 创建附件对象
        attachment = Attachment(
            filename="test.txt", content_type="text/plain", content=attachment_content
        )

        # 创建测试邮件
        email = Email(
            message_id=f"<test.{id(self)}.attachment@example.com>",  # 添加唯一的消息ID
            subject="测试带附件的邮件",
            from_addr=EmailAddress(name="发件人", address=TEST_ACCOUNT["username"]),
            to_addrs=[EmailAddress(name="收件人", address=TEST_ACCOUNT["recipient"])],
            text_content="这是一封带附件的测试邮件。",
            attachments=[attachment],
            date=None,  # 自动设置为当前时间
            status=EmailStatus.DRAFT,
        )

        # 发送邮件
        try:
            result = self.smtp_client.send_email(email)
            self.assertTrue(result)
            self.assertEqual(email.status, EmailStatus.SENT)

            # 检查是否保存了已发送邮件
            sent_dir = os.path.join(self.test_dir, "sent")
            files = os.listdir(sent_dir)
            self.assertTrue(len(files) > 0)

            print(f"带附件的邮件发送成功，已保存到: {os.path.join(sent_dir, files[0])}")
        except Exception as e:
            self.fail(f"发送带附件的邮件失败: {e}")

    def test_send_email_with_multiple_recipients(self):
        """测试发送到多个收件人（包括抄送和密送）"""
        # 创建测试邮件
        email = Email(
            message_id=f"<test.{id(self)}.multiple@example.com>",  # 添加唯一的消息ID
            subject="测试多收件人邮件",
            from_addr=EmailAddress(name="发件人", address=TEST_ACCOUNT["username"]),
            to_addrs=[
                EmailAddress(name="收件人1", address=TEST_ACCOUNT["recipient"]),
                EmailAddress(name="收件人2", address=TEST_ACCOUNT["recipient"]),
            ],
            cc_addrs=[EmailAddress(name="抄送人", address=TEST_ACCOUNT["recipient"])],
            bcc_addrs=[EmailAddress(name="密送人", address=TEST_ACCOUNT["recipient"])],
            text_content="这是一封发送给多个收件人的测试邮件。",
            date=None,  # 自动设置为当前时间
            status=EmailStatus.DRAFT,
        )

        # 发送邮件
        try:
            result = self.smtp_client.send_email(email)
            self.assertTrue(result)
            self.assertEqual(email.status, EmailStatus.SENT)

            # 检查是否保存了已发送邮件
            sent_dir = os.path.join(self.test_dir, "sent")
            files = os.listdir(sent_dir)
            self.assertTrue(len(files) > 0)

            print(f"多收件人邮件发送成功，已保存到: {os.path.join(sent_dir, files[0])}")
        except Exception as e:
            self.fail(f"发送多收件人邮件失败: {e}")


if __name__ == "__main__":
    unittest.main()
