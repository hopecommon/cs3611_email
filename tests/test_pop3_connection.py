import sys
import unittest
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 导入配置
try:
    # 尝试多种导入方式
    try:
        # 方式1：使用完整模块路径
        from tests.test_config import (
            TEST_ACCOUNT,
            TEST_POP3_SERVER,
            TEST_EMAIL,
            TEST_PASSWORD,
        )
    except ImportError:
        try:
            # 方式2：使用相对路径
            from .test_config import (
                TEST_ACCOUNT,
                TEST_POP3_SERVER,
                TEST_EMAIL,
                TEST_PASSWORD,
            )
        except ImportError:
            # 方式3：直接导入（如果当前目录在Python路径中）
            from test_config import (
                TEST_ACCOUNT,
                TEST_POP3_SERVER,
                TEST_EMAIL,
                TEST_PASSWORD,
            )
except ImportError:
    # 方式4：手动导入文件
    import os
    import importlib.util

    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "test_config.py")

    if os.path.exists(config_path):
        try:
            # 如果文件存在，尝试手动导入
            spec = importlib.util.spec_from_file_location("test_config", config_path)
            test_config = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(test_config)

            # 从模块中获取变量
            TEST_ACCOUNT = getattr(test_config, "TEST_ACCOUNT", None)
            TEST_POP3_SERVER = getattr(test_config, "TEST_POP3_SERVER", None)
            TEST_EMAIL = getattr(test_config, "TEST_EMAIL", None)
            TEST_PASSWORD = getattr(test_config, "TEST_PASSWORD", None)

            # 检查是否获取到了所有必要的变量
            if not all([TEST_ACCOUNT, TEST_POP3_SERVER, TEST_EMAIL, TEST_PASSWORD]):
                raise ImportError("配置文件中缺少必要的变量")
        except Exception as e:
            logging.warning(f"导入配置文件失败: {e}")
            raise ImportError(f"导入配置文件失败: {e}")
    else:
        logging.warning(f"配置文件不存在: {config_path}")
        raise ImportError(f"配置文件不存在: {config_path}")
except Exception as e:
    logging.warning(
        f"无法导入测试配置: {e}\n"
        "请确保 test_config.py 文件存在并包含必要的变量。\n"
        "您可以复制 tests/test_config.py.template 为 tests/test_config.py 并填入您的测试账号信息。"
    )
    # 设置默认值，使测试可以加载但会被跳过
    TEST_ACCOUNT = {
        "pop3_host": "pop.example.com",
        "username": "test@example.com",
        "password": "password",
    }
    TEST_POP3_SERVER = TEST_ACCOUNT["pop3_host"]
    TEST_EMAIL = TEST_ACCOUNT["username"]
    TEST_PASSWORD = TEST_ACCOUNT["password"]


