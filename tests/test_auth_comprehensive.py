"""
用户认证功能全面测试 - 测试SMTP和POP3客户端的认证功能
"""

import sys
import os
import unittest
from pathlib import Path
import time

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from client.smtp_client import SMTPClient
from client.pop3_client import POP3Client
from tests.test_config import TEST_ACCOUNT

# 设置测试日志
logger = setup_logging("test_auth_comprehensive")


class TestSMTPAuthentication(unittest.TestCase):
    """SMTP认证测试类"""

    def setUp(self):
        """测试前的准备工作"""
        # 设置测试账号信息
        self.host = TEST_ACCOUNT["smtp_host"]
        self.port = TEST_ACCOUNT["smtp_port"]
        self.use_ssl = TEST_ACCOUNT["smtp_ssl"]
        self.username = TEST_ACCOUNT["username"]
        self.password = TEST_ACCOUNT["password"]
        self.wrong_password = "wrong_password"  # 错误的密码，用于测试认证失败

    def tearDown(self):
        """测试后的清理工作"""
        pass

    def test_auto_auth(self):
        """测试自动选择认证方法"""
        client = SMTPClient(
            host=self.host,
            port=self.port,
            use_ssl=self.use_ssl,
            username=self.username,
            password=self.password,
            auth_method="AUTO",
        )

        try:
            client.connect()
            self.assertIsNotNone(client.connection)
            print("AUTO认证成功")
        except Exception as e:
            self.fail(f"AUTO认证失败: {e}")
        finally:
            if client.connection:
                client.disconnect()

    def test_login_auth(self):
        """测试LOGIN认证方法"""
        client = SMTPClient(
            host=self.host,
            port=self.port,
            use_ssl=self.use_ssl,
            username=self.username,
            password=self.password,
            auth_method="LOGIN",
        )

        try:
            client.connect()
            self.assertIsNotNone(client.connection)
            print("LOGIN认证成功")
        except Exception as e:
            self.fail(f"LOGIN认证失败: {e}")
        finally:
            if client.connection:
                client.disconnect()

    def test_plain_auth(self):
        """测试PLAIN认证方法"""
        client = SMTPClient(
            host=self.host,
            port=self.port,
            use_ssl=self.use_ssl,
            username=self.username,
            password=self.password,
            auth_method="PLAIN",
        )

        try:
            client.connect()
            self.assertIsNotNone(client.connection)
            print("PLAIN认证成功")
        except Exception as e:
            self.fail(f"PLAIN认证失败: {e}")
        finally:
            if client.connection:
                client.disconnect()

    def test_auth_failure(self):
        """测试认证失败的情况"""
        client = SMTPClient(
            host=self.host,
            port=self.port,
            use_ssl=self.use_ssl,
            username=self.username,
            password=self.wrong_password,
            auth_method="AUTO",
        )

        try:
            with self.assertRaises(Exception):
                client.connect()
                print("认证失败测试通过")
        finally:
            # 确保连接被关闭，即使测试失败
            if hasattr(client, "connection") and client.connection:
                try:
                    client.disconnect()
                except:
                    # 如果断开连接失败，尝试直接关闭套接字
                    if hasattr(client.connection, "sock") and client.connection.sock:
                        try:
                            client.connection.sock.close()
                        except:
                            pass


