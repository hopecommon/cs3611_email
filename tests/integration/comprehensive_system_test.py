#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件系统全面功能验证脚本
验证客户端和服务端的完整功能
"""

import os
import sys
import time
import json
import subprocess
import threading
import concurrent.futures
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from server.smtp_server import StableSMTPServer
from server.pop3_server import StablePOP3Server
from server.user_auth import UserAuth
from server.new_db_handler import EmailService as DatabaseHandler
from common.utils import setup_logging

# 设置日志
logger = setup_logging("comprehensive_system_test")


class SystemValidator:
    """系统功能验证器"""

    def __init__(self):
        self.smtp_server = None
        self.pop3_server = None
        self.test_results = {}
        self.start_time = datetime.now()

    def setup_test_environment(self):
        """设置测试环境"""
        print("[INFO] 设置测试环境...")

        # 确保测试用户存在
        try:
            user_auth = UserAuth()
            if not user_auth.get_user_by_username("testuser"):
                user_auth.add_user("testuser", "testpass", "testuser@example.com")
                print("[OK] 创建测试用户: testuser")
            else:
                print("[OK] 测试用户已存在: testuser")
        except Exception as e:
            print(f"[ERROR] 设置测试用户失败: {e}")
            return False

        # 确保数据目录存在
        os.makedirs("data", exist_ok=True)
        os.makedirs("logs", exist_ok=True)

        return True

    def start_servers(self):
        """启动服务器"""
        print("\n[INFO] 启动邮件服务器...")

        try:
            # 启动SMTP服务器
            self.smtp_server = StableSMTPServer(
                host="localhost", port=465, use_ssl=True, require_auth=True
            )
            self.smtp_server.start()
            print("[OK] SMTP SSL服务器启动成功 (端口465)")

            # 启动POP3服务器
            self.pop3_server = StablePOP3Server(
                host="localhost", port=8110, use_ssl=False
            )
            self.pop3_server.start()
            print("[OK] POP3服务器启动成功 (端口8110)")

            # 等待服务器完全启动
            time.sleep(2)
            return True

        except Exception as e:
            print(f"[ERROR] 启动服务器失败: {e}")
            return False

    def stop_servers(self):
        """停止服务器"""
        print("\n[INFO] 停止邮件服务器...")

        if self.smtp_server:
            try:
                self.smtp_server.stop()
                print("[OK] SMTP服务器已停止")
            except Exception as e:
                print(f"[WARNING] 停止SMTP服务器时出错: {e}")

        if self.pop3_server:
            try:
                self.pop3_server.stop()
                print("[OK] POP3服务器已停止")
            except Exception as e:
                print(f"[WARNING] 停止POP3服务器时出错: {e}")

    def test_smtp_functionality(self):
        """测试SMTP功能"""
        print("\n[EMAIL] 测试SMTP邮件发送功能...")

        test_cases = [
            {
                "name": "纯文本邮件",
                "args": [
                    "--host",
                    "localhost",
                    "--port",
                    "465",
                    "--ssl",
                    "--username",
                    "testuser",
                    "--password",
                    "testpass",
                    "--sender",
                    "testuser@example.com",
                    "--recipient",
                    "testuser@example.com",
                    "--subject",
                    "系统测试-纯文本邮件",
                    "--content",
                    "这是一封系统功能验证的纯文本邮件。",
                ],
            },
            {
                "name": "HTML邮件",
                "args": [
                    "--host",
                    "localhost",
                    "--port",
                    "465",
                    "--ssl",
                    "--username",
                    "testuser",
                    "--password",
                    "testpass",
                    "--sender",
                    "testuser@example.com",
                    "--recipient",
                    "testuser@example.com",
                    "--subject",
                    "系统测试-HTML邮件",
                    "--content",
                    "<h1>HTML邮件测试</h1><p>这是一封<b>HTML格式</b>的测试邮件。</p>",
                    "--html",
                ],
            },
        ]

        smtp_results = []

        for test_case in test_cases:
            print(f"  [SEND] 测试: {test_case['name']}")

            try:
                # 运行邮件发送脚本
                result = subprocess.run(
                    ["python", "examples/send_auth_email.py"] + test_case["args"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    print(f"    [OK] {test_case['name']} 发送成功")
                    smtp_results.append(True)
                else:
                    print(f"    [ERROR] {test_case['name']} 发送失败: {result.stderr}")
                    smtp_results.append(False)

            except subprocess.TimeoutExpired:
                print(f"    [ERROR] {test_case['name']} 发送超时")
                smtp_results.append(False)
            except Exception as e:
                print(f"    [ERROR] {test_case['name']} 发送异常: {e}")
                smtp_results.append(False)

        success_rate = sum(smtp_results) / len(smtp_results) * 100
        self.test_results["smtp"] = {
            "success_rate": success_rate,
            "total_tests": len(smtp_results),
            "passed": sum(smtp_results),
        }

        print(
            f"[RESULT] SMTP测试结果: {sum(smtp_results)}/{len(smtp_results)} 通过 ({success_rate:.1f}%)"
        )
        return success_rate >= 90

    def test_pop3_functionality(self):
        """测试POP3功能"""
        print("\n[RECEIVE] 测试POP3邮件接收功能...")

        test_cases = [
            {
                "name": "邮件列表获取",
                "args": [
                    "--host",
                    "localhost",
                    "--port",
                    "995",
                    "--ssl",
                    "--username",
                    "testuser",
                    "--password",
                    "testpass",
                    "--list",
                ],
            },
            {
                "name": "邮件内容检索",
                "args": [
                    "--host",
                    "localhost",
                    "--port",
                    "995",
                    "--ssl",
                    "--username",
                    "testuser",
                    "--password",
                    "testpass",
                    "--retrieve",
                    "1",
                ],
            },
        ]

        pop3_results = []

        for test_case in test_cases:
            print(f"  [DOWNLOAD] 测试: {test_case['name']}")

            try:
                # 运行POP3客户端脚本
                result = subprocess.run(
                    ["python", "-m", "client.pop3_cli"] + test_case["args"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode == 0:
                    print(f"    [OK] {test_case['name']} 成功")
                    pop3_results.append(True)
                else:
                    print(f"    [ERROR] {test_case['name']} 失败: {result.stderr}")
                    pop3_results.append(False)

            except subprocess.TimeoutExpired:
                print(f"    [ERROR] {test_case['name']} 超时")
                pop3_results.append(False)
            except Exception as e:
                print(f"    [ERROR] {test_case['name']} 异常: {e}")
                pop3_results.append(False)

        success_rate = sum(pop3_results) / len(pop3_results) * 100
        self.test_results["pop3"] = {
            "success_rate": success_rate,
            "total_tests": len(pop3_results),
            "passed": sum(pop3_results),
        }

        print(
            f"[RESULT] POP3测试结果: {sum(pop3_results)}/{len(pop3_results)} 通过 ({success_rate:.1f}%)"
        )
        return success_rate >= 90

    def test_database_functionality(self):
        """测试数据库功能"""
        print("\n[DATABASE] 测试数据库存储功能...")

        try:
            db = DatabaseHandler()

            # 测试邮件列表
            emails = db.list_emails()
            print(f"  [RESULT] 数据库中邮件总数: {len(emails)}")

            # 测试用户邮件查询
            user_emails = db.list_emails(user_email="testuser@example.com")
            print(f"  [RESULT] 测试用户邮件数: {len(user_emails)}")

            # 测试邮件内容获取
            if emails:
                content = db.get_email_content(emails[0]["message_id"])
                if content:
                    print(f"  [OK] 邮件内容获取成功 (长度: {len(content)} 字符)")
                else:
                    print(f"  [ERROR] 邮件内容获取失败")
                    return False

            self.test_results["database"] = {
                "success_rate": 100,
                "total_emails": len(emails),
                "user_emails": len(user_emails),
            }

            print(f"[RESULT] 数据库测试: 全部通过")
            return True

        except Exception as e:
            print(f"[ERROR] 数据库测试失败: {e}")
            self.test_results["database"] = {"success_rate": 0, "error": str(e)}
            return False

    def test_concurrent_performance(self, num_clients=60):
        """测试并发性能 - 内置实现"""
        print(f"\n[PERFORMANCE] 测试并发性能 ({num_clients}个客户端)...")

        try:
            # 直接在此处实现并发测试，避免外部脚本的编码问题
            successful_sends = 0
            failed_sends = 0
            send_times = []

            def send_test_email(client_id):
                """发送测试邮件的函数"""
                start_time = time.time()
                try:
                    # 使用subprocess发送邮件，但使用更简单的参数
                    result = subprocess.run(
                        [
                            "python",
                            "examples/send_auth_email.py",
                            "--host",
                            "localhost",
                            "--port",
                            "465",
                            "--ssl",
                            "--username",
                            "testuser",
                            "--password",
                            "testpass",
                            "--sender",
                            "testuser@example.com",
                            "--recipient",
                            "testuser@example.com",
                            "--subject",
                            f"并发测试邮件-{client_id}",
                            "--content",
                            f"这是第{client_id}个客户端发送的并发测试邮件。",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                    duration = time.time() - start_time
                    return (client_id, result.returncode == 0, duration)

                except Exception as e:
                    duration = time.time() - start_time
                    return (client_id, False, duration)

            print(f"  [SEND] 启动 {num_clients} 个并发客户端...")
            start_time = time.time()

            # 使用线程池实现真正的并发
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(num_clients, 20)
            ) as executor:
                # 提交所有发送任务
                futures = [
                    executor.submit(send_test_email, i)
                    for i in range(1, num_clients + 1)
                ]

                # 收集结果
                completed_count = 0
                for future in concurrent.futures.as_completed(futures, timeout=120):
                    try:
                        client_id, success, duration = future.result()
                        send_times.append(duration)

                        if success:
                            successful_sends += 1
                        else:
                            failed_sends += 1

                        completed_count += 1

                        # 每10个完成显示一次进度
                        if completed_count % 10 == 0:
                            print(
                                f"    [PROGRESS] 完成: {completed_count}/{num_clients}"
                            )

                    except Exception as e:
                        failed_sends += 1
                        print(f"    [ERROR] 客户端任务异常: {e}")

            total_time = time.time() - start_time
            success_rate = (
                (successful_sends / num_clients) * 100 if num_clients > 0 else 0
            )
            avg_response_time = sum(send_times) / len(send_times) if send_times else 0
            throughput = successful_sends / total_time if total_time > 0 else 0

            print(f"  [RESULT] 并发测试完成:")
            print(f"    成功发送: {successful_sends}/{num_clients}")
            print(f"    失败发送: {failed_sends}")
            print(f"    成功率: {success_rate:.1f}%")
            print(f"    总耗时: {total_time:.2f}秒")
            print(f"    平均响应时间: {avg_response_time:.3f}秒")
            print(f"    吞吐量: {throughput:.2f}邮件/秒")

            # 保存测试结果
            self.test_results["concurrency"] = {
                "success_rate": success_rate,
                "successful_sends": successful_sends,
                "failed_sends": failed_sends,
                "total_time": total_time,
                "avg_response_time": avg_response_time,
                "throughput": throughput,
                "num_clients": num_clients,
            }

            # 判断测试是否成功 (60%以上成功率认为通过)
            if success_rate >= 60.0:
                print(f"  [OK] 并发测试通过 (成功率: {success_rate:.1f}%)")
                print(f"  [INFO] 如需更精细的并发测试和详细分析报告，请运行:")
                print(f"         python tests/performance/test_enhanced_concurrency.py")
                return True
            else:
                print(f"  [FAIL] 并发测试失败 (成功率: {success_rate:.1f}%)")
                print(f"  [INFO] 如需更精细的并发测试和详细分析报告，请运行:")
                print(f"         python tests/performance/test_enhanced_concurrency.py")
                return False

        except Exception as e:
            print(f"  [ERROR] 并发测试异常: {e}")
            self.test_results["concurrency"] = {"success_rate": 0, "error": str(e)}
            return False

    def generate_test_report(self):
        """生成测试报告"""
        print("\n[REPORT] 生成测试报告...")

        end_time = datetime.now()
        duration = end_time - self.start_time

        report = {
            "test_summary": {
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration.total_seconds(),
                "overall_status": (
                    "PASS"
                    if all(
                        result.get("success_rate", 0) >= 90
                        for result in self.test_results.values()
                    )
                    else "FAIL"
                ),
            },
            "test_results": self.test_results,
            "system_info": {
                "smtp_server": "smtp_server.py (SSL enabled)",
                "pop3_server": "pop3_server.py (optimized)",
                "database": "SQLite with WAL mode",
                "authentication": "user_auth.py",
            },
        }

        # 保存报告
        with open("SYSTEM_VALIDATION_REPORT.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"[OK] 测试报告已保存: SYSTEM_VALIDATION_REPORT.json")
        return report

    def run_full_validation(self):
        """运行完整验证"""
        print("=" * 60)
        print("[MAGNIFYING_GLASS] 邮件系统全面功能验证")
        print("=" * 60)

        # 设置环境
        if not self.setup_test_environment():
            return False

        # 启动服务器
        if not self.start_servers():
            return False

        try:
            # 运行各项测试
            tests = [
                ("SMTP功能测试", self.test_smtp_functionality),
                ("数据库功能测试", self.test_database_functionality),
                ("POP3功能测试", self.test_pop3_functionality),
                ("简易并发性能测试", self.test_concurrent_performance),
            ]

            passed_tests = 0
            total_tests = len(tests)

            for test_name, test_func in tests:
                print(f"\n{'='*20} {test_name} {'='*20}")
                try:
                    if test_func():
                        print(f"[OK] {test_name} 通过")
                        passed_tests += 1
                    else:
                        print(f"[ERROR] {test_name} 失败")
                except Exception as e:
                    print(f"[ERROR] {test_name} 异常: {e}")

            # 生成报告
            report = self.generate_test_report()

            # 显示总结
            print("\n" + "=" * 60)
            print("[RESULT] 验证结果总结")
            print("=" * 60)
            print(
                f"测试通过率: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)"
            )
            print(f"总体状态: {report['test_summary']['overall_status']}")
            print(f"测试耗时: {report['test_summary']['duration_seconds']:.1f} 秒")
            print("")
            print("[ADVANCED] 进阶测试选项:")
            print("  如需更详细的并发性能分析和可视化报告，请运行:")
            print("  python tests/performance/test_enhanced_concurrency.py")
            print(
                "  该测试支持最多200个并发用户，包含详细的时间分析、内容完整性验证等功能"
            )

            return passed_tests == total_tests

        finally:
            self.stop_servers()


def main():
    """主函数"""
    validator = SystemValidator()

    try:
        if validator.run_full_validation():
            print("\n[SUCCESS] 系统验证成功！所有功能正常工作。")
            return 0
        else:
            print("\n[ERROR] 系统验证失败！存在功能问题。")
            return 1
    except KeyboardInterrupt:
        print("\n[WARNING] 验证被用户中断")
        return 1
    except Exception as e:
        print(f"\n[ERROR] 验证过程中出错: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