class TestPOP3Connection(unittest.TestCase):
    def setUp(self):
        # 检查是否有真实的测试配置
        if TEST_EMAIL == "test@example.com":
            self.skipTest("测试配置不存在或使用了默认值")

    def test_connection(self):
        """测试POP3连接"""
        # 使用配置中的信息
        host = TEST_POP3_SERVER
        username = TEST_EMAIL
        password = TEST_PASSWORD
        use_ssl = TEST_ACCOUNT.get("pop3_ssl", True)
        ssl_port = TEST_ACCOUNT.get("pop3_ssl_port", 995)
        port = ssl_port if use_ssl else TEST_ACCOUNT.get("pop3_port", 995)

        print(f"\n测试POP3连接: {host}:{port} (SSL: {use_ssl})")
        print(f"用户名: {username}")

        # 导入POP3客户端
        from client.pop3_client import POP3Client

        try:
            # 创建POP3客户端
            client = POP3Client(
                host=host,
                port=port,
                use_ssl=use_ssl,
                username=username,
                password=password,
            )

            # 测试连接（connect方法已包含认证）
            print("尝试连接到POP3服务器...")
            client.connect()  # connect方法没有返回值，但会在失败时抛出异常
            print("连接和认证成功！")

            # 获取邮件数量
            print("获取邮件统计信息...")
            msg_count, mailbox_size = client.get_mailbox_status()
            print(f"邮箱统计: {msg_count} 封邮件, 总大小: {mailbox_size/1024:.2f} KB")

            # 获取邮件列表
            print("获取邮件列表...")
            messages = client.list_emails()  # 获取所有邮件
            print(f"获取到 {len(messages)} 封邮件")

            # 如果有邮件，获取第一封邮件
            if messages:
                print("\n获取第一封邮件...")
                msg_num = messages[0][0]  # 第一个元素是邮件索引
                email_obj = client.retrieve_email(msg_num)
                print(f"邮件ID: {email_obj.message_id}")
                print(f"发件人: {email_obj.from_addr.address}")
                print(f"主题: {email_obj.subject}")
                print(f"日期: {email_obj.date}")

            # 关闭连接
            print("\n关闭连接...")
            client.disconnect()
            print("连接已关闭")

            # 测试通过
            print("\n✓ POP3连接测试通过")

        except Exception as e:
            print(f"\n✗ POP3连接测试失败: {e}")
            import traceback

            traceback.print_exc()
            self.fail(f"POP3连接测试失败: {e}")

    def test_fetch_email(self):
        """测试获取邮件内容"""
        # 如果没有真实的测试配置，跳过测试
        if TEST_EMAIL == "test@example.com":
            self.skipTest("测试配置不存在或使用了默认值")

        # 使用配置中的信息
        host = TEST_POP3_SERVER
        username = TEST_EMAIL
        password = TEST_PASSWORD
        use_ssl = TEST_ACCOUNT.get("pop3_ssl", True)
        ssl_port = TEST_ACCOUNT.get("pop3_ssl_port", 995)
        port = ssl_port if use_ssl else TEST_ACCOUNT.get("pop3_port", 995)

        print(f"\n测试获取邮件内容: {host}:{port}")

        # 导入POP3客户端
        from client.pop3_client import POP3Client

        try:
            # 创建POP3客户端
            client = POP3Client(
                host=host,
                port=port,
                use_ssl=use_ssl,
                username=username,
                password=password,
            )

            # 连接（包含认证）
            print("连接到POP3服务器...")
            client.connect()
            print("连接和认证成功")

            # 获取邮件列表
            print("获取邮件列表...")
            messages = client.list_emails()  # 获取所有邮件

            if not messages:
                print("邮箱中没有邮件，跳过测试")
                self.skipTest("邮箱中没有邮件")

            # 获取第一封邮件
            msg_num = messages[0][0]  # 第一个元素是邮件索引
            print(f"获取邮件索引: {msg_num}")

            # 获取邮件内容
            print("获取邮件内容...")
            email_obj = client.retrieve_email(msg_num)

            # 验证邮件对象
            self.assertIsNotNone(email_obj, "无法获取邮件")

            # 打印邮件信息
            print("邮件信息:")
            print(f"发件人: {email_obj.from_addr.address}")
            if email_obj.to_addrs:
                print(
                    f"收件人: {', '.join([addr.address for addr in email_obj.to_addrs])}"
                )
            print(f"主题: {email_obj.subject}")
            print(f"日期: {email_obj.date}")

            # 打印邮件内容摘要
            if email_obj.text_content:
                content_preview = (
                    email_obj.text_content[:100] + "..."
                    if len(email_obj.text_content) > 100
                    else email_obj.text_content
                )
                print(f"内容预览: {content_preview}")

            # 关闭连接
            print("\n关闭连接...")
            client.disconnect()
            print("连接已关闭")

            # 测试通过
            print("\n✓ 获取邮件内容测试通过")

        except Exception as e:
            print(f"\n✗ 获取邮件内容测试失败: {e}")
            import traceback

            traceback.print_exc()
            self.fail(f"获取邮件内容测试失败: {e}")

    def test_advanced_features(self):
        """测试POP3客户端的高级功能"""
        # 如果没有真实的测试配置，跳过测试
        if TEST_EMAIL == "test@example.com":
            self.skipTest("测试配置不存在或使用了默认值")

        # 使用配置中的信息
        host = TEST_POP3_SERVER
        username = TEST_EMAIL
        password = TEST_PASSWORD
        use_ssl = TEST_ACCOUNT.get("pop3_ssl", True)
        ssl_port = TEST_ACCOUNT.get("pop3_ssl_port", 995)
        port = ssl_port if use_ssl else TEST_ACCOUNT.get("pop3_port", 995)

        print(f"\n测试POP3高级功能: {host}:{port}")

        # 导入POP3客户端
        from client.pop3_client import POP3Client
        import tempfile
        import os

        try:
            # 创建POP3客户端
            client = POP3Client(
                host=host,
                port=port,
                use_ssl=use_ssl,
                username=username,
                password=password,
            )

            # 连接（包含认证）
            print("连接到POP3服务器...")
            client.connect()
            print("连接和认证成功")

            # 测试获取邮件统计信息
            print("\n测试获取邮件统计信息...")
            msg_count, mailbox_size = client.get_mailbox_status()
            print(f"邮箱统计: {msg_count} 封邮件, 总大小: {mailbox_size/1024:.2f} KB")
            self.assertIsNotNone(msg_count, "无法获取邮件数量")
            self.assertIsNotNone(mailbox_size, "无法获取邮箱大小")

            # 测试获取邮件列表
            print("\n测试获取邮件列表...")
            email_list = client.list_emails()
            print(f"获取到 {len(email_list)} 封邮件")

            # 如果有邮件，测试获取邮件内容和保存为.eml文件
            messages = client.list_emails()
            if messages:
                msg_num = messages[0][0]  # 第一个元素是邮件索引
                print(f"\n测试获取邮件 {msg_num} 的内容...")

                # 获取邮件
                email_obj = client.retrieve_email(msg_num)
                self.assertIsNotNone(email_obj, "无法获取邮件")

                # 创建临时目录
                temp_dir = tempfile.mkdtemp()
                print(f"创建临时目录: {temp_dir}")

                try:
                    # 保存为.eml文件
                    print("保存邮件为.eml文件...")
                    eml_path = client.save_email_as_eml(email_obj, temp_dir)
                    print(f"邮件已保存为: {eml_path}")

                    # 检查文件是否存在
                    self.assertTrue(os.path.exists(eml_path), "保存的.eml文件不存在")

                    # 检查附件
                    if email_obj.attachments:
                        print(f"邮件包含 {len(email_obj.attachments)} 个附件:")
                        for i, attachment in enumerate(email_obj.attachments):
                            print(
                                f"  {i+1}. {attachment.filename} ({len(attachment.content)/1024:.2f} KB)"
                            )
                    else:
                        print("邮件没有附件")
                finally:
                    # 清理临时目录
                    print(f"清理临时目录: {temp_dir}")
                    for filename in os.listdir(temp_dir):
                        file_path = os.path.join(temp_dir, filename)
                        try:
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                        except Exception as e:
                            print(f"删除文件时出错: {e}")
                    os.rmdir(temp_dir)

            # 测试获取所有邮件
            print("\n测试获取所有邮件...")
            all_emails = client.retrieve_all_emails(limit=5)
            print(f"获取到 {len(all_emails)} 封邮件")

            # 关闭连接
            print("\n关闭连接...")
            client.disconnect()
            print("连接已关闭")

            # 测试通过
            print("\n✓ POP3高级功能测试通过")

        except Exception as e:
            print(f"\n✗ POP3高级功能测试失败: {e}")
            import traceback

            traceback.print_exc()
            self.fail(f"POP3高级功能测试失败: {e}")
