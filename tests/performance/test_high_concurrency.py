#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POP3服务器高并发性能测试
"""

import os
import sys
import time
import socket
import ssl
import threading
import concurrent.futures
import psutil
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from server.pop3_server import StablePOP3Server
from common.utils import setup_logging

# 设置日志
logger = setup_logging("test_high_concurrency")


class HighConcurrencyTester:
    """高并发测试类"""

    def __init__(self):
        self.server = None
        self.results = []
        self.start_time = None

    def start_optimized_server(self, port=8113, max_connections=200):
        """启动优化的POP3服务器"""
        print(f"启动优化POP3服务器 (端口 {port}, 最大连接 {max_connections})...")

        try:
            # 确保测试用户存在
            self.ensure_test_user()

            self.server = StablePOP3Server(
                host="localhost",
                port=port,
                use_ssl=False,  # 使用非SSL模式以提高稳定性
                max_connections=max_connections,
            )
            self.server.start()
            print(f"[OK] 优化POP3服务器启动成功: localhost:{port}")
            time.sleep(2)  # 等待服务器完全启动
            return True
        except Exception as e:
            print(f"[FAIL] 优化POP3服务器启动失败: {e}")
            import traceback

            print(f"详细错误: {traceback.format_exc()}")
            return False

    def ensure_test_user(self):
        """确保测试用户存在"""
        try:
            from server.user_auth import UserAuth

            user_auth = UserAuth()

            # 检查测试用户是否存在
            if not user_auth.get_user_by_username("testuser"):
                user_auth.add_user("testuser", "testpass", "testuser@example.com")
                print("[INFO] 创建测试用户: testuser")
            else:
                print("[INFO] 测试用户已存在: testuser")
        except Exception as e:
            print(f"[WARNING] 设置测试用户时出错: {e}")

    def stop_server(self):
        """停止服务器"""
        if self.server:
            try:
                self.server.stop()
                print("[OK] POP3服务器已停止")
            except Exception as e:
                print(f"[WARNING] 停止服务器时出错: {e}")

    def single_client_test(self, client_id, host="localhost", port=8113, timeout=30):
        """单个客户端测试（增加超时时间）"""
        start_time = time.time()

        try:
            # 连接到服务器
            sock = socket.create_connection((host, port), timeout=timeout)

            # 如果是SSL端口，包装为SSL连接
            if port == 8995:  # SSL端口
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                sock = context.wrap_socket(sock, server_hostname=host)

            try:
                # 接收欢迎消息
                welcome = sock.recv(1024).decode("utf-8").strip()
                if not welcome.startswith("+OK"):
                    raise Exception(f"欢迎消息错误: {welcome}")

                # 认证
                sock.send(b"USER testuser\r\n")
                user_resp = sock.recv(1024).decode("utf-8").strip()
                if not user_resp.startswith("+OK"):
                    raise Exception(f"USER命令失败: {user_resp}")

                sock.send(b"PASS testpass\r\n")
                pass_resp = sock.recv(1024).decode("utf-8").strip()
                if not pass_resp.startswith("+OK"):
                    raise Exception(f"PASS命令失败: {pass_resp}")

                # STAT命令
                sock.send(b"STAT\r\n")
                stat_resp = sock.recv(1024).decode("utf-8").strip()
                if not stat_resp.startswith("+OK"):
                    raise Exception(f"STAT命令失败: {stat_resp}")

                # QUIT
                sock.send(b"QUIT\r\n")
                quit_resp = sock.recv(1024).decode("utf-8").strip()

                end_time = time.time()
                duration = end_time - start_time

                return {
                    "client_id": client_id,
                    "success": True,
                    "duration": duration,
                    "error": None,
                }
            finally:
                sock.close()

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time

            return {
                "client_id": client_id,
                "success": False,
                "duration": duration,
                "error": str(e),
            }

    def monitor_system_resources(self, duration=60):
        """监控系统资源使用"""
        print(f"开始监控系统资源 ({duration}秒)...")

        start_time = time.time()
        cpu_samples = []
        memory_samples = []

        while time.time() - start_time < duration:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()

            cpu_samples.append(cpu_percent)
            memory_samples.append(memory_info.percent)

            time.sleep(1)

        return {
            "avg_cpu": sum(cpu_samples) / len(cpu_samples),
            "max_cpu": max(cpu_samples),
            "avg_memory": sum(memory_samples) / len(memory_samples),
            "max_memory": max(memory_samples),
        }

    def concurrent_test(self, num_clients=50, timeout=30):
        """并发测试"""
        print(f"\n=== 高并发测试: {num_clients} 个客户端 ===")

        # 启动资源监控
        monitor_thread = threading.Thread(
            target=lambda: setattr(
                self, "resource_stats", self.monitor_system_resources(30)
            ),
            daemon=True,
        )
        monitor_thread.start()

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_clients) as executor:
            # 提交所有任务
            futures = [
                executor.submit(self.single_client_test, i, "localhost", 8113, timeout)
                for i in range(num_clients)
            ]

            # 收集结果
            results = []
            completed = 0

            for future in concurrent.futures.as_completed(
                futures, timeout=timeout + 10
            ):
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1

                    # 每10个完成显示进度
                    if completed % 10 == 0:
                        print(f"  已完成: {completed}/{num_clients}")

                except Exception as e:
                    results.append(
                        {
                            "client_id": -1,
                            "success": False,
                            "duration": 0,
                            "error": str(e),
                        }
                    )

        end_time = time.time()
        total_duration = end_time - start_time

        # 等待监控线程完成
        monitor_thread.join(timeout=5)

        # 分析结果
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        print(f"\n=== 测试结果分析 ===")
        print(f"总耗时: {total_duration:.2f} 秒")
        print(
            f"成功连接: {len(successful)}/{num_clients} ({len(successful)/num_clients*100:.1f}%)"
        )
        print(
            f"失败连接: {len(failed)}/{num_clients} ({len(failed)/num_clients*100:.1f}%)"
        )

        if successful:
            durations = [r["duration"] for r in successful]
            avg_duration = sum(durations) / len(durations)
            min_duration = min(durations)
            max_duration = max(durations)

            print(f"平均响应时间: {avg_duration:.3f} 秒")
            print(f"最快响应时间: {min_duration:.3f} 秒")
            print(f"最慢响应时间: {max_duration:.3f} 秒")
            print(f"吞吐量: {len(successful)/total_duration:.2f} 连接/秒")

        # 显示资源使用情况
        if hasattr(self, "resource_stats"):
            stats = self.resource_stats
            print(f"\n=== 系统资源使用 ===")
            print(f"平均CPU使用率: {stats['avg_cpu']:.1f}%")
            print(f"最高CPU使用率: {stats['max_cpu']:.1f}%")
            print(f"平均内存使用率: {stats['avg_memory']:.1f}%")
            print(f"最高内存使用率: {stats['max_memory']:.1f}%")

        # 显示失败原因
        if failed:
            print(f"\n=== 失败原因分析 ===")
            error_counts = {}
            for r in failed:
                error = r["error"]
                if error in error_counts:
                    error_counts[error] += 1
                else:
                    error_counts[error] = 1

            for error, count in sorted(
                error_counts.items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  {error}: {count} 次")

        # 成功率阈值
        success_rate = len(successful) / num_clients * 100
        return success_rate >= 90  # 90%以上成功率认为通过

    def progressive_load_test(self):
        """渐进式负载测试"""
        print("POP3服务器渐进式负载测试")
        print("=" * 50)

        if not self.start_optimized_server():
            return False

        try:
            # 测试不同的并发级别
            test_cases = [
                (20, "基础并发"),
                (50, "中等并发"),
                (100, "高并发"),
                (200, "极高并发"),
            ]

            results = []

            for num_clients, description in test_cases:
                print(f"\n{'='*20} {description} ({num_clients}连接) {'='*20}")

                try:
                    success = self.concurrent_test(num_clients, timeout=60)
                    results.append((num_clients, description, success))

                    if success:
                        print(f"[PASS] {description} 测试通过")
                    else:
                        print(f"[FAIL] {description} 测试失败")

                    # 短暂休息让服务器恢复
                    print("等待服务器恢复...")
                    time.sleep(5)

                except Exception as e:
                    print(f"[ERROR] {description} 测试异常: {e}")
                    results.append((num_clients, description, False))

            # 总结结果
            print(f"\n{'='*50}")
            print("渐进式负载测试总结:")

            passed = 0
            for num_clients, description, success in results:
                status = "[PASS]" if success else "[FAIL]"
                print(f"{status} {description} ({num_clients}连接)")
                if success:
                    passed += 1

            print(f"\n通过率: {passed}/{len(results)} ({passed/len(results)*100:.1f}%)")

            return passed >= len(results) * 0.75  # 75%以上通过率认为成功

        finally:
            self.stop_server()


def main():
    """主函数"""
    try:
        tester = HighConcurrencyTester()

        if tester.progressive_load_test():
            print("\n[SUCCESS] 高并发性能测试成功！")
            return 0
        else:
            print("\n[FAILURE] 高并发性能测试失败！")
            return 1

    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n[FAIL] 测试过程中出错: {e}")
        import traceback

        print(f"详细错误: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
