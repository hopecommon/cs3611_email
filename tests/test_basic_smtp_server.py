"""
测试基础SMTP服务器
"""

import os
import sys
import time
import smtplib
import unittest
import threading
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.basic_smtp_server import BasicSMTPServer
from common.utils import setup_logging

# 设置日志
logger = setup_logging("test_basic_smtp_server")


class TestBasicSMTPServer(unittest.TestCase):
    """测试基础SMTP服务器"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        # 使用不常用的端口，避免冲突
        cls.smtp_port = 8035
        cls.smtp_host = "localhost"

        # 创建并启动服务器
        cls.server = BasicSMTPServer(
            host=cls.smtp_host, port=cls.smtp_port, require_auth=False
        )
        cls.server.start()

        # 等待服务器启动
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        """清理测试环境"""
        # 停止服务器
        cls.server.stop()

    def test_send_simple_email(self):
        """测试发送简单邮件"""
        # 创建邮件
        msg = MIMEText("这是一封测试邮件", "plain", "utf-8")
        msg["Subject"] = "测试邮件"
        msg["From"] = "sender@example.com"
        msg["To"] = "recipient@example.com"

        # 发送邮件
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as client:
            client.set_debuglevel(1)  # 启用调试输出
            client.sendmail(
                "sender@example.com", ["recipient@example.com"], msg.as_string()
            )

        # 如果没有异常，则测试通过
        self.assertTrue(True)

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
        html_part = MIMEText(
            "<html><body><h1>这是邮件的HTML部分</h1></body></html>", "html", "utf-8"
        )
        msg.attach(html_part)

        # 发送邮件
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as client:
            client.set_debuglevel(1)  # 启用调试输出
            client.sendmail(
                "sender@example.com", ["recipient@example.com"], msg.as_string()
            )

        # 如果没有异常，则测试通过
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
