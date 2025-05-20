#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SSL邮件服务器启动脚本 - 启动支持SSL的SMTP和POP3服务器
"""

import os
import sys
import time
import socket
import subprocess
import json
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="启动支持SSL的邮件服务器")
    parser.add_argument("--smtp", action="store_true", help="只启动SMTP服务器")
    parser.add_argument("--pop3", action="store_true", help="只启动POP3服务器")
    parser.add_argument("--host", default="localhost", help="服务器主机名")
    parser.add_argument("--smtp-port", type=int, help="SMTP服务器端口")
    parser.add_argument("--pop3-port", type=int, help="POP3服务器端口")
    parser.add_argument("--no-ssl", action="store_true", help="禁用SSL")
    parser.add_argument(
        "--cert", type=str, default="certs/server.crt", help="SSL证书文件"
    )
    parser.add_argument(
        "--key", type=str, default="certs/server.key", help="SSL密钥文件"
    )
    return parser.parse_args()


def check_port(host, port, check_listening=True):
    """
    检查端口状态

    Args:
        host: 主机名
        port: 端口号
        check_listening: 如果为True，检查端口是否有服务在监听；如果为False，检查端口是否可以绑定

    Returns:
        如果端口被占用或有服务在监听（根据check_listening）返回True，否则返回False
    """
    if check_listening:
        # 检查是否有服务在监听这个端口
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
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
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()

            # 如果能连接成功，说明确实被占用了
            if result == 0:
                return True

            # 无法连接，可能是系统保留或其他原因
            # 尝试绑定确认是否可用
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
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
                sock.settimeout(1)
                sock.bind((host, port))
                sock.listen(1)
                sock.close()
                # 可以绑定表示端口未被占用
                return False
            except:
                # 无法绑定表示端口被占用
                return True


def load_port_config():
    """加载端口配置"""
    config_path = "config/port_config.json"
    if not os.path.exists(config_path):
        print(f"配置文件不存在: {config_path}")
        return {}

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"加载配置文件时出错: {e}")
        return {}


def check_ssl_cert(cert_path, key_path):
    """检查SSL证书"""
    print(f"检查SSL证书: {cert_path}")
    print(f"检查SSL密钥: {key_path}")

    # 检查文件是否存在
    if not os.path.exists(cert_path):
        print(f"错误: 证书文件不存在: {cert_path}")
        return False

    if not os.path.exists(key_path):
        print(f"错误: 密钥文件不存在: {key_path}")
        return False

    print("SSL证书和密钥文件存在")
    return True


def start_smtp_server(args, use_ssl=True):
    """启动SMTP服务器"""
    print("\n===== 启动SMTP服务器 =====")

    # 加载端口配置
    config = load_port_config()

    # 确定端口
    if use_ssl:
        port = args.smtp_port or config.get("smtp_ssl_port", 465)
    else:
        port = args.smtp_port or config.get("smtp_port", 8025)

    # 检查端口（检查是否可以绑定，而不是检查是否有服务在监听）
    if check_port(args.host, port, check_listening=False):
        print(f"警告: 端口 {port} 已被占用，服务器可能无法启动")
        print("建议先运行 python check_ports.py 清理占用的端口")

    # 构建命令
    cmd = [
        "python",
        "examples/run_auth_smtp_server.py",
        "--host",
        args.host,
        "--port",
        str(port),
    ]

    if use_ssl:
        cmd.append("--ssl")
        cmd.extend(["--cert", args.cert])
        cmd.extend(["--key", args.key])
    else:
        cmd.append("--no-ssl")

    # 启动服务器
    print(f"执行命令: {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    # 等待服务器启动
    print(f"等待SMTP{'(SSL)' if use_ssl else ''}服务器启动...")
    time.sleep(3)

    # 检查服务器是否成功启动（检查是否有服务在监听）
    if check_port(args.host, port, check_listening=True):
        print(f"SMTP{'(SSL)' if use_ssl else ''}服务器已成功启动在端口 {port}")
    else:
        print(f"警告: 无法检测到SMTP{'(SSL)' if use_ssl else ''}服务器在端口 {port}")

    return process


def start_pop3_server(args, use_ssl=True):
    """启动POP3服务器"""
    print("\n===== 启动POP3服务器 =====")

    # 加载端口配置
    config = load_port_config()

    # 确定端口
    if use_ssl:
        port = args.pop3_port or config.get("pop3_ssl_port", 995)
    else:
        port = args.pop3_port or config.get("pop3_port", 12000)

    # 检查端口（检查是否可以绑定，而不是检查是否有服务在监听）
    if check_port(args.host, port, check_listening=False):
        print(f"警告: 端口 {port} 已被占用，服务器可能无法启动")
        print("建议先运行 python check_ports.py 清理占用的端口")

    # 构建命令
    cmd = [
        "python",
        "examples/run_pop3_server.py",
        "--host",
        args.host,
        "--port",
        str(port),
    ]

    if use_ssl:
        cmd.append("--ssl")
        cmd.extend(["--ssl-cert", args.cert])
        cmd.extend(["--ssl-key", args.key])

    # 启动服务器
    print(f"执行命令: {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

    # 等待服务器启动
    print(f"等待POP3{'(SSL)' if use_ssl else ''}服务器启动...")
    time.sleep(3)

    # 检查服务器是否成功启动（检查是否有服务在监听）
    if check_port(args.host, port, check_listening=True):
        print(f"POP3{'(SSL)' if use_ssl else ''}服务器已成功启动在端口 {port}")
    else:
        print(f"警告: 无法检测到POP3{'(SSL)' if use_ssl else ''}服务器在端口 {port}")

    return process


def main():
    """主函数"""
    args = parse_args()

    # 如果没有指定服务器类型，则启动所有类型
    if not args.smtp and not args.pop3:
        args.smtp = True
        args.pop3 = True

    # 确定是否使用SSL
    use_ssl = not args.no_ssl

    # 如果使用SSL，检查证书
    if use_ssl:
        if not check_ssl_cert(args.cert, args.key):
            print("SSL证书检查失败，请确保证书文件存在")
            return 1

    # 启动服务器
    processes = []

    try:
        # 启动SMTP服务器
        if args.smtp:
            smtp_process = start_smtp_server(args, use_ssl)
            processes.append(smtp_process)

        # 启动POP3服务器
        if args.pop3:
            pop3_process = start_pop3_server(args, use_ssl)
            processes.append(pop3_process)

        # 等待用户输入
        print("\n服务器已启动，按Ctrl+C停止...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止服务器...")
    finally:
        # 停止服务器进程
        for process in processes:
            process.terminate()

        print("服务器已停止")

    return 0


if __name__ == "__main__":
    sys.exit(main())
