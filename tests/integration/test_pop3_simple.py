#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的POP3服务器测试
"""

import os
import sys
import time
import socket
import threading
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from server.pop3_server import StablePOP3Server
from common.utils import setup_logging

# 设置日志
logger = setup_logging("test_pop3_simple")


def test_pop3_server():
    """测试POP3服务器"""
    print("=== 简化POP3服务器测试 ===")

    # 启动POP3服务器
    print("1. 启动POP3服务器...")
    pop3_server = StablePOP3Server(
        host="localhost", port=8111, use_ssl=False  # 使用不同的端口避免冲突
    )

    try:
        pop3_server.start()
        print("[OK] POP3服务器启动成功")

        # 等待服务器完全启动
        time.sleep(2)

        # 测试连接
        print("\n2. 测试连接...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)

        try:
            sock.connect(("localhost", 8111))
            print("[OK] 连接成功")

            # 接收欢迎消息
            welcome = sock.recv(1024).decode("utf-8").strip()
            print(f"[OK] 欢迎消息: {welcome}")

            # 发送USER命令
            print("\n3. 测试USER命令...")
            sock.send(b"USER testuser\r\n")
            user_resp = sock.recv(1024).decode("utf-8").strip()
            print(f"[INFO] USER响应: {user_resp}")

            # 发送PASS命令
            print("\n4. 测试PASS命令...")
            sock.send(b"PASS testpass\r\n")
            pass_resp = sock.recv(1024).decode("utf-8").strip()
            print(f"[INFO] PASS响应: {pass_resp}")

            if pass_resp.startswith("+OK"):
                # 发送STAT命令
                print("\n5. 测试STAT命令...")
                sock.send(b"STAT\r\n")
                stat_resp = sock.recv(1024).decode("utf-8").strip()
                print(f"[INFO] STAT响应: {stat_resp}")

                if stat_resp.startswith("+OK"):
                    print("[SUCCESS] STAT命令成功！")

                    # 解析响应
                    parts = stat_resp.split()
                    if len(parts) >= 3:
                        msg_count = parts[1]
                        total_size = parts[2]
                        print(
                            f"[INFO] 邮件数量: {msg_count}, 总大小: {total_size} 字节"
                        )
                else:
                    print(f"[FAIL] STAT命令失败: {stat_resp}")

                # 发送LIST命令
                print("\n6. 测试LIST命令...")
                sock.send(b"LIST\r\n")
                list_resp = sock.recv(1024).decode("utf-8").strip()
                print(f"[INFO] LIST响应: {list_resp}")

                # 如果LIST成功，接收邮件列表
                if list_resp.startswith("+OK"):
                    print("[OK] LIST命令成功，接收邮件列表...")
                    while True:
                        line = sock.recv(1024).decode("utf-8").strip()
                        print(f"[INFO] LIST数据: {line}")
                        if line == ".":
                            break

                # 发送QUIT命令
                print("\n7. 测试QUIT命令...")
                sock.send(b"QUIT\r\n")
                quit_resp = sock.recv(1024).decode("utf-8").strip()
                print(f"[INFO] QUIT响应: {quit_resp}")
            else:
                print(f"[FAIL] 认证失败: {pass_resp}")

        except Exception as e:
            print(f"[FAIL] 连接测试失败: {e}")
        finally:
            sock.close()

        print("\n[SUCCESS] POP3服务器测试完成")
        return True

    except Exception as e:
        print(f"[FAIL] POP3服务器测试失败: {e}")
        import traceback

        print(f"详细错误: {traceback.format_exc()}")
        return False
    finally:
        # 停止服务器
        print("\n停止POP3服务器...")
        try:
            pop3_server.stop()
            print("[OK] POP3服务器已停止")
        except Exception as e:
            print(f"[WARNING] 停止服务器时出错: {e}")


def main():
    """主函数"""
    print("简化POP3服务器测试")
    print("=" * 50)

    try:
        if test_pop3_server():
            print("\n[SUCCESS] 测试成功！")
            return 0
        else:
            print("\n[FAIL] 测试失败！")
            return 1
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n[FAIL] 测试过程中出错: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
