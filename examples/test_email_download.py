#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试邮件下载和保存功能

此脚本用于测试POP3客户端的邮件下载和保存功能，特别是验证邮件是否会被重复下载和保存。
"""

import os
import sys
import time
import argparse
import shutil
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from client.pop3_client import POP3Client
from common.utils import setup_logging
from common.port_config import get_service_port

# 设置日志
logger = setup_logging("test_email_download")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="测试邮件下载和保存功能")
    parser.add_argument("--host", default="localhost", help="POP3服务器主机名")
    parser.add_argument("--port", type=int, default=8110, help="POP3服务器端口")
    parser.add_argument("--username", default="testuser", help="用户名")
    parser.add_argument("--password", default="testpass", help="密码")
    parser.add_argument("--ssl", action="store_true", help="是否使用SSL/TLS")
    parser.add_argument("--ssl-port", type=int, default=995, help="POP3 SSL端口")
    parser.add_argument("--save-dir", default="test_downloads", help="保存目录")
    parser.add_argument("--clean", action="store_true", help="清理保存目录")
    return parser.parse_args()


def download_emails(args):
    """下载邮件"""
    # 创建保存目录
    save_dir = Path(args.save_dir)
    save_dir.mkdir(exist_ok=True)

    # 从配置文件获取实际端口
    if args.ssl:
        # 优先使用配置文件中的端口，如果不存在则使用命令行参数
        port = get_service_port("pop3_ssl_port", args.ssl_port)
    else:
        port = get_service_port("pop3_port", args.port)

    print(f"从配置获取的端口: {port}")

    # 创建POP3客户端
    client = POP3Client(
        host=args.host,
        port=port,
        username=args.username,
        password=args.password,
        use_ssl=args.ssl,
    )

    try:
        # 连接到服务器
        print(f"正在连接到POP3服务器: {args.host}:{port}")
        client.connect()
        print("连接成功")

        # 获取邮件列表
        print("正在获取邮件列表...")
        messages = client.list_emails()
        print(f"共有 {len(messages)} 封邮件")

        # 获取每封邮件
        for i, (msg_num, size) in enumerate(messages, 1):
            print(
                f"正在下载邮件 {i}/{len(messages)} (编号: {msg_num}, 大小: {size} 字节)..."
            )

            # 获取邮件
            email_obj = client.retrieve_email(msg_num)

            if email_obj:
                # 保存邮件
                save_path = client.save_email_as_eml(email_obj, str(save_dir))
                print(f"已保存邮件到: {save_path}")

                # 打印邮件信息
                print(f"邮件 {msg_num} 信息:")
                print(f"  主题: {email_obj.subject}")
                print(
                    f"  发件人: {email_obj.from_addr.name} <{email_obj.from_addr.address}>"
                )
                print(f"  日期: {email_obj.date}")
                print(f"  附件数: {len(email_obj.attachments)}")
                print()
            else:
                print(f"获取邮件 {msg_num} 失败")
                print()

        # 断开连接
        client.disconnect()
        print("已断开连接")

    except Exception as e:
        print(f"下载邮件时出错: {e}")
        logger.error(f"下载邮件时出错: {e}")
        # 尝试断开连接
        try:
            client.disconnect()
        except:
            pass


def check_duplicates(save_dir):
    """检查是否有重复的邮件"""
    save_dir = Path(save_dir)
    if not save_dir.exists():
        print(f"保存目录不存在: {save_dir}")
        return

    # 获取所有.eml文件
    eml_files = list(save_dir.glob("*.eml"))
    print(f"共有 {len(eml_files)} 个.eml文件")

    # 检查文件名是否包含邮件ID
    for eml_file in eml_files:
        print(f"文件: {eml_file.name}")


def main():
    """主函数"""
    args = parse_args()

    # 清理保存目录
    if args.clean and os.path.exists(args.save_dir):
        print(f"正在清理保存目录: {args.save_dir}")
        shutil.rmtree(args.save_dir)

    # 下载邮件
    print("第一次下载邮件...")
    download_emails(args)

    # 检查保存的邮件
    print("\n检查保存的邮件...")
    check_duplicates(args.save_dir)

    # 再次下载邮件
    print("\n第二次下载邮件...")
    download_emails(args)

    # 再次检查保存的邮件
    print("\n再次检查保存的邮件...")
    check_duplicates(args.save_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
