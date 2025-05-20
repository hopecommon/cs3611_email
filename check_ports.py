#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
端口管理工具 - 检查并管理邮件服务器端口配置
"""

import os
import sys
import argparse
import json
import socket
import subprocess
import platform
import time
from pathlib import Path

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common.port_config import (
    resolve_port,
    get_port_config,
    save_port_config,
    is_port_available,
    update_configuration,
)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="端口管理工具")
    parser.add_argument("--check", action="store_true", help="检查端口配置")
    parser.add_argument("--update", action="store_true", help="更新端口配置")
    parser.add_argument("--kill", action="store_true", help="终止占用端口的进程")
    parser.add_argument(
        "--list-running", action="store_true", help="列出正在运行的邮件服务器"
    )
    parser.add_argument("--test", action="store_true", help="测试端口连接")
    parser.add_argument("--host", default="localhost", help="主机名")

    # 端口设置
    parser.add_argument("--smtp-port", type=int, help="设置SMTP端口")
    parser.add_argument("--smtp-ssl-port", type=int, help="设置SMTP SSL端口")
    parser.add_argument("--pop3-port", type=int, help="设置POP3端口")
    parser.add_argument("--pop3-ssl-port", type=int, help="设置POP3 SSL端口")
    return parser.parse_args()


def find_process_by_port(port):
    """
    查找占用指定端口的进程

    Args:
        port: 端口号

    Returns:
        进程ID，如果没有找到则返回None
    """
    system = platform.system()

    try:
        if system == "Windows":
            # Windows使用netstat命令
            cmd = f"netstat -ano | findstr :{port}"
            output = subprocess.check_output(cmd, shell=True).decode()

            if output:
                for line in output.split("\n"):
                    if "LISTENING" in line:
                        parts = line.strip().split()
                        pid = parts[-1]
                        return pid
        elif system == "Linux" or system == "Darwin":  # Linux或MacOS
            # Linux/MacOS使用lsof命令
            cmd = f"lsof -i :{port} -t"
            output = subprocess.check_output(cmd, shell=True).decode()

            if output:
                return output.strip()
    except Exception as e:
        print(f"查找进程时出错: {e}")

    return None


def kill_process(pid):
    """
    终止指定进程

    Args:
        pid: 进程ID

    Returns:
        如果成功终止返回True，否则返回False
    """
    system = platform.system()

    try:
        if system == "Windows":
            subprocess.check_call(f"taskkill /F /PID {pid}", shell=True)
        else:
            subprocess.check_call(f"kill -9 {pid}", shell=True)
        return True
    except Exception as e:
        print(f"终止进程时出错: {e}")
        return False


def list_running_servers():
    """
    列出正在运行的邮件服务器

    Returns:
        运行中的邮件服务器字典，键为服务类型，值为端口号
    """
    config = get_port_config()
    running_servers = {}

    # 检查配置的服务是否在运行
    for service, port in config.items():
        if not isinstance(port, int):
            continue

        if not is_port_available("localhost", port):
            pid = find_process_by_port(port)
            running_servers[service] = {"port": port, "pid": pid}

    return running_servers


def check_port_configuration(host="localhost"):
    """
    检查端口配置

    Args:
        host: 主机名

    Returns:
        端口配置检查结果字典
    """
    # 获取当前配置
    config = get_port_config()

    # 检查结果
    result = {}

    # 检查每个服务端口
    for service_name, port in config.items():
        # 排除非端口配置
        if not isinstance(port, int):
            continue

        # 检查端口是否可用
        available = is_port_available(host, port)

        # 获取占用端口的进程ID
        pid = None if available else find_process_by_port(port)

        result[service_name] = {"port": port, "available": available, "pid": pid}

    return result


def test_port_connection(host, port, timeout=2, test_bind=False):
    """
    测试端口连接

    Args:
        host: 主机名
        port: 端口号
        timeout: 超时时间（秒）
        test_bind: 是否测试端口绑定而非连接

    Returns:
        (成功与否, 连接结果, 响应数据)
    """
    if test_bind:
        # 先检查是否有服务在监听这个端口
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()

            # 如果能连接成功，说明有服务在监听
            if result == 0:
                try:
                    # 尝试再次连接以获取服务响应数据
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(timeout)
                    sock.connect((host, port))
                    data = sock.recv(1024)
                    sock.close()
                    return False, "端口已被占用，有服务在监听", data
                except:
                    return False, "端口已被占用，有服务在监听但无法获取响应", None

            # 无法连接，可能是系统保留或其他原因
            # 尝试绑定确认是否可用
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.bind((host, port))
                sock.listen(1)
                sock.close()
                # 能成功绑定，说明端口虽然无法连接但实际可用
                return True, "端口可以绑定（未被占用）", None
            except Exception as e:
                # 既无法连接也无法绑定，可能是系统保留的端口
                return False, f"端口无法绑定（系统保留或被占用）: {e}", None
        except Exception as e:
            # 出错时，尝试直接绑定
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.bind((host, port))
                sock.listen(1)
                sock.close()
                # 可以绑定表示端口未被占用
                return True, "端口可以绑定（未被占用）", None
            except Exception as e:
                # 无法绑定表示端口被占用或系统保留
                return False, f"端口无法绑定: {e}", None
    else:
        # 测试端口连接（是否有服务在监听）
        try:
            # 创建套接字
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            # 连接到服务器
            start_time = time.time()
            sock.connect((host, port))
            connect_time = time.time() - start_time

            # 尝试接收数据
            data = sock.recv(1024)

            # 关闭连接
            sock.close()

            return True, f"连接成功 ({connect_time:.3f}s)", data
        except socket.timeout:
            return False, "连接超时", None
        except ConnectionRefusedError:
            return False, "连接被拒绝", None
        except Exception as e:
            return False, f"连接错误: {e}", None


def update_port_config(args):
    """
    根据命令行参数更新端口配置

    Args:
        args: 命令行参数

    Returns:
        更新后的配置
    """
    # 获取当前配置
    config = get_port_config()

    # 更新SMTP端口
    if args.smtp_port is not None:
        if not is_port_available("localhost", args.smtp_port):
            print(f"警告: SMTP端口 {args.smtp_port} 已被占用")
        save_port_config("smtp_port", args.smtp_port)
        print(f"已更新SMTP端口: {args.smtp_port}")

    # 更新SMTP SSL端口
    if args.smtp_ssl_port is not None:
        if not is_port_available("localhost", args.smtp_ssl_port):
            print(f"警告: SMTP SSL端口 {args.smtp_ssl_port} 已被占用")
        save_port_config("smtp_ssl_port", args.smtp_ssl_port)
        print(f"已更新SMTP SSL端口: {args.smtp_ssl_port}")

    # 更新POP3端口
    if args.pop3_port is not None:
        if not is_port_available("localhost", args.pop3_port):
            print(f"警告: POP3端口 {args.pop3_port} 已被占用")
        save_port_config("pop3_port", args.pop3_port)
        print(f"已更新POP3端口: {args.pop3_port}")

    # 更新POP3 SSL端口
    if args.pop3_ssl_port is not None:
        if not is_port_available("localhost", args.pop3_ssl_port):
            print(f"警告: POP3 SSL端口 {args.pop3_ssl_port} 已被占用")
        save_port_config("pop3_ssl_port", args.pop3_ssl_port)
        print(f"已更新POP3 SSL端口: {args.pop3_ssl_port}")

    # 返回更新后的配置
    return get_port_config()


def kill_processes_by_ports(ports, host="localhost"):
    """
    终止占用指定端口的进程

    Args:
        ports: 端口列表
        host: 主机名

    Returns:
        已终止的进程数量
    """
    killed_count = 0

    for port in ports:
        if not is_port_available(host, port):
            pid = find_process_by_port(port)
            if pid:
                print(f"正在终止占用端口 {port} 的进程 (PID: {pid})...")
                if kill_process(pid):
                    print(f"已终止进程 (PID: {pid})")
                    killed_count += 1
                else:
                    print(f"无法终止进程 (PID: {pid})")
            else:
                print(f"无法找到占用端口 {port} 的进程")

    return killed_count


def main():
    """主函数"""
    args = parse_args()
    host = args.host

    # 没有指定操作，默认检查端口配置
    if not any([args.check, args.update, args.kill, args.list_running, args.test]):
        args.check = True

    # 检查端口配置
    if args.check:
        print("\n===== 端口配置检查 =====")
        config = get_port_config()
        print("当前端口配置:")
        for service, port in config.items():
            print(f"  {service}: {port}")

        print("\n端口可用性检查:")
        results = check_port_configuration(host)

        for service, info in results.items():
            status = "可用" if info["available"] else "被占用"
            pid_info = f" (进程ID: {info['pid']})" if info["pid"] else ""
            print(f"  {service}: {info['port']} - {status}{pid_info}")

            # 如果端口被占用，尝试识别服务
            if not info["available"] and info["pid"]:
                # 测试端口连接（检查是否有服务在监听）
                success, message, data = test_port_connection(host, info["port"])
                if success and data:
                    try:
                        data_str = data.decode("utf-8", errors="ignore")
                        if data_str:
                            print(f"    响应: {data_str.strip()}")
                    except:
                        pass

    # 更新端口配置
    if args.update:
        print("\n===== 更新端口配置 =====")

        # 通过命令行参数更新
        if any(
            [args.smtp_port, args.smtp_ssl_port, args.pop3_port, args.pop3_ssl_port]
        ):
            new_config = update_port_config(args)
            print("\n更新后的端口配置:")
            for service, port in new_config.items():
                print(f"  {service}: {port}")
        else:
            # 自动查找可用端口并更新
            print("正在查找可用端口...")
            result = update_configuration(auto_save=True)

            print("\n端口配置结果:")
            for service, info in result.items():
                changed = " (已更改)" if info["changed"] else ""
                print(f"  {service}: {info['port']}{changed} - {info['message']}")

    # 终止占用端口的进程
    if args.kill:
        print("\n===== 终止占用端口的进程 =====")

        # 获取当前配置的端口
        config = get_port_config()
        ports = [port for port in config.values() if isinstance(port, int)]

        # 终止进程
        killed = kill_processes_by_ports(ports, host)
        print(f"\n已终止 {killed} 个进程")

    # 列出正在运行的邮件服务器
    if args.list_running:
        print("\n===== 正在运行的邮件服务器 =====")
        running_servers = list_running_servers()

        if running_servers:
            for service, info in running_servers.items():
                pid_info = f" (进程ID: {info['pid']})" if info["pid"] else ""
                print(f"  {service}: {info['port']}{pid_info}")
        else:
            print("  没有检测到运行中的邮件服务器")

    # 测试端口连接
    if args.test:
        print("\n===== 端口连接测试 =====")
        config = get_port_config()

        for service, port in config.items():
            if not isinstance(port, int):
                continue

            print(f"\n测试 {service} ({host}:{port}):")

            # 测试端口绑定（是否可用）
            print("测试端口绑定（是否可用）...")
            bind_success, bind_message, bind_data = test_port_connection(
                host, port, test_bind=True
            )
            print(f"  绑定测试: {bind_message}")

            # 测试端口连接（是否有服务在监听）
            print("测试端口连接（是否有服务在监听）...")
            connect_success, connect_message, connect_data = test_port_connection(
                host, port
            )
            print(f"  连接测试: {connect_message}")

            if connect_success and connect_data:
                try:
                    data_str = connect_data.decode("utf-8", errors="ignore")
                    if data_str:
                        print(f"  响应: {data_str.strip()}")
                except:
                    print(f"  响应: [无法解码的二进制数据]")

            # 端口状态总结
            if bind_success:
                print("  总结: 端口未被占用，可以用于启动服务")
            elif connect_success:
                print("  总结: 端口已被占用，且有服务在监听")
                # 尝试确定监听服务
                if connect_data:
                    print(
                        "  建议: 确认该端口上运行的是否为所需的服务，如果不是请更换端口"
                    )
                else:
                    print("  建议: 该端口已有服务占用，建议更换端口")
            elif "系统保留" in bind_message:
                print("  总结: 端口被系统保留，但无活动服务")
                print("  建议: 可以尝试使用该端口启动服务，但系统可能会阻止某些操作")
            else:
                print("  总结: 端口状态异常，可能被占用但没有服务正常响应")
                print("  建议: 建议使用非标准端口，或者尝试fix_ports.py --kill释放端口")


if __name__ == "__main__":
    main()
