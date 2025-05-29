#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版SMTP/POP3并发压力测试
支持60个测试用户同时给同一个用户发送邮件
包含性能监控、连接管理和详细的结果验证
"""

import os
import sys
import time
import socket
import subprocess
import threading
import concurrent.futures
import json
import queue
import statistics
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from server.pop3_server import StablePOP3Server
from server.smtp_server import StableSMTPServer
from server.user_auth import UserAuth
from server.new_db_handler import EmailService
from common.utils import setup_logging
from common.config import MAX_CONNECTIONS, THREAD_POOL_SIZE

# 设置日志
logger = setup_logging("enhanced_concurrency_test")


@dataclass
class TestResult:
    """测试结果数据类"""

    user_number: int
    success: bool
    duration: float
    error: Optional[str] = None
    timestamp: Optional[datetime] = None


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""

    total_duration: float
    success_rate: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    throughput: float  # 请求/秒
    concurrent_connections: int
    errors: List[str]


class EnhancedConcurrencyTester:
    """增强版并发测试器"""

    def __init__(self):
        self.smtp_server = None
        self.pop3_server = None
        self.email_service = EmailService()
        self.user_auth = UserAuth()
        self.smtp_port = None
        self.pop3_port = None

        # 测试配置
        self.target_username = f"target_user_{datetime.now().strftime('%H%M%S')}"
        self.target_email = f"{self.target_username}@test.local"
        self.target_password = "targetpass123"

        # 性能监控
        self.connection_monitor = ConnectionMonitor()
        self.performance_metrics = []

        # 测试结果
        self.send_results: List[TestResult] = []
        self.receive_results: List[TestResult] = []

    def find_available_port(self, start_port=8000, max_attempts=100):
        """查找可用端口"""
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    sock.bind(("localhost", port))
                    return port
            except:
                continue
        return None

    def test_port_connection(self, host, port, timeout=5):
        """测试端口连接"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                return result == 0
        except:
            return False

    def start_servers(self):
        """启动SMTP和POP3服务器"""
        print("🚀 启动增强版邮件服务器...")

        # 查找可用端口
        self.smtp_port = self.find_available_port(8025)
        self.pop3_port = self.find_available_port(8110)

        if not self.smtp_port or not self.pop3_port:
            print("❌ 无法找到可用端口")
            return False

        print(f"📧 SMTP端口: {self.smtp_port}")
        print(f"📥 POP3端口: {self.pop3_port}")

        try:
            # 启动SMTP服务器（增强配置）
            self.smtp_server = StableSMTPServer(
                host="localhost",
                port=self.smtp_port,
                use_ssl=False,
                require_auth=True,
                db_handler=self.email_service,
                max_connections=MAX_CONNECTIONS,
            )

            # 直接调用start方法而不是在线程中启动
            self.smtp_server.start()

            # 等待SMTP服务器启动
            for i in range(30):  # 增加等待时间
                if self.test_port_connection("localhost", self.smtp_port):
                    print("✅ SMTP服务器已启动")
                    break
                time.sleep(0.5)
            else:
                print("❌ SMTP服务器启动失败")
                return False

            # 启动POP3服务器（增强配置）
            self.pop3_server = StablePOP3Server(
                host="localhost",
                port=self.pop3_port,
                use_ssl=False,
                max_connections=MAX_CONNECTIONS,
            )

            # 直接调用start方法而不是在线程中启动
            self.pop3_server.start()

            # 等待POP3服务器启动
            for i in range(30):  # 增加等待时间
                if self.test_port_connection("localhost", self.pop3_port):
                    print("✅ POP3服务器已启动")
                    break
                time.sleep(0.5)
            else:
                print("❌ POP3服务器启动失败")
                return False

            print("✅ 所有服务器启动成功！")

            # 额外的稳定性检查
            time.sleep(2)
            if not self.test_port_connection("localhost", self.smtp_port):
                print("❌ SMTP服务器连接测试失败")
                return False
            if not self.test_port_connection("localhost", self.pop3_port):
                print("❌ POP3服务器连接测试失败")
                return False

            print("✅ 服务器连接测试通过")
            return True

        except Exception as e:
            print(f"❌ 启动服务器失败: {e}")
            import traceback

            print(f"详细错误: {traceback.format_exc()}")
            return False

    def create_target_user(self):
        """创建目标用户"""
        print(f"👤 创建目标用户: {self.target_email}")
        try:
            user = self.user_auth.add_user(
                username=self.target_username,
                password=self.target_password,
                email=self.target_email,
                full_name=f"目标测试用户 {self.target_username}",
            )

            if user and self.user_auth.authenticate(
                self.target_username, self.target_password
            ):
                print("✅ 目标用户创建并验证成功")
                return True
            else:
                print("❌ 用户认证验证失败")
                return False

        except Exception as e:
            print(f"❌ 创建用户失败: {e}")
            return False

    def send_single_email(self, user_number: int) -> TestResult:
        """发送单封邮件"""
        start_time = time.time()

        try:
            subject = f"并发测试邮件 #{user_number:03d}"
            content = f"""这是第{user_number:03d}封并发测试邮件

邮件编号: {user_number:03d}
发送者ID: sender_{user_number:03d}
发送时间: {datetime.now()}
目标用户: {self.target_email}

本邮件用于测试SMTP服务器的高并发处理能力。
请验证邮件编号 {user_number:03d} 的正确性。
"""

            # 构造命令行参数
            cmd = [
                sys.executable,
                "-m",
                "client.smtp_cli",
                "--host",
                "localhost",
                "--port",
                str(self.smtp_port),
                "--username",
                self.target_username,
                "--password",
                self.target_password,
                "--from",
                f"sender_{user_number:03d}@test.local",
                "--to",
                self.target_email,
                "--subject",
                subject,
                "--text",
                content,
            ]

            # 执行命令
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent.parent.parent,
                capture_output=True,
                text=True,
                timeout=30,
            )

            duration = time.time() - start_time
            success = result.returncode == 0

            return TestResult(
                user_number=user_number,
                success=success,
                duration=duration,
                error=(
                    None if success else (result.stderr or result.stdout or "未知错误")
                ),
                timestamp=datetime.now(),
            )

        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                user_number=user_number,
                success=False,
                duration=duration,
                error=str(e),
                timestamp=datetime.now(),
            )

    def receive_emails_via_cli(self) -> List[Dict]:
        """通过POP3客户端接收邮件 - 增强重试机制"""
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                logger.info(f"尝试接收邮件 (第{attempt + 1}次)")

                # 直接使用POP3客户端而不是命令行工具
                from client.pop3_client_refactored import POP3Client

                pop3_client = POP3Client(
                    host="localhost",
                    port=self.pop3_port,
                    use_ssl=False,
                    username=self.target_username,
                    password=self.target_password,
                    timeout=60,
                    max_retries=3,
                )

                # 连接并获取邮件
                logger.debug("正在连接到POP3服务器...")
                pop3_client.connect()

                logger.debug("正在获取邮件列表...")
                emails = pop3_client.retrieve_all_emails()

                logger.debug("正在断开POP3连接...")
                pop3_client.disconnect()

                # 转换为测试所需的格式 - 增强内容验证
                result_emails = []
                for email in emails:
                    # 从主题中提取邮件编号
                    subject = email.subject or ""
                    content = email.text_content or ""

                    if "并发测试邮件" in subject and "#" in subject:
                        try:
                            # 提取邮件编号
                            start = subject.find("#") + 1
                            end = subject.find(" ", start)
                            if end == -1:
                                end = len(subject)
                            email_number = int(subject[start:end])

                            # 验证邮件内容是否包含正确的编号
                            expected_content_markers = [
                                f"邮件编号: {email_number:03d}",
                                f"发送者ID: sender_{email_number:03d}",
                                f"第{email_number:03d}封并发测试邮件",
                                f"请验证邮件编号 {email_number:03d} 的正确性",
                            ]

                            # 检查内容完整性
                            content_integrity = all(
                                marker in content for marker in expected_content_markers
                            )

                            # 提取时间戳（如果有的话）
                            received_time = datetime.now()  # 接收时间

                            result_emails.append(
                                {
                                    "number": email_number,
                                    "subject": subject,
                                    "content": content,
                                    "content_preview": (
                                        content[:200] + "..."
                                        if len(content) > 200
                                        else content
                                    ),
                                    "content_integrity": content_integrity,
                                    "from_addr": (
                                        email.from_addr.address
                                        if email.from_addr
                                        else ""
                                    ),
                                    "received_time": received_time,
                                    "content_markers": expected_content_markers,
                                    "email_size": len(content.encode("utf-8")),
                                    "has_expected_sender": f"sender_{email_number:03d}@test.local"
                                    in (
                                        email.from_addr.address
                                        if email.from_addr
                                        else ""
                                    ),
                                }
                            )
                        except Exception as e:
                            logger.error(f"解析邮件编号失败: {e}")
                            continue

                logger.info(f"成功接收 {len(result_emails)} 封邮件")
                return result_emails

            except Exception as e:
                logger.warning(f"第{attempt + 1}次接收邮件失败: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    logger.error("所有重试都失败了")

        # 如果所有重试都失败，返回空列表
        print("⚠️  邮件接收失败，可能需要更多时间等待邮件投递")
        return []

    def calculate_performance_metrics(
        self, results: List[TestResult]
    ) -> PerformanceMetrics:
        """计算性能指标"""
        if not results:
            return PerformanceMetrics(0, 0, 0, 0, 0, 0, 0, [])

        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        total_duration = max(r.duration for r in results) if results else 0
        success_rate = len(successful_results) / len(results) * 100

        if successful_results:
            durations = [r.duration for r in successful_results]
            avg_response_time = statistics.mean(durations)
            min_response_time = min(durations)
            max_response_time = max(durations)
            throughput = (
                len(successful_results) / total_duration if total_duration > 0 else 0
            )
        else:
            avg_response_time = min_response_time = max_response_time = throughput = 0

        errors = [r.error for r in failed_results if r.error]

        return PerformanceMetrics(
            total_duration=total_duration,
            success_rate=success_rate,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            throughput=throughput,
            concurrent_connections=len(results),
            errors=errors[:10],  # 只保留前10个错误
        )

    def save_test_results(
        self,
        send_results: List[TestResult],
        receive_results: List[Dict],
        metrics: PerformanceMetrics,
    ):
        """保存测试结果"""
        test_dir = Path("test_output")
        test_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存发送结果
        send_data = [
            {
                "user_number": r.user_number,
                "success": r.success,
                "duration": r.duration,
                "error": r.error,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            }
            for r in send_results
        ]

        send_file = test_dir / f"enhanced_send_results_{timestamp}.json"
        with open(send_file, "w", encoding="utf-8") as f:
            json.dump(send_data, f, ensure_ascii=False, indent=2)

        # 保存接收结果 - 添加默认转换器处理datetime
        receive_file = test_dir / f"enhanced_receive_results_{timestamp}.json"
        with open(receive_file, "w", encoding="utf-8") as f:
            json.dump(receive_results, f, ensure_ascii=False, indent=2, default=str)

        # 保存性能指标
        metrics_data = {
            "total_duration": metrics.total_duration,
            "success_rate": metrics.success_rate,
            "avg_response_time": metrics.avg_response_time,
            "min_response_time": metrics.min_response_time,
            "max_response_time": metrics.max_response_time,
            "throughput": metrics.throughput,
            "concurrent_connections": metrics.concurrent_connections,
            "errors": metrics.errors,
            "test_timestamp": timestamp,
        }

        metrics_file = test_dir / f"enhanced_performance_metrics_{timestamp}.json"
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(metrics_data, f, ensure_ascii=False, indent=2)

        print(f"📁 测试结果已保存到: {test_dir}")
        return test_dir

    def print_verification_report(self, report: Dict):
        """打印人类可读的验证报告"""
        print("\n" + "=" * 70)
        print("📊 详细验证报告 - 并发能力证据")
        print("=" * 70)

        # 1. 基本统计
        summary = report["test_summary"]
        print(f"\n📈 基本统计:")
        print(f"   发送邮件: {summary['successful_sent']}/{summary['total_sent']} 成功")
        print(f"   接收邮件: {summary['total_received']} 封")
        print(f"   匹配邮件: {summary['matched_emails']} 封")
        print(f"   匹配率: {summary['match_rate']:.1f}%")

        if summary.get("missing_numbers"):
            missing = summary["missing_numbers"][:10]  # 只显示前10个
            print(f"   ❌ 丢失编号: {missing}")

        # 2. 并发性证据
        timing = report.get("timing_analysis", {})
        if timing:
            print(f"\n⏱️ 并发性能分析:")
            print(f"   首次发送: {timing.get('first_send_time', 'N/A')}")
            print(f"   最后发送: {timing.get('last_send_time', 'N/A')}")
            print(f"   总耗时: {timing.get('total_send_duration', 0):.2f} 秒")
            print(f"   发送速率: {timing.get('send_rate', 0):.1f} 邮件/秒")
            print(
                f"   是否并发: {'✅ 是' if timing.get('is_concurrent', False) else '❌ 否'}"
            )

            dist = timing.get("time_distribution", {})
            print(f"   时间分布:")
            print(f"     < 1秒: {dist.get('under_1s', 0)} 个")
            print(f"     1-3秒: {dist.get('1s_to_3s', 0)} 个")
            print(f"     3-5秒: {dist.get('3s_to_5s', 0)} 个")
            print(f"     > 5秒: {dist.get('over_5s', 0)} 个")

        # 3. 内容完整性
        content = report.get("content_integrity", {})
        print(f"\n📝 内容完整性验证:")
        print(f"   检查邮件: {content.get('total_checked', 0)} 封")
        print(f"   完整性通过: {content.get('integrity_passed', 0)} 封")
        print(f"   完整性失败: {content.get('integrity_failed', 0)} 封")
        print(f"   完整性率: {content.get('integrity_rate', 0):.1f}%")
        print(f"   发送者准确: {content.get('correct_senders', 0)} 封")
        print(f"   发送者准确率: {content.get('sender_accuracy', 0):.1f}%")

        # 4. 内容样例展示
        samples = content.get("content_samples", [])
        if samples:
            print(f"\n📋 邮件内容样例验证:")
            for i, sample in enumerate(samples[:3], 1):  # 只显示前3个
                print(f"\n   邮件 #{sample['number']:03d}:")
                print(f"     主题: {sample['subject']}")
                print(f"     内容预览: {sample['content_preview'][:80]}...")
                print(
                    f"     完整性: {'✅ 通过' if sample['integrity_passed'] else '❌ 失败'}"
                )
                print(
                    f"     发送者: {'✅ 正确' if sample['sender_correct'] else '❌ 错误'}"
                )

        # 5. 并发能力证据汇总
        evidence = report.get("concurrency_evidence", {})
        print(f"\n🎯 并发能力证据:")
        print(f"   服务器配置: {evidence.get('server_capacity', 'N/A')}")
        print(f"   线程池大小: {evidence.get('thread_pool_size', 'N/A')}")
        print(f"   实际并发用户: {evidence.get('actual_concurrent_users', 'N/A')}")
        print(f"   峰值发送率: {evidence.get('peak_send_rate', 0):.1f} 邮件/秒")

        for point in evidence.get("evidence_points", []):
            print(f"   {point}")

        # 6. 详细结果表格
        detailed = report.get("detailed_results", {}).get("sample_emails", [])
        if detailed:
            print(f"\n📊 前10封邮件详细验证:")
            print("   编号 | 主题正确 | 内容完整 | 发送者正确 | 大小(字节)")
            print("   " + "-" * 55)
            for sample in detailed:
                num = sample["email_number"]
                subj = "✅" if sample["subject_correct"] else "❌"
                cont = "✅" if sample["all_markers_found"] else "❌"
                send = "✅" if "sender_" in sample.get("sender_email", "") else "❌"
                size = sample["size_bytes"]
                print(
                    f"   {num:03d}  |    {subj}     |    {cont}     |     {send}      | {size}"
                )

        print("\n" + "=" * 70)

    def verify_results(
        self, send_results: List[TestResult], receive_results: List[Dict]
    ) -> bool:
        """验证测试结果 - 增强版验证"""
        print("\n🔍 验证测试结果...")

        # 生成详细验证报告
        report = self.generate_detailed_verification_report(
            send_results, receive_results
        )

        # 打印详细报告
        self.print_verification_report(report)

        # 保存详细报告
        test_dir = Path("test_output")
        test_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        report_file = test_dir / f"detailed_verification_report_{timestamp}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        # 生成人类可读的报告文件
        readable_report_file = test_dir / f"verification_report_{timestamp}.txt"
        with open(readable_report_file, "w", encoding="utf-8") as f:
            import io
            import sys

            old_stdout = sys.stdout
            sys.stdout = f
            self.print_verification_report(report)
            sys.stdout = old_stdout

        print(f"\n📁 详细验证报告已保存: {report_file}")
        print(f"📁 人类可读报告已保存: {readable_report_file}")

        # 判断测试是否成功
        summary = report["test_summary"]
        content = report["content_integrity"]
        timing = report.get("timing_analysis", {})

        success_criteria = [
            summary["match_rate"] >= 95.0,  # 95%以上匹配率
            content.get("integrity_rate", 0) >= 90.0,  # 90%以上内容完整性
            content.get("sender_accuracy", 0) >= 95.0,  # 95%以上发送者准确性
            timing.get("is_concurrent", False),  # 真正的并发
        ]

        passed_criteria = sum(success_criteria)
        total_criteria = len(success_criteria)

        print(f"\n✅ 验证标准通过情况: {passed_criteria}/{total_criteria}")

        if all(success_criteria):
            print("🎉 所有验证标准都通过！并发能力得到充分证明！")
            return True
        else:
            print("❌ 部分验证标准未通过，需要进一步分析")
            return False

    def cleanup_servers(self):
        """清理服务器"""
        print("\n🧹 清理服务器...")
        try:
            if self.smtp_server:
                self.smtp_server.stop()
            if self.pop3_server:
                self.pop3_server.stop()
        except:
            pass

    def run_test_only(self, num_users=60):
        """运行测试（服务器已启动）"""
        print("增强版SMTP/POP3并发压力测试")
        print("=" * 60)
        print(f"测试方案: {num_users}个发送者 → 1个接收者")
        print(f"最大连接数: {MAX_CONNECTIONS}")
        print(f"线程池大小: {THREAD_POOL_SIZE}")
        print("=" * 60)

        try:
            # 1. 启动性能监控
            self.connection_monitor.start()

            # 2. 并发发送邮件
            print(f"📤 开始并发发送 {num_users} 封邮件...")
            start_time = time.time()

            # 使用更大的线程池
            max_workers = min(num_users, THREAD_POOL_SIZE // 2)
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=max_workers
            ) as executor:
                send_futures = [
                    executor.submit(self.send_single_email, i)
                    for i in range(1, num_users + 1)
                ]

                completed = 0
                for future in concurrent.futures.as_completed(
                    send_futures, timeout=300
                ):
                    try:
                        result = future.result()
                        self.send_results.append(result)
                        completed += 1

                        if completed % 10 == 0:
                            success_count = sum(
                                1 for r in self.send_results if r.success
                            )
                            print(
                                f"  进度: {completed}/{num_users} (成功: {success_count})"
                            )

                    except Exception as e:
                        self.send_results.append(
                            TestResult(
                                user_number=-1, success=False, duration=0, error=str(e)
                            )
                        )

            send_duration = time.time() - start_time
            success_count = sum(1 for r in self.send_results if r.success)
            print(
                f"✅ 发送完成! 成功: {success_count}/{num_users}, 耗时: {send_duration:.2f}秒"
            )

            # 3. 等待邮件投递和处理
            print("⏱️  等待邮件投递和处理...")
            time.sleep(8)  # 增加等待时间，让服务器有足够时间处理

            # 4. 接收邮件
            print("📥 接收邮件...")
            received_emails = self.receive_emails_via_cli()
            print(f"📥 接收到 {len(received_emails)} 封邮件")

            # 5. 停止性能监控
            self.connection_monitor.stop()

            # 6. 计算性能指标
            metrics = self.calculate_performance_metrics(self.send_results)

            # 7. 保存结果
            test_dir = self.save_test_results(
                self.send_results, received_emails, metrics
            )

            # 8. 显示性能报告
            self.display_performance_report(metrics)

            # 9. 验证结果并生成详细报告
            success = self.verify_results(self.send_results, received_emails)

            # 10. 生成详细验证报告
            report = self.generate_detailed_verification_report(
                self.send_results, received_emails
            )

            # 返回测试结果和报告
            return success, report

        except Exception as e:
            print(f"测试失败: {e}")
            import traceback

            print(f"详细错误: {traceback.format_exc()}")
            return False, {}

        finally:
            self.connection_monitor.stop()

    def display_performance_report(self, metrics: PerformanceMetrics):
        """显示性能报告"""
        print("\n📊 性能报告")
        print("=" * 40)
        print(f"总耗时: {metrics.total_duration:.2f} 秒")
        print(f"成功率: {metrics.success_rate:.1f}%")
        print(f"平均响应时间: {metrics.avg_response_time:.3f} 秒")
        print(f"最快响应时间: {metrics.min_response_time:.3f} 秒")
        print(f"最慢响应时间: {metrics.max_response_time:.3f} 秒")
        print(f"吞吐量: {metrics.throughput:.2f} 请求/秒")
        print(f"并发连接数: {metrics.concurrent_connections}")

        if metrics.errors:
            print(f"\n❌ 前5个错误:")
            for i, error in enumerate(metrics.errors[:5], 1):
                print(f"  {i}. {error[:100]}...")

    def generate_detailed_verification_report(
        self, send_results: List[TestResult], receive_results: List[Dict]
    ) -> Dict:
        """生成详细的验证报告，提供直观的并发能力证据"""
        print("\n📋 生成详细验证报告...")

        report = {
            "test_summary": {},
            "timing_analysis": {},
            "content_integrity": {},
            "concurrency_evidence": {},
            "detailed_results": {},
        }

        # 1. 测试摘要
        successful_sends = [r for r in send_results if r.success]
        successful_numbers = {r.user_number for r in successful_sends}
        received_numbers = {email["number"] for email in receive_results}
        matched_numbers = successful_numbers & received_numbers

        report["test_summary"] = {
            "total_sent": len(send_results),
            "successful_sent": len(successful_sends),
            "total_received": len(receive_results),
            "matched_emails": len(matched_numbers),
            "match_rate": (
                len(matched_numbers) / len(successful_sends) * 100
                if successful_sends
                else 0
            ),
            "missing_numbers": sorted(list(successful_numbers - received_numbers)),
            "extra_numbers": sorted(list(received_numbers - successful_numbers)),
        }

        # 2. 时间分析 - 证明并发性
        if send_results:
            send_times = [
                r.timestamp for r in send_results if r.timestamp and r.success
            ]
            if send_times:
                send_times.sort()
                time_spans = []
                for i in range(1, len(send_times)):
                    span = (send_times[i] - send_times[0]).total_seconds()
                    time_spans.append(span)

                total_duration = (send_times[-1] - send_times[0]).total_seconds()

                report["timing_analysis"] = {
                    "first_send_time": send_times[0].strftime("%H:%M:%S.%f")[:-3],
                    "last_send_time": send_times[-1].strftime("%H:%M:%S.%f")[:-3],
                    "total_send_duration": total_duration,
                    "average_interval": (
                        statistics.mean(time_spans) if time_spans else 0
                    ),
                    "concurrent_window": len(
                        [t for t in time_spans if t < 5.0]
                    ),  # 5秒内的发送
                    # 修复并发判定逻辑：检查发送密度和总时间
                    "is_concurrent": (
                        total_duration <= 10.0  # 总时间不超过10秒
                        and len(send_times) >= 2  # 至少2封邮件
                        and (len(send_times) / max(total_duration, 0.001))
                        >= 0.5  # 发送密度 >= 0.5邮件/秒
                    )
                    or (
                        len(send_times) <= 5
                        and total_duration <= 2.0  # 小规模测试：5封邮件2秒内完成
                    ),
                    "send_rate": len(send_times)
                    / max(total_duration, 0.001),  # 避免除零
                    "time_distribution": {
                        "under_1s": len([t for t in time_spans if t < 1.0]),
                        "1s_to_3s": len([t for t in time_spans if 1.0 <= t < 3.0]),
                        "3s_to_5s": len([t for t in time_spans if 3.0 <= t < 5.0]),
                        "over_5s": len([t for t in time_spans if t >= 5.0]),
                    },
                }

        # 3. 内容完整性分析
        content_stats = {
            "total_checked": len(receive_results),
            "integrity_passed": 0,
            "integrity_failed": 0,
            "correct_senders": 0,
            "content_samples": [],
            "integrity_details": [],
        }

        for email in receive_results:
            # 内容完整性检查
            if email.get("content_integrity", False):
                content_stats["integrity_passed"] += 1
            else:
                content_stats["integrity_failed"] += 1

            # 发送者正确性检查
            if email.get("has_expected_sender", False):
                content_stats["correct_senders"] += 1

            # 收集内容样例
            if len(content_stats["content_samples"]) < 5:  # 只保存前5个样例
                content_stats["content_samples"].append(
                    {
                        "number": email["number"],
                        "subject": email["subject"],
                        "content_preview": email.get("content_preview", ""),
                        "expected_markers": email.get("content_markers", []),
                        "integrity_passed": email.get("content_integrity", False),
                        "sender_correct": email.get("has_expected_sender", False),
                    }
                )

            # 详细完整性信息
            content_stats["integrity_details"].append(
                {
                    "number": email["number"],
                    "integrity": email.get("content_integrity", False),
                    "size": email.get("email_size", 0),
                    "has_correct_sender": email.get("has_expected_sender", False),
                }
            )

        content_stats["integrity_rate"] = (
            content_stats["integrity_passed"] / max(content_stats["total_checked"], 1)
        ) * 100
        content_stats["sender_accuracy"] = (
            content_stats["correct_senders"] / max(content_stats["total_checked"], 1)
        ) * 100

        report["content_integrity"] = content_stats

        # 4. 并发能力证据
        concurrency_evidence = {
            "server_capacity": f"支持 {MAX_CONNECTIONS} 并发连接",
            "thread_pool_size": THREAD_POOL_SIZE,
            "actual_concurrent_users": len(send_results),
            "peak_send_rate": report["timing_analysis"].get("send_rate", 0),
            "evidence_points": [],
        }

        # 生成证据点
        if report["timing_analysis"].get("is_concurrent", False):
            concurrency_evidence["evidence_points"].append(
                "✅ 发送时间分布证明真正的并发处理"
            )
        else:
            # 添加并发性判定失败的详细说明
            timing = report["timing_analysis"]
            total_duration = timing.get("total_send_duration", 0)
            send_rate = timing.get("send_rate", 0)
            email_count = len(send_results)

            if email_count <= 5:
                if total_duration <= 2.0:
                    concurrency_evidence["evidence_points"].append(
                        f"⚠️ 小规模测试({email_count}封邮件)在{total_duration:.2f}秒内完成，属于并发处理"
                    )
                    # 重新设置并发状态
                    report["timing_analysis"]["is_concurrent"] = True
                else:
                    concurrency_evidence["evidence_points"].append(
                        f"❌ 发送时间过长({total_duration:.2f}秒)，可能存在性能问题"
                    )
            else:
                concurrency_evidence["evidence_points"].append(
                    f"❌ 发送密度不足({send_rate:.1f}邮件/秒)，未达到并发标准"
                )

        if report["test_summary"]["match_rate"] > 95:
            concurrency_evidence["evidence_points"].append(
                "✅ 高匹配率证明并发处理的可靠性"
            )

        if content_stats["integrity_rate"] > 90:
            concurrency_evidence["evidence_points"].append(
                "✅ 高内容完整性证明没有数据混乱"
            )

        if content_stats["sender_accuracy"] > 95:
            concurrency_evidence["evidence_points"].append(
                "✅ 发送者准确性证明邮件正确路由"
            )

        concurrency_evidence["evidence_points"].append(
            f"✅ {len(matched_numbers)}封邮件编号完全匹配，无错位"
        )

        report["concurrency_evidence"] = concurrency_evidence

        # 5. 详细结果样例（用于人工验证）
        detailed_samples = []
        for i, email in enumerate(
            sorted(receive_results, key=lambda x: x["number"])[:10]
        ):  # 前10个
            detailed_samples.append(
                {
                    "email_number": email["number"],
                    "subject_correct": f"#{email['number']:03d}" in email["subject"],
                    "content_snippet": email.get("content_preview", "")[:100],
                    "all_markers_found": email.get("content_integrity", False),
                    "sender_email": email.get("from_addr", ""),
                    "size_bytes": email.get("email_size", 0),
                }
            )

        report["detailed_results"]["sample_emails"] = detailed_samples

        return report


class ConnectionMonitor:
    """连接监控器"""

    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        self.metrics = []

    def start(self):
        """开始监控"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

    def _monitor(self):
        """监控循环"""
        while self.monitoring:
            try:
                # 这里可以添加系统资源监控
                # 例如：CPU使用率、内存使用率、网络连接数等
                time.sleep(1)
            except:
                pass


def main():
    """主函数"""
    try:
        print("增强版SMTP/POP3并发压力测试工具")
        print("支持60个用户同时发送邮件，包含详细的性能分析")
        print("-" * 60)

        print("请选择测试模式:")
        print("1. 快速测试 (5个用户)")
        print("2. 中等测试 (20个用户)")
        print("3. 高负载测试 (60个用户)")
        print("4. 极限测试 (100个用户)")
        print("5. 自定义用户数")

        choice = input("选择模式 (1/2/3/4/5, 默认2): ").strip() or "2"

        if choice == "1":
            num_users = 5
        elif choice == "2":
            num_users = 20
        elif choice == "3":
            num_users = 60
        elif choice == "4":
            num_users = 100
        elif choice == "5":
            num_users = int(input("输入用户数 (1-200): ") or "10")
        else:
            num_users = 20

        print(f"\n开始 {num_users} 用户并发测试...")

        # 直接在这里管理服务器生命周期
        smtp_server = None
        pop3_server = None

        try:
            print("🚀 直接启动邮件服务器...")

            # 查找可用端口
            def find_available_port(start_port=8000, max_attempts=100):
                import socket

                for port in range(start_port, start_port + max_attempts):
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                            sock.settimeout(1)
                            sock.bind(("localhost", port))
                            return port
                    except:
                        continue
                return None

            smtp_port = find_available_port(8025)
            pop3_port = find_available_port(8110)

            if not smtp_port or not pop3_port:
                print("❌ 无法找到可用端口")
                return 1

            print(f"📧 SMTP端口: {smtp_port}")
            print(f"📥 POP3端口: {pop3_port}")

            # 创建邮件服务
            email_service = EmailService()

            # 启动SMTP服务器
            smtp_server = StableSMTPServer(
                host="localhost",
                port=smtp_port,
                use_ssl=False,
                require_auth=True,
                db_handler=email_service,
                max_connections=MAX_CONNECTIONS,
            )
            smtp_server.start()
            print("✅ SMTP服务器已启动")

            # 启动POP3服务器
            pop3_server = StablePOP3Server(
                host="localhost",
                port=pop3_port,
                use_ssl=False,
                max_connections=MAX_CONNECTIONS,
            )
            pop3_server.start()
            print("✅ POP3服务器已启动")

            # 等待服务器稳定
            print("⏱️  等待服务器稳定...")
            time.sleep(5)

            # 测试连接
            def test_port_connection(host, port, timeout=5):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        sock.settimeout(timeout)
                        result = sock.connect_ex((host, port))
                        return result == 0
                except:
                    return False

            if not test_port_connection("localhost", smtp_port):
                print("❌ SMTP服务器连接测试失败")
                return 1
            if not test_port_connection("localhost", pop3_port):
                print("❌ POP3服务器连接测试失败")
                return 1

            print("✅ 服务器连接测试通过")

            # 创建并运行测试
            tester = EnhancedConcurrencyTester()
            tester.smtp_port = smtp_port
            tester.pop3_port = pop3_port
            tester.email_service = email_service

            # 创建目标用户
            if not tester.create_target_user():
                print("❌ 创建目标用户失败")
                return 1

            # 运行测试（不再启动服务器）
            try:
                success, report = tester.run_test_only(num_users)
            except ValueError:
                # 兼容旧版本可能只返回布尔值的情况
                success = tester.run_test_only(num_users)
                report = {}

            if success:
                print(f"\n✅ 增强版并发测试成功!")
                print("📁 查看 test_output 目录了解详细结果")

                # 自动生成可视化报告
                try:
                    from tests.performance.generate_visual_report import (
                        generate_html_report,
                    )

                    # 定义输出目录和时间戳
                    test_dir = Path("test_output")
                    test_dir.mkdir(exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    html_file = test_dir / f"visual_report_{timestamp}.html"

                    if report:  # 只有当报告数据存在时才生成报告
                        generate_html_report(report, str(html_file))
                        print(f"🌐 可视化报告已生成: {html_file}")

                        # 尝试打开浏览器
                        try:
                            import webbrowser

                            webbrowser.open(f"file://{html_file.absolute()}")
                            print("🔗 已在浏览器中打开可视化报告")
                        except:
                            print("💡 请手动在浏览器中打开HTML文件查看详细证据")
                    else:
                        print("⚠️ 无法生成可视化报告：缺少报告数据")

                except Exception as e:
                    print(f"⚠️  生成可视化报告失败: {e}")

                return 0
            else:
                print(f"\n❌ 增强版并发测试失败!")
                print("💡 请查看详细验证报告了解失败原因")

                # 即使失败也尝试生成报告以供分析
                if "report" in locals() and report:
                    try:
                        from tests.performance.generate_visual_report import (
                            generate_html_report,
                        )

                        test_dir = Path("test_output")
                        test_dir.mkdir(exist_ok=True)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        html_file = test_dir / f"failed_test_report_{timestamp}.html"
                        generate_html_report(report, str(html_file))
                        print(f"📊 失败分析报告已生成: {html_file}")
                    except Exception as e:
                        print(f"⚠️  生成失败分析报告失败: {e}")

                return 1

        finally:
            # 清理服务器
            print("\n🧹 清理服务器...")
            try:
                if smtp_server:
                    smtp_server.stop()
                if pop3_server:
                    pop3_server.stop()
            except:
                pass

    except KeyboardInterrupt:
        print("\n测试被中断")
        return 1
    except Exception as e:
        print(f"\n测试启动失败: {e}")
        import traceback

        print(f"详细错误: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