class TestPOP3Authentication(unittest.TestCase):
    """POP3认证测试类"""

    def setUp(self):
        """测试前的准备工作"""
        # 设置测试账号信息
        self.host = TEST_ACCOUNT["pop3_host"]
        self.port = TEST_ACCOUNT["pop3_port"]
        self.use_ssl = TEST_ACCOUNT["pop3_ssl"]
        self.username = TEST_ACCOUNT["username"]
        self.password = TEST_ACCOUNT["password"]
        self.wrong_password = "wrong_password"  # 错误的密码，用于测试认证失败

    def tearDown(self):
        """测试后的清理工作"""
        pass

    def test_auto_auth(self):
        """测试自动选择认证方法"""
        client = POP3Client(
            host=self.host,
            port=self.port,
            use_ssl=self.use_ssl,
            username=self.username,
            password=self.password,
            auth_method="AUTO",
        )

        try:
            client.connect()
            self.assertIsNotNone(client.connection)
            print("AUTO认证成功")
        except Exception as e:
            self.fail(f"AUTO认证失败: {e}")
        finally:
            if client.connection:
                client.disconnect()

    def test_basic_auth(self):
        """测试基本认证方法"""
        client = POP3Client(
            host=self.host,
            port=self.port,
            use_ssl=self.use_ssl,
            username=self.username,
            password=self.password,
            auth_method="BASIC",
        )

        try:
            client.connect()
            self.assertIsNotNone(client.connection)
            print("BASIC认证成功")
        except Exception as e:
            self.fail(f"BASIC认证失败: {e}")
        finally:
            if client.connection:
                client.disconnect()

    def test_apop_auth(self):
        """测试APOP认证方法（如果服务器支持）"""
        client = POP3Client(
            host=self.host,
            port=self.port,
            use_ssl=self.use_ssl,
            username=self.username,
            password=self.password,
            auth_method="APOP",
        )

        try:
            client.connect()
            self.assertIsNotNone(client.connection)
            print("APOP认证成功或已降级到基本认证")
        except Exception as e:
            print(f"APOP认证失败，可能是服务器不支持: {e}")
            # 不将此视为测试失败，因为许多服务器不支持APOP
        finally:
            if client.connection:
                client.disconnect()

    def test_auth_failure(self):
        """测试认证失败的情况"""
        client = POP3Client(
            host=self.host,
            port=self.port,
            use_ssl=self.use_ssl,
            username=self.username,
            password=self.wrong_password,
            auth_method="AUTO",
        )

        try:
            with self.assertRaises(Exception):
                client.connect()
                print("认证失败测试通过")
        finally:
            # 确保连接被关闭，即使测试失败
            if hasattr(client, "connection") and client.connection:
                try:
                    client.disconnect()
                except:
                    # 如果断开连接失败，尝试直接关闭套接字
                    if hasattr(client.connection, "sock") and client.connection.sock:
                        try:
                            client.connection.sock.close()
                        except:
                            pass


class TestSSLAuthentication(unittest.TestCase):
    """SSL加密认证测试类"""

    def setUp(self):
        """测试前的准备工作"""
        # 设置测试账号信息
        self.smtp_host = TEST_ACCOUNT["smtp_host"]
        self.pop3_host = TEST_ACCOUNT["pop3_host"]
        self.username = TEST_ACCOUNT["username"]
        self.password = TEST_ACCOUNT["password"]

    def tearDown(self):
        """测试后的清理工作"""
        pass

    def test_smtp_ssl_auth(self):
        """测试SMTP SSL加密认证"""
        client = SMTPClient(
            host=self.smtp_host,
            port=25,
            use_ssl=True,  # 使用SSL加密
            username=self.username,
            password=self.password,
            auth_method="AUTO",
        )

        try:
            client.connect()
            self.assertIsNotNone(client.connection)
            print("SMTP SSL加密认证成功")
        except Exception as e:
            self.fail(f"SMTP SSL加密认证失败: {e}")
        finally:
            if client.connection:
                client.disconnect()

    def test_pop3_ssl_auth(self):
        """测试POP3 SSL加密认证"""
        client = POP3Client(
            host=self.pop3_host,
            port=110,
            use_ssl=True,  # 使用SSL加密
            username=self.username,
            password=self.password,
            auth_method="AUTO",
        )

        try:
            client.connect()
            self.assertIsNotNone(client.connection)
            print("POP3 SSL加密认证成功")
        except Exception as e:
            self.fail(f"POP3 SSL加密认证失败: {e}")
        finally:
            if client.connection:
                client.disconnect()


if __name__ == "__main__":
    unittest.main()
