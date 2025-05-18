"""
基本认证功能测试 - 简化版测试SMTP和POP3客户端的认证功能
"""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 导入日志模块，避免导入错误
from common.utils import setup_logging

# 设置测试日志
logger = setup_logging("test_auth_basic")

from client.smtp_client import SMTPClient
from client.pop3_client import POP3Client


class TestBasicAuth(unittest.TestCase):
    """基本认证测试类"""

    def test_smtp_client_init(self):
        """测试SMTP客户端初始化"""
        client = SMTPClient(
            host="smtp.example.com",
            port=465,
            use_ssl=True,
            username="user@example.com",
            password="password",
            auth_method="AUTO",
        )

        self.assertEqual(client.host, "smtp.example.com")
        self.assertEqual(client.auth_method, "AUTO")
        self.assertEqual(client.username, "user@example.com")
        self.assertEqual(client.password, "password")

    def test_pop3_client_init(self):
        """测试POP3客户端初始化"""
        client = POP3Client(
            host="pop3.example.com",
            port=995,
            use_ssl=True,
            username="user@example.com",
            password="password",
            auth_method="BASIC",
        )

        self.assertEqual(client.host, "pop3.example.com")
        self.assertEqual(client.auth_method, "BASIC")
        self.assertEqual(client.username, "user@example.com")
        self.assertEqual(client.password, "password")

    def test_auth_plain_string(self):
        """测试AUTH PLAIN字符串生成"""
        client = SMTPClient(
            username="user",
            password="pass",
        )

        auth_string = client._generate_auth_plain_string()
        import base64

        decoded = base64.b64decode(auth_string)

        self.assertEqual(decoded, b"\0user\0pass")


if __name__ == "__main__":
    unittest.main()
