#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版并发邮件测试
基于POP3多客户端连接，添加SMTP发送功能
"""

import os
import sys
import time
import threading
import concurrent.futures
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from server.pop3_server import StablePOP3Server
from server.smtp_server import StableSMTPServer
from server.user_auth import UserAuth
from server.new_db_handler import EmailService
from client.smtp_client import SMTPClient
from client.pop3_client_refactored import POP3Client
from common.models import Email, EmailAddress, EmailStatus
from common.utils import setup_logging

# 设置日志
logger = setup_logging("simple_concurrency_test")


class SimpleConcurrencyTester:
    """简化版并发测试类"""

    def __init__(self):
        self.smtp_server = None
        self.pop3_server = None
        self.email_service = EmailService()
        self.user_auth = UserAuth()
        self.test_users = []
        self.test_results = {}

    def start_servers(self, smtp_port=2526, pop3_port=8111):
        """启动服务器（使用不同端口避免权限问题）"""
        print(f"🚀 启动测试服务器...")

        try:
            # 启动SMTP服务器
            print(f"📤 启动SMTP服务器 (localhost:{smtp_port})")
            self.smtp_server = StableSMTPServer(
                host="localhost",
                port=smtp_port,
                use_ssl=False,
                require_auth=True,
                db_handler=self.email_service,
            )

            smtp_thread = threading.Thread(target=self.smtp_server.start, daemon=True)
            smtp_thread.start()

            # 等待SMTP服务器启动
            for i in range(10):
                try:
                    import socket

                    sock = socket.socket()
                    sock.settimeout(1)
                    result = sock.connect_ex(("localhost", smtp_port))
                    sock.close()
                    if result == 0:
                        print("✅ SMTP服务器已启动")
                        break
                except:
                    pass
                time.sleep(1)
                print(f"   等待SMTP启动... ({i+1}/10)")
            else:
                print("❌ SMTP服务器启动失败")
                return False

            # 启动POP3服务器
            print(f"📥 启动POP3服务器 (localhost:{pop3_port})")
            self.pop3_server = StablePOP3Server(
                host="localhost", port=pop3_port, use_ssl=False
            )

            pop3_thread = threading.Thread(target=self.pop3_server.start, daemon=True)
            pop3_thread.start()

            # 等待POP3服务器启动
            for i in range(10):
                try:
                    import socket

                    sock = socket.socket()
                    sock.settimeout(1)
                    result = sock.connect_ex(("localhost", pop3_port))
                    sock.close()
                    if result == 0:
                        print("✅ POP3服务器已启动")
                        break
                except:
                    pass
                time.sleep(1)
                print(f"   等待POP3启动... ({i+1}/10)")
            else:
                print("❌ POP3服务器启动失败")
                return False

            print("✅ 所有服务器启动成功！")
            return True

        except Exception as e:
            print(f"❌ 启动服务器失败: {e}")
            return False

    def create_test_users(self, count=50):
        """创建测试用户"""
        print(f"👥 创建 {count} 个测试用户...")

        self.test_users = []
        for i in range(1, count + 1):
            user_id = f"testuser{i:03d}"
            email = f"testuser{i:03d}@localhost"
            password = f"testpass{i:03d}"

            try:
                if self.user_auth.add_user(user_id, password, email):
                    self.test_users.append(
                        {
                            "number": i,
                            "user_id": user_id,
                            "email": email,
                            "password": password,
                            "display_name": f"测试用户{i:03d}",
                        }
                    )

                    if i % 10 == 0:
                        print(f"  已创建: {i}/{count}")

            except Exception as e:
                print(f"  创建用户{i}失败: {e}")

        print(f"✅ 成功创建 {len(self.test_users)} 个用户")
        return len(self.test_users) > 0

    def send_test_email(self, user_info, smtp_port=2526):
        """单个用户发送测试邮件"""
        user_num = user_info["number"]

        try:
            # 创建SMTP客户端
            smtp_client = SMTPClient(
                host="localhost",
                port=smtp_port,
                use_ssl=False,
                username=user_info["email"],
                password=user_info["password"],
                auth_method="LOGIN",
            )

            # 生成测试邮件内容
            subject = f"测试邮件#{user_num:03d}"
            content = f"""这是用户{user_num:03d}发送的测试邮件

