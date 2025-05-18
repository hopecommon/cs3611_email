"""
SMTP客户端测试 - 测试SMTP客户端功能
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import generate_message_id
from common.models import Email, EmailAddress, Attachment, EmailStatus, EmailPriority
from client.smtp_client import SMTPClient
from client.mime_handler import MIMEHandler


class TestSMTPClient(unittest.TestCase):
    """SMTP客户端测试类"""

    def setUp(self):
        """测试前的准备工作"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()

        # 创建测试邮件
        self.test_email = Email(
            message_id=generate_message_id(),
            subject="测试邮件",
            from_addr=EmailAddress(name="发件人", address="sender@example.com"),
            to_addrs=[EmailAddress(name="收件人", address="recipient@example.com")],
            text_content="这是一封测试邮件。",
            date=datetime.now(),
            status=EmailStatus.DRAFT,
            priority=EmailPriority.NORMAL,
        )

    def tearDown(self):
        """测试后的清理工作"""
        # 删除临时目录
        shutil.rmtree(self.temp_dir)

    @patch("smtplib.SMTP")
    def test_connect_without_ssl(self, mock_smtp):
        """测试不使用SSL连接"""
        # 设置模拟对象
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        mock_smtp_instance.has_extn.return_value = False

        # 创建SMTP客户端
        client = SMTPClient(host="localhost", port=25, use_ssl=False)

        # 连接
        client.connect()

        # 验证
        mock_smtp.assert_called_once_with("localhost", 25, timeout=30)
        self.assertFalse(mock_smtp_instance.starttls.called)
        self.assertFalse(mock_smtp_instance.login.called)

    @patch("smtplib.SMTP")
    def test_connect_with_starttls(self, mock_smtp):
        """测试使用STARTTLS连接"""
        # 设置模拟对象
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        mock_smtp_instance.has_extn.return_value = True

        # 创建SMTP客户端
        client = SMTPClient(host="localhost", port=25, use_ssl=False)

        # 连接
        client.connect()

        # 验证
        mock_smtp.assert_called_once_with("localhost", 25, timeout=30)
        mock_smtp_instance.has_extn.assert_called_once_with("STARTTLS")
        mock_smtp_instance.starttls.assert_called_once()
        self.assertFalse(mock_smtp_instance.login.called)

    @patch("smtplib.SMTP_SSL")
    def test_connect_with_ssl(self, mock_smtp_ssl):
        """测试使用SSL连接"""
        # 设置模拟对象
        mock_smtp_instance = MagicMock()
        mock_smtp_ssl.return_value = mock_smtp_instance

        # 创建SMTP客户端
        client = SMTPClient(host="localhost", port=25, use_ssl=True, ssl_port=465)

        # 连接
        client.connect()

        # 验证
        mock_smtp_ssl.assert_called_once()
        self.assertEqual(mock_smtp_ssl.call_args[0][0], "localhost")
        self.assertEqual(mock_smtp_ssl.call_args[0][1], 465)
        self.assertFalse(mock_smtp_instance.login.called)

    @patch("smtplib.SMTP")
    def test_connect_with_auth(self, mock_smtp):
        """测试带认证的连接"""
        # 设置模拟对象
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        mock_smtp_instance.has_extn.return_value = False

        # 创建SMTP客户端
        client = SMTPClient(
            host="localhost", port=25, use_ssl=False, username="user", password="pass"
        )

        # 连接
        client.connect()

        # 验证
        mock_smtp.assert_called_once_with("localhost", 25, timeout=30)
        mock_smtp_instance.login.assert_called_once_with("user", "pass")

    @patch("smtplib.SMTP")
    def test_disconnect(self, mock_smtp):
        """测试断开连接"""
        # 设置模拟对象
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance

        # 创建SMTP客户端
        client = SMTPClient(host="localhost", port=25, use_ssl=False)

        # 连接
        client.connect()

        # 断开连接
        client.disconnect()

        # 验证
        mock_smtp_instance.quit.assert_called_once()
        self.assertIsNone(client.connection)

    @patch("smtplib.SMTP")
    def test_send_email(self, mock_smtp):
        """测试发送邮件"""
        # 设置模拟对象
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance

        # 创建SMTP客户端
        client = SMTPClient(host="localhost", port=25, use_ssl=False)

        # 连接
        client.connect()

        # 发送邮件
        result = client.send_email(self.test_email)

        # 验证
        self.assertTrue(result)
        mock_smtp_instance.send_message.assert_called_once()
        self.assertEqual(self.test_email.status, EmailStatus.SENT)

    def test_create_mime_message(self):
        """测试创建MIME消息"""
        # 创建SMTP客户端
        client = SMTPClient()

        # 创建MIME消息
        msg = client._create_mime_message(self.test_email)

        # 验证
        self.assertEqual(msg["Subject"], self.test_email.subject)
        self.assertEqual(
            MIMEHandler.decode_header_value(msg["From"]),
            f"{self.test_email.from_addr.name} <{self.test_email.from_addr.address}>",
        )
        self.assertEqual(
            MIMEHandler.decode_header_value(msg["To"]),
            f"{self.test_email.to_addrs[0].name} <{self.test_email.to_addrs[0].address}>",
        )
        self.assertIn("Date", msg)
        self.assertIn("Message-ID", msg)

    def test_create_mime_message_with_html(self):
        """测试创建带HTML内容的MIME消息"""
        # 修改测试邮件
        self.test_email.html_content = "<html><body><p>这是HTML内容</p></body></html>"

        # 创建SMTP客户端
        client = SMTPClient()

        # 创建MIME消息
        msg = client._create_mime_message(self.test_email)

        # 验证
        self.assertEqual(msg["Subject"], self.test_email.subject)

        # 检查是否包含alternative部分
        self.assertTrue(msg.is_multipart())
        for part in msg.get_payload():
            if part.get_content_type() == "multipart/alternative":
                alt_part = part
                break
        else:
            self.fail("未找到multipart/alternative部分")

        # 检查alternative部分是否包含text和html
        content_types = [p.get_content_type() for p in alt_part.get_payload()]
        self.assertIn("text/plain", content_types)
        self.assertIn("text/html", content_types)

    def test_create_attachment_part(self):
        """测试创建附件部分"""
        # 创建测试附件
        test_content = b"This is test content."
        attachment = Attachment(
            filename="test.txt", content_type="text/plain", content=test_content
        )

        # 创建SMTP客户端
        client = SMTPClient()

        # 创建附件部分
        part = client._create_attachment_part(attachment)

        # 验证
        self.assertEqual(part.get_content_type(), "text/plain")
        self.assertEqual(part.get_filename(), "test.txt")
        self.assertEqual(
            part.get_payload(decode=True).decode("utf-8"), "This is test content."
        )


if __name__ == "__main__":
    unittest.main()
