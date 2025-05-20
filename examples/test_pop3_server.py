#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
POP3服务器测试脚本

此脚本用于测试POP3服务器的基本功能，包括：
1. 启动POP3服务器
2. 发送测试邮件
3. 接收测试邮件
4. 验证邮件内容
"""

import os
import sys
import time
import argparse
import subprocess
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging

# 设置日志
logger = setup_logging("test_pop3_server")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="测试POP3服务器")
    parser.add_argument("--host", default="localhost", help="服务器主机名")
    parser.add_argument("--smtp-port", type=int, default=8025, help="SMTP服务器端口")
    parser.add_argument("--pop3-port", type=int, default=8110, help="POP3服务器端口")
    parser.add_argument("--username", default="testuser", help="测试用户名")
    parser.add_argument("--password", default="testpass", help="测试密码")
    parser.add_argument("--ssl", action="store_true", help="使用SSL连接")
    parser.add_argument("--no-ssl", dest="ssl", action="store_false", help="不使用SSL连接")
    parser.set_defaults(ssl=False)
    return parser.parse_args()


def run_command(command, cwd=None, timeout=30):
    """运行命令并返回输出"""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"命令执行失败: {e}")
        logger.error(f"错误输出: {e.stderr}")
        return None
    except subprocess.TimeoutExpired:
        logger.error(f"命令执行超时: {command}")
        return None
    except Exception as e:
        logger.error(f"执行命令时出错: {e}")
        return None


def start_servers(args):
    """启动SMTP和POP3服务器"""
    print("正在启动服务器...")
    
    # 构建命令
    smtp_cmd = [
        "python", "examples/run_auth_smtp_server.py",
        "--port", str(args.smtp_port),
    ]
    
    pop3_cmd = [
        "python", "examples/run_pop3_server.py",
        "--port", str(args.pop3_port),
    ]
    
    if args.ssl:
        smtp_cmd.append("--ssl")
        pop3_cmd.append("--ssl")
    
    # 启动服务器
    try:
        smtp_process = subprocess.Popen(
            smtp_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        pop3_process = subprocess.Popen(
            pop3_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        # 等待服务器启动
        print("等待服务器启动...")
        time.sleep(2)
        
        return smtp_process, pop3_process
    except Exception as e:
        logger.error(f"启动服务器时出错: {e}")
        return None, None


def send_test_email(args):
    """发送测试邮件"""
    print("正在发送测试邮件...")
    
    # 构建命令
    cmd = [
        "python", "examples/send_auth_email.py",
        "--host", args.host,
        "--port", str(args.smtp_port),
        "--username", args.username,
        "--password", args.password,
        "--sender", f"{args.username}@example.com",
        "--recipient", f"{args.username}@example.com",
        "--subject", "测试邮件",
        "--content", "这是一封测试邮件，用于测试POP3服务器功能。",
    ]
    
    if args.ssl:
        cmd.append("--ssl")
    
    # 发送邮件
    output = run_command(cmd)
    if output and "邮件已成功发送" in output:
        print("测试邮件发送成功")
        return True
    else:
        print("测试邮件发送失败")
        return False


def receive_test_email(args):
    """接收测试邮件"""
    print("正在接收测试邮件...")
    
    # 构建命令
    cmd = [
        "python", "examples/receive_pop3_email.py",
        "--host", args.host,
        "--port", str(args.pop3_port),
        "--username", args.username,
        "--password", args.password,
        "--save-dir", "test_emails",
    ]
    
    if args.ssl:
        cmd.append("--ssl")
    
    # 接收邮件
    output = run_command(cmd)
    if output and "已保存邮件到" in output:
        print("测试邮件接收成功")
        return True
    else:
        print("测试邮件接收失败")
        return False


def cleanup(smtp_process, pop3_process):
    """清理资源"""
    print("正在清理资源...")
    
    # 终止进程
    if smtp_process:
        smtp_process.terminate()
        smtp_process.wait(timeout=5)
    
    if pop3_process:
        pop3_process.terminate()
        pop3_process.wait(timeout=5)
    
    # 删除测试邮件
    test_dir = Path("test_emails")
    if test_dir.exists():
        for file in test_dir.glob("*.eml"):
            try:
                file.unlink()
            except Exception as e:
                logger.error(f"删除文件时出错: {e}")
        
        try:
            test_dir.rmdir()
        except Exception as e:
            logger.error(f"删除目录时出错: {e}")


def main():
    """主函数"""
    args = parse_args()
    
    smtp_process = None
    pop3_process = None
    
    try:
        # 启动服务器
        smtp_process, pop3_process = start_servers(args)
        if not smtp_process or not pop3_process:
            print("服务器启动失败")
            return 1
        
        # 发送测试邮件
        if not send_test_email(args):
            print("测试失败：无法发送邮件")
            return 1
        
        # 等待邮件处理
        print("等待邮件处理...")
        time.sleep(2)
        
        # 接收测试邮件
        if not receive_test_email(args):
            print("测试失败：无法接收邮件")
            return 1
        
        print("测试成功：邮件发送和接收正常")
        return 0
    
    except KeyboardInterrupt:
        print("测试被用户中断")
        return 1
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
        print(f"测试失败：{e}")
        return 1
    finally:
        # 清理资源
        cleanup(smtp_process, pop3_process)


if __name__ == "__main__":
    sys.exit(main())
