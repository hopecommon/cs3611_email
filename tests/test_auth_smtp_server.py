"""
测试认证SMTP服务器
"""

import os
import sys
import time
import smtplib
import ssl
import unittest
import threading
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.authenticated_smtp_server import AuthenticatedSMTPServer
from common.utils import setup_logging
from server.user_auth import UserAuth

# 设置日志
logger = setup_logging("test_auth_smtp_server")


class TestAuthenticatedSMTPServer(unittest.TestCase):
    """测试认证SMTP服务器"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        # 使用不常用的端口，避免冲突
        cls.smtp_port = 8045
        cls.smtp_host = "localhost"

        # 确保测试用户存在
        cls.test_username = "testuser"
        cls.test_password = "testpass"
        user_auth = UserAuth()
        user_auth.add_user(cls.test_username, cls.test_password)

        # 创建并启动服务器
        cls.server = AuthenticatedSMTPServer(
            host=cls.smtp_host, 
            port=cls.smtp_port, 
            require_auth=True,
            use_ssl=True
        )
        cls.server.start()

        # 等待服务器启动
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        """清理测试环境"""
        # 停止服务器
        cls.server.stop()

    def test_auth_required(self):
        """测试认证要求"""
        # 创建邮件
        msg = MIMEText("这是一封测试邮件", "plain", "utf-8")
        msg["Subject"] = "测试邮件"
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"

        # 创建SSL上下文
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # 尝试在不认证的情况下发送邮件
        with self.assertRaises(smtplib.SMTPAuthenticationError):
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as client:
                client.set_debuglevel(1)  # 启用调试输出
                client.sendmail("sender@example.com", ["recipient@example.com"], msg.as_string())

    def test_auth_success(self):
        """测试认证成功"""
        # 创建邮件
        msg = MIMEText("这是一封测试邮件", "plain", "utf-8")
        msg["Subject"] = "测试邮件"
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"

        # 创建SSL上下文
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # 尝试在认证的情况下发送邮件
        try:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as client:
                client.set_debuglevel(1)  # 启用调试输出
                client.login(self.test_username, self.test_password)
                client.sendmail("sender@example.com", ["recipient@example.com"], msg.as_string())
            # 如果没有异常，则测试通过
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"认证失败: {e}")

    def test_auth_failure(self):
        """测试认证失败"""
        # 创建SSL上下文
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # 尝试使用错误的密码认证
        with self.assertRaises(smtplib.SMTPAuthenticationError):
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as client:
                client.set_debuglevel(1)  # 启用调试输出
                client.login(self.test_username, "wrongpassword")

    def test_send_multipart_email(self):
        """测试发送多部分邮件"""
        # 创建多部分邮件
        msg = MIMEMultipart()
        msg["Subject"] = "测试多部分邮件"
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"

        # 添加文本部分
        text_part = MIMEText("这是邮件的文本部分", "plain", "utf-8")
        msg.attach(text_part)

        # 添加HTML部分
        html_part = MIMEText("<html><body><h1>这是邮件的HTML部分</h1></body></html>", "html", "utf-8")
        msg.attach(html_part)

        # 创建SSL上下文
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # 尝试在认证的情况下发送邮件
        try:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as client:
                client.set_debuglevel(1)  # 启用调试输出
                client.login(self.test_username, self.test_password)
                client.sendmail("sender@example.com", ["recipient@example.com"], msg.as_string())
            # 如果没有异常，则测试通过
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"发送多部分邮件失败: {e}")


if __name__ == "__main__":
    unittest.main()
