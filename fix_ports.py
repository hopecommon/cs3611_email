#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
端口问题修复工具 - 自动解决端口占用等问题
"""

import os
import sys
import subprocess
import socket
import time
import argparse
import platform
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common.port_config import (
    update_configuration,
    get_port_config,
    save_port_config,
    is_port_available,
)

# 添加从start_ssl_servers.py导入check_port函数
try:
    from start_ssl_servers import check_port
except ImportError:
    # 如果导入失败，定义一个兼容的函数
    def check_port(host, port, check_listening=False):
        """
        检查端口

        Args:
            host: 主机名
            port: 端口号
            check_listening: 是否检查服务是否在监听而不是检查是否可绑定

        Returns:
            True: 如果check_listening=True且有服务在监听，或check_listening=False且端口被占用
            False: 其他情况
        """
        if check_listening:
            # 检查是否有服务在监听这个端口
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((host, port))
                sock.close()
                # 返回0表示连接成功，即端口有服务在监听
                return result == 0
            except:
                # 出错时保守地返回False，表示无法确认是否有服务在监听
                return False
        else:
            # 先检查是否有服务在监听这个端口
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((host, port))
                sock.close()

                # 如果能连接成功，说明确实被占用了
                if result == 0:
                    return True

                # 无法连接，可能是系统保留或其他原因
                # 尝试绑定确认是否可用
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    sock.bind((host, port))
                    sock.listen(1)
                    sock.close()
                    # 能成功绑定，说明端口虽然无法连接但实际可用
                    return False
                except:
                    # 既无法连接也无法绑定，确实是被占用了
                    return True
            except:
                # 出错时，尝试直接绑定
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    sock.bind((host, port))
                    sock.listen(1)
                    sock.close()
                    # 可以绑定表示端口未被占用
                    return False
                except:
                    # 无法绑定表示端口被占用
                    return True


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="端口问题修复工具")
    parser.add_argument("--auto-fix", action="store_true", help="自动修复端口问题")
    parser.add_argument("--kill", action="store_true", help="终止占用端口的进程")
    parser.add_argument("--reset", action="store_true", help="重置为默认端口配置")
    parser.add_argument("--show", action="store_true", help="显示当前端口配置")
    return parser.parse_args()


def find_and_kill_process(port):
    """
    查找并终止占用指定端口的进程

    Returns:
        成功终止返回True，否则返回False
    """
    system = platform.system()

    try:
        if system == "Windows":
            # 查找进程
            cmd = f"netstat -ano | findstr :{port}"
            output = subprocess.check_output(cmd, shell=True).decode()

            pid = None
            for line in output.split("\n"):
                if "LISTENING" in line:
                    parts = line.strip().split()
                    pid = parts[-1]
                    break

            if pid:
                # 终止进程
                print(f"正在终止占用端口 {port} 的进程 (PID: {pid})...")
                subprocess.call(f"taskkill /F /PID {pid}", shell=True)
                return True
        elif system == "Linux" or system == "Darwin":  # Linux或macOS
            # 查找进程
            cmd = f"lsof -i :{port} -t"
            output = subprocess.check_output(cmd, shell=True).decode().strip()

            if output:
                # 终止进程
                pid = output.split("\n")[0]
                print(f"正在终止占用端口 {port} 的进程 (PID: {pid})...")
                subprocess.call(f"kill -9 {pid}", shell=True)
                return True
    except Exception as e:
        print(f"终止进程时出错: {e}")

    return False


def reset_port_config():
    """
    重置为默认端口配置
    """
    default_config = {
        "pop3_port": 12000,  # 使用非标准端口，避免冲突
        "pop3_ssl_port": 12995,
        "smtp_port": 8025,  # 使用非标准端口，避免冲突
        "smtp_ssl_port": 8465,
    }

    # 检查这些端口是否可用
    for service, port in default_config.items():
        if check_port("localhost", port, check_listening=False):
            print(f"警告: 默认端口 {port} 已被占用，尝试查找其他可用端口")

            # 查找可用端口
            base_port = port
            for offset in range(1, 10):
                new_port = base_port + offset
                if not check_port("localhost", new_port, check_listening=False):
                    default_config[service] = new_port
                    print(f"为 {service} 找到可用端口: {new_port}")
                    break
            else:
                print(f"错误: 无法为 {service} 找到可用端口")

    # 保存配置
    for service, port in default_config.items():
        save_port_config(service, port)
        print(f"已设置 {service} 为 {port}")

    return default_config


def show_port_info():
    """
    显示端口信息
    """
    config = get_port_config()
    print("\n当前端口配置:")
    for service, port in config.items():
        if isinstance(port, int):
            try:
                # 检查端口是否可绑定
                can_bind = not check_port("localhost", port, check_listening=False)
                # 检查是否有服务在监听
                has_service = check_port("localhost", port, check_listening=True)

                if can_bind:
                    status = "可用"
                elif has_service:
                    status = "被占用 (有服务在监听)"
                else:
                    status = "被占用 (无法绑定)"
            except Exception as e:
                status = f"状态检查失败: {str(e)}"

            print(f"  {service}: {port} - {status}")

    # 检查SSL证书
    cert_file = "certs/cert.pem"
    key_file = "certs/key.pem"

    print("\nSSL证书状态:")
    if os.path.exists(cert_file):
        print(f"  证书文件: {cert_file} - 存在")
    else:
        print(f"  证书文件: {cert_file} - 不存在")

    if os.path.exists(key_file):
        print(f"  密钥文件: {key_file} - 存在")
    else:
        print(f"  密钥文件: {key_file} - 不存在")

    # 显示运行提示
    print("\n运行服务器:")
    print("  python start_ssl_servers.py")
    print("  或分别运行:")
    print("  python -m server.authenticated_smtp_server --host localhost --port 8025")
    print("  python -m server.pop3_server --host localhost --port 12000")
    print("\n使用SSL:")
    print("  python start_ssl_servers.py --cert certs/cert.pem --key certs/key.pem")


def main():
    """主函数"""
    args = parse_args()

    # 如果没有指定任何操作，显示帮助
    if not any([args.auto_fix, args.kill, args.reset, args.show]):
        args.show = True

    if args.reset:
        print("正在重置端口配置...")
        reset_port_config()

    if args.kill:
        print("正在终止占用端口的进程...")
        config = get_port_config()
        killed = False

        for service, port in config.items():
            if isinstance(port, int) and check_port(
                "localhost", port, check_listening=False
            ):
                if find_and_kill_process(port):
                    print(f"已终止占用端口 {port} 的进程")
                    killed = True
                else:
                    print(f"无法终止占用端口 {port} 的进程")

        if not killed:
            print("没有找到需要终止的进程")

    if args.auto_fix:
        print("正在自动修复端口问题...")

        # 1. 首先尝试终止占用端口的进程
        config = get_port_config()
        killed = False

        for service, port in config.items():
            if isinstance(port, int) and check_port(
                "localhost", port, check_listening=False
            ):
                if find_and_kill_process(port):
                    print(f"已终止占用端口 {port} 的进程")
                    killed = True
                else:
                    print(f"无法终止占用端口 {port} 的进程")

        # 2. 如果仍有端口被占用，更新配置使用其他端口
        has_occupied = False
        for service, port in config.items():
            if isinstance(port, int) and check_port(
                "localhost", port, check_listening=False
            ):
                has_occupied = True
                break

        if has_occupied:
            print("部分端口仍被占用，更新配置使用其他端口...")
            result = update_configuration(auto_save=True)

            print("\n端口配置结果:")
            for service, info in result.items():
                changed = " (已更改)" if info["changed"] else ""
                print(f"  {service}: {info['port']}{changed} - {info['message']}")
        else:
            print("所有端口已可用")

    if args.show:
        show_port_info()

    return 0


if __name__ == "__main__":
    sys.exit(main())