用户编号: {user_num:03d}
用户ID: {user_info['user_id']} 
邮箱: {user_info['email']}
发送时间: {datetime.now()}

测试目的: 验证并发发送时邮件内容不会错乱
"""

            # 创建邮件对象
            email = Email(
                message_id=f"<test{user_num:03d}@localhost>",
                subject=subject,
                from_addr=EmailAddress(
                    name=user_info["display_name"], address=user_info["email"]
                ),
                to_addrs=[
                    EmailAddress(
                        name=user_info["display_name"], address=user_info["email"]
                    )
                ],
                text_content=content,
                date=None,
                status=EmailStatus.DRAFT,
            )

            # 发送邮件
            result = smtp_client.send_email(email)

            return {
                "user_number": user_num,
                "success": result,
                "subject": subject,
                "content": content,
                "error": None if result else "发送失败",
            }

        except Exception as e:
            return {
                "user_number": user_num,
                "success": False,
                "subject": None,
                "content": None,
                "error": str(e),
            }

    def receive_test_email(self, user_info, pop3_port=8111):
        """单个用户接收测试邮件"""
        user_num = user_info["number"]

        try:
            # 创建POP3客户端
            pop3_client = POP3Client(
                host="localhost",
                port=pop3_port,
                use_ssl=False,
                username=user_info["email"],
                password=user_info["password"],
            )

            # 连接POP3服务器
            if not pop3_client.connect():
                return {
                    "user_number": user_num,
                    "success": False,
                    "error": "POP3连接失败",
                }

            # 获取邮件列表
            emails = pop3_client.list_emails()

            # 查找自己的邮件
            found_email = None
            for email_info in emails:
                try:
                    email_content = pop3_client.get_email(email_info["index"])
                    if (
                        email_content
                        and f"测试邮件#{user_num:03d}"
                        in email_content.get("subject", "")
                    ):
                        found_email = email_content
                        break
                except:
                    continue

            pop3_client.disconnect()

            if found_email:
                return {
                    "user_number": user_num,
                    "success": True,
                    "subject": found_email.get("subject", ""),
                    "content": found_email.get("content", ""),
                    "error": None,
                }
            else:
                return {
                    "user_number": user_num,
                    "success": False,
                    "subject": None,
                    "content": None,
                    "error": f"未找到邮件#{user_num:03d}",
                }

        except Exception as e:
            return {
                "user_number": user_num,
                "success": False,
                "subject": None,
                "content": None,
                "error": str(e),
            }

    def save_test_results(self, send_results, receive_results):
        """保存测试结果到测试目录"""
        test_dir = Path("test_output")
        test_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存发送结果
        send_file = test_dir / f"send_results_{timestamp}.json"
        with open(send_file, "w", encoding="utf-8") as f:
            json.dump(send_results, f, ensure_ascii=False, indent=2)

        # 保存接收结果
        receive_file = test_dir / f"receive_results_{timestamp}.json"
        with open(receive_file, "w", encoding="utf-8") as f:
            json.dump(receive_results, f, ensure_ascii=False, indent=2)

        # 保存邮件内容到单独文件，便于查看
        for result in receive_results:
            if result["success"] and result["content"]:
                user_num = result["user_number"]
                email_file = test_dir / f"email_{user_num:03d}_{timestamp}.txt"
                with open(email_file, "w", encoding="utf-8") as f:
                    f.write(f"用户编号: {user_num:03d}\n")
                    f.write(f"主题: {result['subject']}\n")
                    f.write(f"内容:\n{result['content']}\n")

        print(f"📁 测试结果已保存到: {test_dir}")
        return test_dir

    def verify_results(self, send_results, receive_results):
        """验证用户数字和内容匹配"""
        print(f"\n=== 验证结果 ===")

        successful_sends = [r for r in send_results if r["success"]]
        successful_receives = [r for r in receive_results if r["success"]]

        print(f"发送成功: {len(successful_sends)}/50")
        print(f"接收成功: {len(successful_receives)}/50")

        # 检查内容匹配
        matched = 0
        mismatched = []

        for send_result in successful_sends:
            user_num = send_result["user_number"]

            # 找到对应的接收结果
            receive_result = next(
                (r for r in successful_receives if r["user_number"] == user_num), None
            )

            if receive_result:
                # 检查主题是否匹配
                expected_subject = f"测试邮件#{user_num:03d}"
                actual_subject = receive_result["subject"]

                # 检查内容中是否包含正确的用户编号
                expected_number = f"用户编号: {user_num:03d}"
                actual_content = receive_result["content"]

                if (
                    expected_subject == actual_subject
                    and expected_number in actual_content
                ):
                    matched += 1
                else:
                    mismatched.append(
                        {
                            "user_number": user_num,
                            "expected_subject": expected_subject,
                            "actual_subject": actual_subject,
                            "content_match": expected_number in actual_content,
                        }
                    )

        print(f"内容匹配: {matched}/{len(successful_sends)}")

        if mismatched:
            print(f"❌ 发现 {len(mismatched)} 个不匹配:")
            for item in mismatched[:3]:  # 只显示前3个
                print(f"  用户{item['user_number']:03d}: 主题或内容不匹配")

        success_rate = matched / max(len(successful_sends), 1) * 100
        print(f"匹配率: {success_rate:.1f}%")

        return success_rate >= 95

    def run_test(self, num_users=50):
        """运行完整测试"""
        print("简化版并发邮件测试")
        print("=" * 50)
        print(f"测试 {num_users} 个用户并发发送带编号邮件")
        print("=" * 50)

        try:
            # 1. 启动服务器
            if not self.start_servers():
                return False

            # 2. 创建用户
            if not self.create_test_users(num_users):
                return False

            # 3. 并发发送邮件
            print(f"\n📤 并发发送测试...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                send_futures = [
                    executor.submit(self.send_test_email, user)
                    for user in self.test_users[:num_users]
                ]
                send_results = [
                    f.result()
                    for f in concurrent.futures.as_completed(send_futures, timeout=60)
                ]

            # 4. 等待邮件投递
            print("⏱️  等待邮件投递...")
            time.sleep(3)

            # 5. 并发接收邮件
            print(f"\n📥 并发接收测试...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                receive_futures = [
                    executor.submit(self.receive_test_email, user)
                    for user in self.test_users[:num_users]
                ]
                receive_results = [
                    f.result()
                    for f in concurrent.futures.as_completed(
                        receive_futures, timeout=60
                    )
                ]

            # 6. 保存结果
            self.save_test_results(send_results, receive_results)

            # 7. 验证结果
            success = self.verify_results(send_results, receive_results)

            if success:
                print(f"\n🎉 测试通过！邮件内容匹配正确")
            else:
                print(f"\n❌ 测试失败！发现内容不匹配")

            return success

        except Exception as e:
            print(f"测试失败: {e}")
            return False

        finally:
            # 清理
            print("\n🧹 清理服务器...")
            try:
                if self.smtp_server:
                    self.smtp_server.stop()
                if self.pop3_server:
                    self.pop3_server.stop()
            except:
                pass


def main():
    """主函数"""
    try:
        tester = SimpleConcurrencyTester()

        num_users = int(input("测试用户数 (默认50): ") or "50")

        if tester.run_test(num_users):
            print(f"\n✅ 并发测试成功！")
            print("📁 查看 test_output 目录了解详细结果")
            return 0
        else:
            print(f"\n❌ 并发测试失败！")
            return 1

    except KeyboardInterrupt:
        print("\n测试被中断")
        return 1
    except Exception as e:
        print(f"\n测试启动失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
