"""
邮件接收功能测试 - 测试POP3客户端的邮件接收功能
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
from client.pop3_client import POP3Client
from tests.test_config import TEST_ACCOUNT

# 设置测试日志
logger = setup_logging("test_pop3_receive")


class TestPOP3Receive(unittest.TestCase):
    """POP3接收测试类"""

    def setUp(self):
        """测试前的准备工作"""
        # 创建临时目录用于存储测试邮件
        self.test_dir = tempfile.mkdtemp()

        # 创建POP3客户端
        self.pop3_client = POP3Client(
            host=TEST_ACCOUNT["pop3_host"],
            port=TEST_ACCOUNT["pop3_port"],
            use_ssl=TEST_ACCOUNT["pop3_ssl"],
            username=TEST_ACCOUNT["username"],
            password=TEST_ACCOUNT["password"],
            auth_method="AUTO",
        )

    def tearDown(self):
        """测试后的清理工作"""
        # 断开POP3连接
        if self.pop3_client.connection:
            self.pop3_client.disconnect()

        # 删除临时目录
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_connect_to_mailbox(self):
        """测试连接到邮箱"""
        try:
            self.pop3_client.connect()
            self.assertIsNotNone(self.pop3_client.connection)
            print("成功连接到邮箱")
        except Exception as e:
            self.fail(f"连接到邮箱失败: {e}")

    def test_get_mailbox_status(self):
        """测试获取邮箱状态"""
        try:
            self.pop3_client.connect()
            status = self.pop3_client.get_mailbox_status()
            self.assertIsInstance(status, tuple)
            self.assertEqual(len(status), 2)
            print(f"邮箱状态: {status[0]}封邮件, {status[1]}字节")
        except Exception as e:
            self.fail(f"获取邮箱状态失败: {e}")

    def test_list_emails(self):
        """测试列出邮件"""
        try:
            self.pop3_client.connect()
            email_list = self.pop3_client.list_emails()
            self.assertIsInstance(email_list, list)
            print(f"邮箱中有{len(email_list)}封邮件")

            # 打印前5封邮件的信息
            for i, (msg_num, msg_size) in enumerate(email_list[:5]):
                print(f"邮件 {msg_num}: {msg_size} 字节")
                if i >= 4:
                    break
        except Exception as e:
            self.fail(f"列出邮件失败: {e}")

    def test_retrieve_email(self):
        """测试获取单封邮件"""
        try:
            self.pop3_client.connect()
            email_list = self.pop3_client.list_emails()

            if not email_list:
                self.skipTest("邮箱中没有邮件，跳过测试")

            # 获取最新的邮件（通常是列表中的最后一个）
            msg_num = email_list[-1][0]
            email = self.pop3_client.retrieve_email(msg_num, delete=False)

            self.assertIsNotNone(email)
            self.assertIsInstance(email, Email)

            print(f"成功获取邮件 {msg_num}")
            print(f"主题: {email.subject}")
            print(f"发件人: {email.from_addr.name} <{email.from_addr.address}>")
            print(f"日期: {email.date}")
            print(f"附件数量: {len(email.attachments)}")
        except Exception as e:
            self.fail(f"获取邮件失败: {e}")

    def test_retrieve_email_with_attachments(self):
        """测试获取带附件的邮件"""
        try:
            self.pop3_client.connect()
            email_list = self.pop3_client.list_emails()

            if not email_list:
                self.skipTest("邮箱中没有邮件，跳过测试")

            # 尝试找到带附件的邮件
            found_email_with_attachment = False

            # 从最新的邮件开始检查
            for msg_num, _ in reversed(email_list):
                email = self.pop3_client.retrieve_email(msg_num, delete=False)

                if email and email.attachments:
                    found_email_with_attachment = True
                    print(f"找到带附件的邮件 {msg_num}")
                    print(f"主题: {email.subject}")
                    print(f"发件人: {email.from_addr.name} <{email.from_addr.address}>")
                    print(f"日期: {email.date}")
                    print(f"附件数量: {len(email.attachments)}")

                    # 打印附件信息
                    for i, attachment in enumerate(email.attachments):
                        print(
                            f"附件 {i+1}: {attachment.filename} ({attachment.content_type}), {len(attachment.content)} 字节"
                        )

                    break

            if not found_email_with_attachment:
                print("未找到带附件的邮件，请先发送一封带附件的测试邮件")
        except Exception as e:
            self.fail(f"获取带附件的邮件失败: {e}")

    def test_save_email_as_eml(self):
        """测试将邮件保存为.eml文件"""
        try:
            self.pop3_client.connect()
            email_list = self.pop3_client.list_emails()

            if not email_list:
                self.skipTest("邮箱中没有邮件，跳过测试")

            # 获取最新的邮件
            msg_num = email_list[-1][0]
            email = self.pop3_client.retrieve_email(msg_num, delete=False)

            # 保存为.eml文件
            filepath = self.pop3_client.save_email_as_eml(email, self.test_dir)

            self.assertTrue(os.path.exists(filepath))
            self.assertTrue(os.path.getsize(filepath) > 0)

            print(f"邮件已保存为: {filepath}")
            print(f"文件大小: {os.path.getsize(filepath)} 字节")
        except Exception as e:
            self.fail(f"保存邮件失败: {e}")

    def test_retrieve_all_emails(self):
        """测试获取所有邮件（带过滤条件）"""
        try:
            self.pop3_client.connect()

            # 获取最近5封邮件
            emails = self.pop3_client.retrieve_all_emails(delete=False, limit=5)

            self.assertIsInstance(emails, list)
            print(f"成功获取了 {len(emails)} 封邮件")

            # 打印邮件信息
            for i, email in enumerate(emails):
                print(f"邮件 {i+1}:")
                print(f"  主题: {email.subject}")
                print(f"  发件人: {email.from_addr.name} <{email.from_addr.address}>")
                print(f"  日期: {email.date}")
                print(f"  附件数量: {len(email.attachments)}")
        except Exception as e:
            self.fail(f"获取所有邮件失败: {e}")


if __name__ == "__main__":
    unittest.main()
