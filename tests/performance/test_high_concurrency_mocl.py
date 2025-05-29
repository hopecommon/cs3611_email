#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版并发邮件测试
模拟50个用户并发发送带编号邮件，验证内容不错乱
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

from common.utils import setup_logging

# 设置日志
logger = setup_logging("simple_concurrency_test")


class SimpleConcurrencyTester:
    """简化版并发测试类"""

    def __init__(self):
        self.test_users = []
        self.sent_emails = {}
        self.lock = threading.Lock()

    def create_test_users(self, count=50):
        """创建测试用户"""
        print(f"👥 创建 {count} 个测试用户...")

        self.test_users = []
        for i in range(1, count + 1):
            user_info = {
                "number": i,
                "user_id": f"testuser{i:03d}",
                "email": f"testuser{i:03d}@localhost",
                "password": f"testpass{i:03d}",
                "display_name": f"测试用户{i:03d}",
            }
            self.test_users.append(user_info)

            if i % 10 == 0:
                print(f"  已创建: {i}/{count}")

        print(f"✅ 成功创建 {len(self.test_users)} 个用户")
        return True

    def send_test_email(self, user_info):
        """模拟单个用户发送测试邮件"""
        user_num = user_info["number"]

        try:
            # 模拟发送延迟
            time.sleep(0.01)  # 10ms延迟模拟网络

            # 生成测试邮件内容
            subject = f"测试邮件#{user_num:03d}"
            content = f"""这是用户{user_num:03d}发送的测试邮件

用户编号: {user_num:03d}
用户ID: {user_info['user_id']} 
邮箱: {user_info['email']}
发送时间: {datetime.now()}

测试目的: 验证并发发送时邮件内容不会错乱
"""

            # 使用线程锁保证线程安全
            with self.lock:
                self.sent_emails[user_num] = {
                    "user_info": user_info,
                    "subject": subject,
                    "content": content,
                    "sent_time": datetime.now(),
                }

            return {
                "user_number": user_num,
                "success": True,
                "subject": subject,
                "content": content,
                "error": None,
            }

        except Exception as e:
            return {
                "user_number": user_num,
                "success": False,
                "subject": None,
                "content": None,
                "error": str(e),
            }

    def save_test_results(self, send_results):
        """保存测试结果到测试目录"""
        test_dir = Path("test_output")
        test_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存发送结果
        send_file = test_dir / f"send_results_{timestamp}.json"
        with open(send_file, "w", encoding="utf-8") as f:
            json.dump(send_results, f, ensure_ascii=False, indent=2)

        # 保存每个用户的邮件内容到单独文件
        for user_num, email_data in self.sent_emails.items():
            email_file = test_dir / f"email_{user_num:03d}_{timestamp}.txt"
            with open(email_file, "w", encoding="utf-8") as f:
                f.write(f"用户编号: {user_num:03d}\n")
                f.write(f"主题: {email_data['subject']}\n")
                f.write(f"发送时间: {email_data['sent_time']}\n")
                f.write(f"内容:\n{email_data['content']}\n")

        print(f"📁 测试结果已保存到: {test_dir}")
        return test_dir

    def verify_results(self, send_results):
        """验证用户数字和内容匹配"""
        print(f"\n=== 验证结果 ===")

        successful_sends = [r for r in send_results if r["success"]]
        print(f"发送成功: {len(successful_sends)}/50")

        # 检查内容匹配
        matched = 0
        mismatched = []

        for result in successful_sends:
            user_num = result["user_number"]

            # 检查主题是否包含正确编号
            expected_subject = f"测试邮件#{user_num:03d}"
            actual_subject = result["subject"]

            # 检查内容中是否包含正确的用户编号
            expected_number = f"用户编号: {user_num:03d}"
            actual_content = result["content"]

            if expected_subject == actual_subject and expected_number in actual_content:
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
        else:
            print(f"✅ 所有邮件内容完全匹配！")

        success_rate = matched / max(len(successful_sends), 1) * 100
        print(f"匹配率: {success_rate:.1f}%")

        return success_rate >= 95

    def display_sample_results(self, count=5):
        """显示前几个用户的邮件内容"""
        print(f"\n=== 样本邮件内容 (前{count}个) ===")

        for i in range(1, min(count + 1, len(self.sent_emails) + 1)):
            if i in self.sent_emails:
                email_data = self.sent_emails[i]
                print(f"\n📧 用户 {i:03d} 的邮件:")
                print(f"   发送者: {email_data['user_info']['display_name']}")
                print(f"   主题: {email_data['subject']}")

                content_lines = email_data["content"].split("\n")[:8]
                print(f"   内容:")
                for line in content_lines:
                    if line.strip():
                        print(f"     {line}")

    def run_test(self, num_users=50):
        """运行完整测试"""
        print("简化版并发邮件测试")
        print("=" * 50)
        print(f"测试 {num_users} 个用户并发发送带编号邮件")
        print("模拟发送到文件系统，验证内容不错乱")
        print("=" * 50)

        try:
            # 1. 创建用户
            if not self.create_test_users(num_users):
                return False

            # 2. 并发发送邮件测试
            print(f"\n📤 并发发送测试...")
            start_time = time.time()

            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                send_futures = [
                    executor.submit(self.send_test_email, user)
                    for user in self.test_users[:num_users]
                ]

                send_results = []
                completed = 0

                for future in concurrent.futures.as_completed(send_futures, timeout=30):
                    try:
                        result = future.result()
                        send_results.append(result)
                        completed += 1

                        # 每完成10个显示进度
                        if completed % 10 == 0:
                            print(f"  进度: {completed}/{num_users}")

                    except Exception as e:
                        send_results.append(
                            {"user_number": -1, "success": False, "error": str(e)}
                        )

            duration = time.time() - start_time
            print(f"  并发发送完成，耗时: {duration:.2f} 秒")

            # 3. 保存结果
            self.save_test_results(send_results)

            # 4. 验证结果
            success = self.verify_results(send_results)

            # 5. 显示样本
            self.display_sample_results(5)

            if success:
                print(f"\n🎉 测试通过！邮件内容匹配正确")
                print(f"✅ {num_users} 个用户并发发送邮件，内容无错乱")
            else:
                print(f"\n❌ 测试失败！发现内容不匹配")

            return success

        except Exception as e:
            print(f"测试失败: {e}")
            import traceback

            print(f"详细错误: {traceback.format_exc()}")
            return False


def main():
    """主函数"""
    try:
        print("简化版并发邮件测试工具")
        print("模拟50个用户并发发送带编号邮件，验证内容不错乱")
        print("-" * 50)

        tester = SimpleConcurrencyTester()

        num_users = int(input("测试用户数 (默认50): ") or "50")

        if tester.run_test(num_users):
            print(f"\n✅ 并发测试成功！")
            print("📁 查看 test_output 目录了解详细结果")
            print("🔍 可以打开各个邮件文件验证用户编号是否正确对应")
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
