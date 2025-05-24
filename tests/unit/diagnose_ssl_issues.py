#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POP3服务器SSL问题诊断脚本
"""

import os
import sys
import ssl
import socket
import time
import threading
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from server.pop3_server import StablePOP3Server
from common.config import SSL_CERT_FILE, SSL_KEY_FILE
from common.utils import setup_logging

# 设置日志
logger = setup_logging("diagnose_ssl")


class SSLDiagnostics:
    """SSL诊断类"""

    def __init__(self):
        self.results = {}

    def check_ssl_certificates(self):
        """检查SSL证书"""
        print("=== SSL证书检查 ===")

        # 检查证书文件是否存在
        cert_exists = os.path.exists(SSL_CERT_FILE)
        key_exists = os.path.exists(SSL_KEY_FILE)

        print(f"证书文件: {SSL_CERT_FILE}")
        print(f"  存在: {cert_exists}")
        if cert_exists:
            stat = os.stat(SSL_CERT_FILE)
            print(f"  大小: {stat.st_size} 字节")
            print(f"  修改时间: {time.ctime(stat.st_mtime)}")

        print(f"私钥文件: {SSL_KEY_FILE}")
        print(f"  存在: {key_exists}")
        if key_exists:
            stat = os.stat(SSL_KEY_FILE)
            print(f"  大小: {stat.st_size} 字节")
            print(f"  修改时间: {time.ctime(stat.st_mtime)}")

        # 尝试加载证书
        if cert_exists and key_exists:
            try:
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                context.load_cert_chain(SSL_CERT_FILE, SSL_KEY_FILE)
                print("[OK] SSL证书加载成功")

                # 获取证书信息
                with open(SSL_CERT_FILE, "rb") as f:
                    cert_data = f.read()
                    cert = ssl.DER_cert_to_PEM_cert(
                        ssl.PEM_cert_to_DER_cert(cert_data.decode())
                    )
                    print(f"[INFO] 证书格式: PEM")

                self.results["ssl_certs"] = True
                return True
            except Exception as e:
                print(f"[FAIL] SSL证书加载失败: {e}")
                self.results["ssl_certs"] = False
                return False
        else:
            print("[FAIL] SSL证书文件缺失")
            self.results["ssl_certs"] = False
            return False

    def test_ssl_context_creation(self):
        """测试SSL上下文创建"""
        print("\n=== SSL上下文创建测试 ===")

        try:
            # 测试不同的SSL上下文配置
            configs = [
                (
                    "默认配置",
                    lambda: ssl.create_default_context(ssl.Purpose.CLIENT_AUTH),
                ),
                ("TLS服务器", lambda: ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)),
                ("TLS客户端", lambda: ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)),
            ]

            for name, create_func in configs:
                try:
                    context = create_func()
                    if hasattr(context, "load_cert_chain"):
                        context.load_cert_chain(SSL_CERT_FILE, SSL_KEY_FILE)
                    print(f"[OK] {name}: 创建成功")
                    print(f"     协议: {context.protocol}")
                    print(f"     验证模式: {context.verify_mode}")
                except Exception as e:
                    print(f"[FAIL] {name}: {e}")

            self.results["ssl_context"] = True
            return True

        except Exception as e:
            print(f"[FAIL] SSL上下文创建失败: {e}")
            self.results["ssl_context"] = False
            return False

    def test_ssl_server_socket(self):
        """测试SSL服务器套接字"""
        print("\n=== SSL服务器套接字测试 ===")

        try:
            # 创建SSL上下文
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(SSL_CERT_FILE, SSL_KEY_FILE)

            # 创建服务器套接字
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # 绑定到测试端口
            test_port = 9995
            server_socket.bind(("localhost", test_port))
            server_socket.listen(1)

            print(f"[OK] SSL服务器套接字绑定到端口 {test_port}")

            # 包装为SSL套接字
            ssl_socket = context.wrap_socket(server_socket, server_side=True)
            print(f"[OK] SSL套接字包装成功")

            # 清理
            ssl_socket.close()

            self.results["ssl_socket"] = True
            return True

        except Exception as e:
            print(f"[FAIL] SSL服务器套接字测试失败: {e}")
            import traceback

            print(f"详细错误: {traceback.format_exc()}")
            self.results["ssl_socket"] = False
            return False

    def test_ssl_client_connection(self):
        """测试SSL客户端连接"""
        print("\n=== SSL客户端连接测试 ===")

        # 启动测试SSL服务器
        server_thread = threading.Thread(target=self._ssl_test_server, daemon=True)
        server_thread.start()
        time.sleep(1)  # 等待服务器启动

        try:
            # 创建SSL客户端
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            # 连接到测试服务器
            with socket.create_connection(("localhost", 9996)) as sock:
                with context.wrap_socket(sock, server_hostname="localhost") as ssl_sock:
                    print(f"[OK] SSL客户端连接成功")
                    print(f"     协议版本: {ssl_sock.version()}")
                    print(f"     加密套件: {ssl_sock.cipher()}")

                    # 发送测试数据
                    ssl_sock.send(b"TEST\r\n")
                    response = ssl_sock.recv(1024)
                    print(f"     服务器响应: {response.decode().strip()}")

            self.results["ssl_client"] = True
            return True

        except Exception as e:
            print(f"[FAIL] SSL客户端连接失败: {e}")
            import traceback

            print(f"详细错误: {traceback.format_exc()}")
            self.results["ssl_client"] = False
            return False

    def _ssl_test_server(self):
        """SSL测试服务器"""
        try:
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.load_cert_chain(SSL_CERT_FILE, SSL_KEY_FILE)

            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(("localhost", 9996))
            server_socket.listen(1)

            ssl_socket = context.wrap_socket(server_socket, server_side=True)

            conn, addr = ssl_socket.accept()
            data = conn.recv(1024)
            conn.send(b"+OK SSL Test Server\r\n")
            conn.close()
            ssl_socket.close()

        except Exception as e:
            print(f"SSL测试服务器错误: {e}")

    def test_pop3_ssl_server_startup(self):
        """测试POP3 SSL服务器启动"""
        print("\n=== POP3 SSL服务器启动测试 ===")

        try:
            # 创建SSL POP3服务器
            pop3_server = StablePOP3Server(
                host="localhost",
                port=9997,
                use_ssl=True,
                ssl_cert_file=SSL_CERT_FILE,
                ssl_key_file=SSL_KEY_FILE,
            )

            # 尝试启动
            pop3_server.start()
            print("[OK] POP3 SSL服务器启动成功")

            # 等待一下
            time.sleep(1)

            # 停止服务器
            pop3_server.stop()
            print("[OK] POP3 SSL服务器停止成功")

            self.results["pop3_ssl_startup"] = True
            return True

        except Exception as e:
            print(f"[FAIL] POP3 SSL服务器启动失败: {e}")
            import traceback

            print(f"详细错误: {traceback.format_exc()}")
            self.results["pop3_ssl_startup"] = False
            return False

    def run_all_diagnostics(self):
        """运行所有SSL诊断"""
        print("POP3 SSL诊断开始")
        print("=" * 50)

        tests = [
            ("SSL证书检查", self.check_ssl_certificates),
            ("SSL上下文创建", self.test_ssl_context_creation),
            ("SSL服务器套接字", self.test_ssl_server_socket),
            ("SSL客户端连接", self.test_ssl_client_connection),
            ("POP3 SSL服务器启动", self.test_pop3_ssl_server_startup),
        ]

        passed = 0
        total = len(tests)

        for name, test_func in tests:
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                print(f"[ERROR] {name} 测试异常: {e}")

        print("\n" + "=" * 50)
        print("SSL诊断结果总结:")
        print(f"通过: {passed}/{total}")

        for test_name, result in self.results.items():
            status = "[PASS]" if result else "[FAIL]"
            print(f"{status} {test_name}")

        return passed == total


def main():
    """主函数"""
    diagnostics = SSLDiagnostics()

    if diagnostics.run_all_diagnostics():
        print("\n[SUCCESS] 所有SSL诊断通过")
        return 0
    else:
        print("\n[FAILURE] 部分SSL诊断失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
