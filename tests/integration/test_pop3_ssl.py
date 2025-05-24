#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POP3 SSL连接专门测试
"""

import os
import sys
import ssl
import time
import socket
import threading
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from server.pop3_server import StablePOP3Server
from common.utils import setup_logging

# 设置日志
logger = setup_logging("test_pop3_ssl")


class POP3SSLTester:
    """POP3 SSL测试类"""

    def __init__(self):
        self.ssl_server = None
        self.non_ssl_server = None

    def start_ssl_server(self, port=995):
        """启动SSL POP3服务器"""
        print(f"启动SSL POP3服务器 (端口 {port})...")

        try:
            self.ssl_server = StablePOP3Server(
                host="localhost", port=port, use_ssl=True, max_connections=20
            )
            self.ssl_server.start()
            print(f"[OK] SSL POP3服务器启动成功: localhost:{port}")
            time.sleep(1)  # 等待服务器启动
            return True
        except Exception as e:
            print(f"[FAIL] SSL POP3服务器启动失败: {e}")
            return False

    def start_non_ssl_server(self, port=8110):
        """启动非SSL POP3服务器"""
        print(f"启动非SSL POP3服务器 (端口 {port})...")

        try:
            self.non_ssl_server = StablePOP3Server(
                host="localhost", port=port, use_ssl=False, max_connections=20
            )
            self.non_ssl_server.start()
            print(f"[OK] 非SSL POP3服务器启动成功: localhost:{port}")
            time.sleep(1)  # 等待服务器启动
            return True
        except Exception as e:
            print(f"[FAIL] 非SSL POP3服务器启动失败: {e}")
            return False

    def stop_servers(self):
        """停止所有服务器"""
        if self.ssl_server:
            try:
                self.ssl_server.stop()
                print("[OK] SSL POP3服务器已停止")
            except Exception as e:
                print(f"[WARNING] 停止SSL服务器时出错: {e}")

        if self.non_ssl_server:
            try:
                self.non_ssl_server.stop()
                print("[OK] 非SSL POP3服务器已停止")
            except Exception as e:
                print(f"[WARNING] 停止非SSL服务器时出错: {e}")

    def test_ssl_connection(self, host="localhost", port=995):
        """测试SSL连接"""
        print(f"\n=== SSL连接测试 ({host}:{port}) ===")

        try:
            # 创建SSL上下文
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            # 连接到SSL服务器
            with socket.create_connection((host, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssl_sock:
                    print(f"[OK] SSL连接建立成功")
                    print(f"     协议版本: {ssl_sock.version()}")
                    print(f"     加密套件: {ssl_sock.cipher()}")

                    # 接收欢迎消息
                    welcome = ssl_sock.recv(1024).decode("utf-8").strip()
                    print(f"[OK] 欢迎消息: {welcome}")

                    if not welcome.startswith("+OK"):
                        print(f"[FAIL] 欢迎消息格式错误")
                        return False

                    # 测试USER命令
                    ssl_sock.send(b"USER testuser\r\n")
                    user_resp = ssl_sock.recv(1024).decode("utf-8").strip()
                    print(f"[INFO] USER响应: {user_resp}")

                    if not user_resp.startswith("+OK"):
                        print(f"[FAIL] USER命令失败")
                        return False

                    # 测试PASS命令
                    ssl_sock.send(b"PASS testpass\r\n")
                    pass_resp = ssl_sock.recv(1024).decode("utf-8").strip()
                    print(f"[INFO] PASS响应: {pass_resp}")

                    if not pass_resp.startswith("+OK"):
                        print(f"[FAIL] PASS命令失败")
                        return False

                    # 测试STAT命令
                    ssl_sock.send(b"STAT\r\n")
                    stat_resp = ssl_sock.recv(1024).decode("utf-8").strip()
                    print(f"[INFO] STAT响应: {stat_resp}")

                    if not stat_resp.startswith("+OK"):
                        print(f"[FAIL] STAT命令失败")
                        return False

                    # 测试LIST命令
                    ssl_sock.send(b"LIST\r\n")
                    list_resp = ssl_sock.recv(1024).decode("utf-8").strip()
                    print(f"[INFO] LIST响应: {list_resp}")

                    if not list_resp.startswith("+OK"):
                        print(f"[FAIL] LIST命令失败")
                        return False

                    # 接收LIST数据
                    while True:
                        line = ssl_sock.recv(1024).decode("utf-8").strip()
                        if line == ".":
                            break
                        print(f"[INFO] LIST数据: {line}")

                    # 测试QUIT命令
                    ssl_sock.send(b"QUIT\r\n")
                    quit_resp = ssl_sock.recv(1024).decode("utf-8").strip()
                    print(f"[INFO] QUIT响应: {quit_resp}")

                    print(f"[SUCCESS] SSL连接测试完全成功")
                    return True

        except Exception as e:
            print(f"[FAIL] SSL连接测试失败: {e}")
            import traceback

            print(f"详细错误: {traceback.format_exc()}")
            return False

    def test_non_ssl_connection(self, host="localhost", port=8110):
        """测试非SSL连接"""
        print(f"\n=== 非SSL连接测试 ({host}:{port}) ===")

        try:
            # 直接TCP连接
            with socket.create_connection((host, port), timeout=10) as sock:
                print(f"[OK] 非SSL连接建立成功")

                # 接收欢迎消息
                welcome = sock.recv(1024).decode("utf-8").strip()
                print(f"[OK] 欢迎消息: {welcome}")

                if not welcome.startswith("+OK"):
                    print(f"[FAIL] 欢迎消息格式错误")
                    return False

                # 测试USER命令
                sock.send(b"USER testuser\r\n")
                user_resp = sock.recv(1024).decode("utf-8").strip()
                print(f"[INFO] USER响应: {user_resp}")

                # 测试PASS命令
                sock.send(b"PASS testpass\r\n")
                pass_resp = sock.recv(1024).decode("utf-8").strip()
                print(f"[INFO] PASS响应: {pass_resp}")

                # 测试STAT命令
                sock.send(b"STAT\r\n")
                stat_resp = sock.recv(1024).decode("utf-8").strip()
                print(f"[INFO] STAT响应: {stat_resp}")

                # 测试QUIT命令
                sock.send(b"QUIT\r\n")
                quit_resp = sock.recv(1024).decode("utf-8").strip()
                print(f"[INFO] QUIT响应: {quit_resp}")

                print(f"[SUCCESS] 非SSL连接测试成功")
                return True

        except Exception as e:
            print(f"[FAIL] 非SSL连接测试失败: {e}")
            return False

    def compare_ssl_vs_non_ssl(self):
        """对比SSL和非SSL模式"""
        print("\n=== SSL vs 非SSL 对比测试 ===")

        # 启动两个服务器
        ssl_started = self.start_ssl_server(995)
        non_ssl_started = self.start_non_ssl_server(8110)

        if not ssl_started or not non_ssl_started:
            print("[FAIL] 无法启动服务器进行对比测试")
            return False

        try:
            # 测试SSL连接
            ssl_start = time.time()
            ssl_success = self.test_ssl_connection("localhost", 995)
            ssl_duration = time.time() - ssl_start

            # 测试非SSL连接
            non_ssl_start = time.time()
            non_ssl_success = self.test_non_ssl_connection("localhost", 8110)
            non_ssl_duration = time.time() - non_ssl_start

            # 对比结果
            print(f"\n=== 对比结果 ===")
            print(f"SSL模式:")
            print(f"  成功: {'是' if ssl_success else '否'}")
            print(f"  耗时: {ssl_duration:.3f} 秒")

            print(f"非SSL模式:")
            print(f"  成功: {'是' if non_ssl_success else '否'}")
            print(f"  耗时: {non_ssl_duration:.3f} 秒")

            if ssl_success and non_ssl_success:
                overhead = ((ssl_duration - non_ssl_duration) / non_ssl_duration) * 100
                print(f"SSL开销: {overhead:.1f}%")
                print(f"[SUCCESS] SSL和非SSL模式都正常工作")
                return True
            else:
                print(f"[FAIL] 部分模式工作异常")
                return False

        finally:
            self.stop_servers()

    def run_ssl_stress_test(self, num_connections=10):
        """SSL压力测试"""
        print(f"\n=== SSL压力测试 ({num_connections}个连接) ===")

        if not self.start_ssl_server(995):
            return False

        try:
            import concurrent.futures

            def ssl_test_worker(worker_id):
                try:
                    return self.test_ssl_connection("localhost", 995)
                except Exception as e:
                    print(f"Worker {worker_id} 失败: {e}")
                    return False

            start_time = time.time()

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=num_connections
            ) as executor:
                futures = [
                    executor.submit(ssl_test_worker, i) for i in range(num_connections)
                ]

                results = []
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        results.append(False)

            end_time = time.time()
            duration = end_time - start_time

            successful = sum(results)
            success_rate = (successful / num_connections) * 100

            print(f"[INFO] SSL压力测试结果:")
            print(f"  总连接数: {num_connections}")
            print(f"  成功连接: {successful}")
            print(f"  成功率: {success_rate:.1f}%")
            print(f"  总耗时: {duration:.2f} 秒")
            print(f"  平均耗时: {duration/num_connections:.3f} 秒/连接")

            return success_rate >= 90  # 90%以上成功率认为通过

        finally:
            self.stop_servers()


def main():
    """主函数"""
    print("POP3 SSL连接专门测试")
    print("=" * 50)

    tester = POP3SSLTester()

    try:
        # 运行所有测试
        tests = [
            ("SSL vs 非SSL 对比", lambda: tester.compare_ssl_vs_non_ssl()),
            ("SSL压力测试 (5连接)", lambda: tester.run_ssl_stress_test(5)),
            ("SSL压力测试 (10连接)", lambda: tester.run_ssl_stress_test(10)),
        ]

        passed = 0
        total = len(tests)

        for name, test_func in tests:
            print(f"\n{'='*20} {name} {'='*20}")
            try:
                if test_func():
                    print(f"[PASS] {name}")
                    passed += 1
                else:
                    print(f"[FAIL] {name}")
            except Exception as e:
                print(f"[ERROR] {name} 异常: {e}")

        print(f"\n{'='*50}")
        print(f"测试结果: {passed}/{total} 通过")

        if passed == total:
            print("[SUCCESS] 所有SSL测试通过！")
            return 0
        else:
            print("[FAILURE] 部分SSL测试失败！")
            return 1

    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    finally:
        tester.stop_servers()


if __name__ == "__main__":
    sys.exit(main())
