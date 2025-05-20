#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
POP3客户端示例脚本 - 接收邮件
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from client.pop3_client import POP3Client
from common.utils import setup_logging
from common.port_config import get_service_port

# 设置日志
logger = setup_logging("receive_pop3_email")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="接收POP3邮件")
    parser.add_argument(
        "--host", type=str, default="localhost", help="POP3服务器主机名或IP地址"
    )
    parser.add_argument("--port", type=int, default=110, help="POP3服务器端口")
    parser.add_argument("--ssl-port", type=int, default=995, help="POP3 SSL端口")
    parser.add_argument("--username", type=str, required=True, help="用户名")
    parser.add_argument("--password", type=str, required=True, help="密码")
    parser.add_argument("--ssl", action="store_true", help="是否使用SSL/TLS")
    parser.add_argument(
        "--save-dir", type=str, default="received_emails", help="保存邮件的目录"
    )
    return parser.parse_args()


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()

    # 创建保存目录
    save_dir = Path(args.save_dir)
    save_dir.mkdir(exist_ok=True)

    try:
        # 从配置文件获取实际端口
        if args.ssl:
            # 优先使用配置文件中的端口，如果不存在则使用命令行参数
            primary_port = get_service_port("pop3_ssl_port", args.ssl_port)
            # 备用端口列表
            backup_ports = [995, 8995, 9995]
        else:
            primary_port = get_service_port("pop3_port", args.port)
            # 备用端口列表
            backup_ports = [110, 8110, 8111, 9110]

        # 确保主端口在备用端口列表中
        if primary_port not in backup_ports:
            backup_ports.insert(0, primary_port)

        print(f"主端口: {primary_port}")
        print(f"备用端口: {backup_ports}")

        # 创建POP3客户端
        client = POP3Client(
            host=args.host,
            port=primary_port,
            username=args.username,
            password=args.password,
            use_ssl=args.ssl,
        )

        print(
            f"使用{'SSL' if args.ssl else '非SSL'}连接，尝试连接到端口: {backup_ports}"
        )

        # 连接到服务器
        print(f"正在连接到POP3服务器: {args.host}")
        try:
            # 尝试连接到多个端口
            for port in backup_ports:
                try:
                    client.port = port
                    client.connect()
                    print(f"成功连接到端口: {port}")
                    logger.info(f"成功连接到POP3服务器: {args.host}:{port}")
                    break
                except Exception as e:
                    print(f"连接到端口 {port} 失败: {e}")
                    logger.warning(f"连接到端口 {port} 失败: {e}")

            if not client.connection:
                raise Exception("无法连接到任何端口")

            print("连接成功")
        except Exception as e:
            print(f"连接POP3服务器失败: {e}")
            logger.error(f"连接POP3服务器失败: {e}")
            return 1

        # 获取邮箱状态
        print("正在获取邮箱状态...")
        try:
            count, size = client.get_mailbox_status()
            print(f"邮箱状态: {count}封邮件, {size}字节")
            logger.info(f"邮箱状态: {count}封邮件, {size}字节")
        except Exception as e:
            print(f"获取邮箱状态失败: {e}")
            logger.error(f"获取邮箱状态失败: {e}")
            # 尝试断开连接
            try:
                client.disconnect()
            except:
                pass
            return 1

        # 获取邮件列表
        print("正在获取邮件列表...")
        try:
            messages = client.list_emails()
            print(f"共有 {len(messages)} 封邮件")
            logger.info(f"成功获取邮件列表，共有 {len(messages)} 封邮件")
        except Exception as e:
            print(f"获取邮件列表失败: {e}")
            logger.error(f"获取邮件列表失败: {e}")
            # 尝试断开连接
            try:
                client.disconnect()
            except:
                pass
            return 1

        # 获取每封邮件
        for i, (msg_num, size) in enumerate(messages, 1):
            print(
                f"正在下载邮件 {i}/{len(messages)} (编号: {msg_num}, 大小: {size} 字节)..."
            )
            logger.info(f"开始获取邮件 {msg_num}, 大小: {size} 字节")

            try:
                # 获取邮件
                email_obj = client.retrieve_email(msg_num)

                if email_obj:
                    # 保存邮件
                    save_path = client.save_email_as_eml(email_obj, str(save_dir))
                    print(f"已保存邮件到: {save_path}")
                    logger.info(f"已保存邮件 {msg_num} 到: {save_path}")

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
                    logger.warning(f"获取邮件 {msg_num} 失败，返回了None")
                    print()
            except Exception as e:
                print(f"处理邮件 {msg_num} 时出错: {e}")
                logger.error(f"处理邮件 {msg_num} 时出错: {e}")
                print()

        # 断开连接
        print("正在断开连接...")
        try:
            client.disconnect()
            print("已成功断开连接")
            logger.info("已成功断开与POP3服务器的连接")
        except Exception as e:
            print(f"断开连接时出错: {e}")
            logger.error(f"断开连接时出错: {e}")

    except Exception as e:
        logger.error(f"接收邮件时出错: {e}")
        print(f"错误: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
