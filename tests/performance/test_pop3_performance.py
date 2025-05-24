#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POP3服务器性能测试
"""

import os
import sys
import time
import socket
import threading
import concurrent.futures
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from server.pop3_server import StablePOP3Server
from common.utils import setup_logging

# 设置日志
logger = setup_logging("test_pop3_performance")


class POP3PerformanceTest:
    """POP3性能测试类"""

    def __init__(self, host="localhost", port=8112):
        self.host = host
        self.port = port
        self.server = None
        self.results = []

    def start_server(self):
        """启动POP3服务器"""
        print("启动POP3服务器...")
        self.server = StablePOP3Server(
            host=self.host,
            port=self.port,
            use_ssl=False,
            max_connections=50,  # 支持更多并发连接
        )

        try:
            self.server.start()
            print(f"[OK] POP3服务器启动成功: {self.host}:{self.port}")
            time.sleep(1)  # 等待服务器启动
            return True
        except Exception as e:
            print(f"[FAIL] POP3服务器启动失败: {e}")
            return False

    def stop_server(self):
        """停止POP3服务器"""
        if self.server:
            try:
                self.server.stop()
                print("[OK] POP3服务器已停止")
            except Exception as e:
                print(f"[WARNING] 停止服务器时出错: {e}")

    def single_client_test(self, client_id):
        """单个客户端测试"""
        start_time = time.time()

        try:
            # 连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.host, self.port))

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

            # LIST命令
            sock.send(b"LIST\r\n")
            list_resp = sock.recv(1024).decode("utf-8").strip()
            if not list_resp.startswith("+OK"):
                raise Exception(f"LIST命令失败: {list_resp}")

            # 接收LIST数据
            while True:
                line = sock.recv(1024).decode("utf-8").strip()
                if line == ".":
                    break

            # QUIT
            sock.send(b"QUIT\r\n")
            quit_resp = sock.recv(1024).decode("utf-8").strip()

            sock.close()

            end_time = time.time()
            duration = end_time - start_time

            return {
                "client_id": client_id,
                "success": True,
                "duration": duration,
                "error": None,
            }

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time

            return {
                "client_id": client_id,
                "success": False,
                "duration": duration,
                "error": str(e),
            }

    def concurrent_test(self, num_clients=10):
        """并发测试"""
        print(f"\n=== 并发测试: {num_clients} 个客户端 ===")

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_clients) as executor:
            # 提交所有任务
            futures = [
                executor.submit(self.single_client_test, i) for i in range(num_clients)
            ]

            # 收集结果
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
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

        # 分析结果
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        print(f"[INFO] 总耗时: {total_duration:.2f} 秒")
        print(f"[INFO] 成功连接: {len(successful)}/{num_clients}")
        print(f"[INFO] 失败连接: {len(failed)}/{num_clients}")

        if successful:
            avg_duration = sum(r["duration"] for r in successful) / len(successful)
            min_duration = min(r["duration"] for r in successful)
            max_duration = max(r["duration"] for r in successful)

            print(f"[INFO] 平均响应时间: {avg_duration:.3f} 秒")
            print(f"[INFO] 最快响应时间: {min_duration:.3f} 秒")
            print(f"[INFO] 最慢响应时间: {max_duration:.3f} 秒")
            print(f"[INFO] 吞吐量: {len(successful)/total_duration:.2f} 连接/秒")

        if failed:
            print(f"[WARNING] 失败的连接:")
            for r in failed[:5]:  # 只显示前5个错误
                print(f"  客户端 {r['client_id']}: {r['error']}")

        return len(successful) == num_clients

    def run_performance_tests(self):
        """运行性能测试"""
        print("POP3服务器性能测试")
        print("=" * 50)

        if not self.start_server():
            return False

        try:
            # 测试不同的并发级别
            test_cases = [1, 5, 10, 20]
            all_passed = True

            for num_clients in test_cases:
                success = self.concurrent_test(num_clients)
                if not success:
                    all_passed = False
                    print(f"[FAIL] {num_clients} 并发测试失败")
                else:
                    print(f"[SUCCESS] {num_clients} 并发测试成功")

                # 短暂休息
                time.sleep(1)

            return all_passed

        finally:
            self.stop_server()


def main():
    """主函数"""
    try:
        test = POP3PerformanceTest()

        if test.run_performance_tests():
            print("\n[SUCCESS] 所有性能测试通过！")
            return 0
        else:
            print("\n[FAIL] 部分性能测试失败！")
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
