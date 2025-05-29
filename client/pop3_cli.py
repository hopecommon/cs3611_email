"""
POP3命令行接口 - 提供命令行接收邮件的功能
"""

import os
import sys
import argparse
import getpass
from typing import List, Optional
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.config import POP3_SERVER, EMAIL_STORAGE_DIR
from client.pop3_client_refactored import POP3Client
from common.port_config import resolve_port

# 设置日志
logger = setup_logging("pop3_cli")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="POP3客户端命令行工具")

    # 服务器设置
    server_group = parser.add_argument_group("服务器设置")
    server_group.add_argument("--host", type=str, help="POP3服务器主机名")
    server_group.add_argument("--port", type=int, help="POP3服务器端口")
    server_group.add_argument("--ssl", action="store_true", help="使用SSL/TLS")
    server_group.add_argument("--ssl-port", type=int, help="SSL/TLS端口")

    # 认证设置
    auth_group = parser.add_argument_group("认证设置")
    auth_group.add_argument("--username", type=str, required=True, help="认证用户名")
    auth_group.add_argument("--password", type=str, help="认证密码")
    auth_group.add_argument("--ask-password", action="store_true", help="提示输入密码")

    # 操作选项
    action_group = parser.add_argument_group("操作选项")
    action_group.add_argument("--list", action="store_true", help="列出邮件")
    action_group.add_argument("--retrieve", type=int, help="获取指定编号的邮件")
    action_group.add_argument(
        "--retrieve-all", action="store_true", help="获取所有邮件"
    )
    action_group.add_argument("--delete", type=int, help="删除指定编号的邮件")
    action_group.add_argument("--status", action="store_true", help="获取邮箱状态")

    # 其他选项
    parser.add_argument("--save-dir", type=str, help="保存邮件的目录")
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--verbose", action="store_true", help="显示详细信息")
    parser.add_argument(
        "--timeout", type=int, default=120, help="连接超时时间（秒），默认为120秒"
    )
    parser.add_argument(
        "--max-retries", type=int, default=3, help="最大重试次数，默认为3次"
    )

    return parser.parse_args()


def load_config(config_path: str) -> dict:
    """
    从配置文件加载配置

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典
    """
    if not os.path.exists(config_path):
        logger.error(f"配置文件不存在: {config_path}")
        sys.exit(1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        logger.info(f"已加载配置文件: {config_path}")
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        sys.exit(1)


def print_email_list(emails: List[tuple]):
    """
    打印邮件列表

    Args:
        emails: 邮件列表，每项为(邮件编号, 邮件大小)元组
    """
    if not emails:
        print("邮箱为空")
        return

    print(f"共有{len(emails)}封邮件:")
    print("编号\t大小(字节)")
    print("-" * 30)
    for msg_num, size in emails:
        print(f"{msg_num}\t{size}")


def print_email(email, verbose: bool = False):
    """
    打印邮件内容

    Args:
        email: Email对象
        verbose: 是否显示详细信息
    """
    print("=" * 50)
    try:
        print(f"主题: {email.subject or '(无主题)'}")
    except UnicodeEncodeError:
        # 安全地处理无法显示的字符
        print(
            f"主题: {(email.subject or '(无主题)').encode('gbk', errors='replace').decode('gbk')}"
        )

    # 安全地处理发件人信息
    if email.from_addr:
        from_name = email.from_addr.name or ""
        from_address = email.from_addr.address or "unknown@localhost"
        if from_name:
            print(f"发件人: {from_name} <{from_address}>")
        else:
            print(f"发件人: {from_address}")
    else:
        print("发件人: (未知发件人)")

    # 安全地处理收件人信息
    if email.to_addrs:
        to_list = []
        for addr in email.to_addrs:
            if addr:
                addr_name = addr.name or ""
                addr_address = addr.address or ""
                if addr_name:
                    to_list.append(f"{addr_name} <{addr_address}>")
                else:
                    to_list.append(addr_address)
        print(f"收件人: {', '.join(to_list) if to_list else '(未知收件人)'}")
    else:
        print("收件人: (未知收件人)")

    # 安全地处理抄送信息
    if email.cc_addrs:
        cc_list = []
        for addr in email.cc_addrs:
            if addr:
                addr_name = addr.name or ""
                addr_address = addr.address or ""
                if addr_name:
                    cc_list.append(f"{addr_name} <{addr_address}>")
                else:
                    cc_list.append(addr_address)
        if cc_list:
            print(f"抄送: {', '.join(cc_list)}")

    print(f"日期: {email.date or '(未知日期)'}")

    if email.attachments:
        print(f"附件: {len(email.attachments)}个")
        for i, attachment in enumerate(email.attachments, 1):
            try:
                print(
                    f"  {i}. {attachment.filename} ({attachment.content_type}, {attachment.size}字节)"
                )
            except UnicodeEncodeError:
                print(
                    f"  {i}. {attachment.filename.encode('gbk', errors='replace').decode('gbk')} ({attachment.content_type}, {attachment.size}字节)"
                )

    print("-" * 50)
    if email.text_content:
        if verbose:
            print(email.text_content)
        else:
            # 只显示前几行
            lines = email.text_content.split("\n")
            preview = "\n".join(lines[:10])
            if len(lines) > 10:
                preview += "\n...(更多内容)"
            print(preview)
    elif email.html_content:
        print("(HTML内容，请使用--verbose查看完整内容)")
        if verbose:
            print(email.html_content)
    print("=" * 50)


def main():
    """主函数"""
    args = parse_args()
    setup_logging("pop3_cli", verbose=args.verbose)

    # 加载配置
    config = {}
    if args.config:
        config = load_config(args.config)

    # 获取POP3设置，确保命令行参数具有最高优先级
    pop3_config = config.get("pop3", {})

    # 主机配置：命令行 > 配置文件 > 默认值
    host = args.host or pop3_config.get("host") or POP3_SERVER["host"]

    # SSL配置：需要特殊处理以确保命令行优先级
    # 如果用户明确指定了--ssl，使用该设置
    # 如果用户没有指定--ssl，但指定了端口，根据端口判断是否应该使用SSL
    if args.ssl:
        # 用户明确要求SSL
        use_ssl = True
    elif args.port is not None:
        # 用户指定了端口但没有指定SSL，根据端口推断
        # 标准SSL端口(995, 465等)使用SSL，其他端口不使用SSL
        standard_ssl_ports = {995, 465, 993, 587}  # 常见SSL端口
        use_ssl = args.port in standard_ssl_ports
    else:
        # 用户既没有指定SSL也没有指定端口，使用配置文件或默认值
        use_ssl = pop3_config.get("use_ssl") or POP3_SERVER["use_ssl"]

    # 端口配置：命令行参数具有绝对最高优先级
    cmd_port = args.port if args.port is not None else None
    cmd_ssl_port = args.ssl_port if args.ssl_port is not None else None

    # 根据是否使用SSL选择要解析的端口
    if use_ssl:
        # SSL模式：优先使用用户指定的端口，否则使用SSL端口解析逻辑
        if cmd_port is not None:
            # 用户明确指定了端口，直接使用（即使是非标准SSL端口）
            port = cmd_port
            port_source = "命令行指定端口"
        else:
            # 用户没有指定端口，使用SSL端口解析
            port, changed, message = resolve_port(
                "pop3", cmd_ssl_port, use_ssl=True, auto_detect=False, is_client=True
            )
            port_source = message
    else:
        # 非SSL模式：优先使用用户指定的端口
        if cmd_port is not None:
            # 用户明确指定了端口，直接使用
            port = cmd_port
            port_source = "命令行指定端口"
        else:
            # 用户没有指定端口，使用非SSL端口解析
            port, changed, message = resolve_port(
                "pop3", cmd_port, use_ssl=False, auto_detect=False, is_client=True
            )
            port_source = message

    if port == 0:
        print(f"错误: 无效端口配置")
        sys.exit(1)

    # 显示最终使用的配置（便于用户确认）
    print(
        f"连接配置: {host}:{port} (SSL: {'启用' if use_ssl else '禁用'}) - {port_source}"
    )

    # 获取认证信息
    username = args.username or pop3_config.get("username")
    password = args.password or pop3_config.get("password")

    if args.ask_password or not password:
        password = getpass.getpass("请输入POP3密码: ")

    # 获取保存目录
    save_dir = (
        args.save_dir
        or config.get("save_dir")
        or os.path.join(EMAIL_STORAGE_DIR, "inbox")
    )
    os.makedirs(save_dir, exist_ok=True)

    # 创建POP3客户端
    pop3_client = POP3Client(
        host=host,
        port=port,
        use_ssl=use_ssl,
        username=username,
        password=password,
        timeout=args.timeout,
        max_retries=args.max_retries,
    )

    try:
        # 连接到服务器
        print(f"正在连接到POP3服务器: {host}:{port}")
        pop3_client.connect()

        # 执行操作
        if args.status:
            # 获取邮箱状态
            msg_count, mailbox_size = pop3_client.get_mailbox_status()
            print(f"邮箱状态: {msg_count}封邮件, {mailbox_size}字节")

        elif args.list:
            # 列出邮件
            emails = pop3_client.list_emails()
            print_email_list(emails)

        elif args.retrieve is not None:
            # 获取指定邮件
            msg_num = args.retrieve
            print(f"正在获取邮件 #{msg_num}...")
            email = pop3_client.retrieve_email(msg_num)

            if email:
                print_email(email, args.verbose)

                # 保存邮件
                eml_path = pop3_client.save_email_as_eml(email, save_dir)
                print(f"邮件已保存为: {eml_path}")
            else:
                print(f"获取邮件 #{msg_num} 失败")

        elif args.retrieve_all:
            # 获取所有邮件
            print("正在获取所有邮件...")
            try:
                emails = pop3_client.retrieve_all_emails()

                if emails:
                    print(f"\n已成功获取{len(emails)}封邮件")

                    success_count = 0
                    error_count = 0

                    for i, email in enumerate(emails, 1):
                        try:
                            print(f"\n邮件 {i}/{len(emails)}:")
                            print_email(email, args.verbose)

                            # 只保存邮件文件，不操作数据库（避免与POP3服务器冲突）
                            try:
                                eml_path = pop3_client.save_email_as_eml(
                                    email, save_dir
                                )
                                print(f"邮件已保存为: {eml_path}")
                                success_count += 1

                            except Exception as save_err:
                                logger.error(f"保存邮件失败: {save_err}")
                                print(f"保存邮件失败: {save_err}")
                                error_count += 1
                        except Exception as e:
                            logger.error(f"处理邮件 {i} 时出错: {e}")
                            print(f"处理邮件 {i} 时出错: {e}")
                            error_count += 1
                            continue

                    # 显示最终统计信息
                    print(f"\n处理完成!")
                    print(f"成功保存: {success_count} 封邮件")
                    if error_count > 0:
                        print(f"保存失败: {error_count} 封邮件")

                    print(f"\n💡 提示: 邮件已保存为文件，数据库记录由POP3服务器管理")
                else:
                    print("没有邮件可获取或获取过程中出现错误")
            except Exception as e:
                logger.error(f"获取所有邮件失败: {e}")
                print(f"获取所有邮件失败: {e}")
                import traceback

                logger.error(f"异常详情: {traceback.format_exc()}")

        elif args.delete is not None:
            # 删除指定邮件
            msg_num = args.delete
            print(f"正在删除邮件 #{msg_num}...")
            # 这里我们先获取邮件，然后再删除，以便用户确认
            email = pop3_client.retrieve_email(msg_num, delete=True)

            if email:
                print(f"已删除邮件: {email.subject}")
            else:
                print(f"删除邮件 #{msg_num} 失败")

        else:
            print(
                "未指定操作，请使用--list, --retrieve, --retrieve-all, --delete或--status"
            )

    except Exception as e:
        logger.error(f"操作失败: {e}")
        print(f"操作失败: {e}")
        if "connection refused" in str(e).lower():
            print(f"连接被拒绝，请检查服务器 {host}:{port} 是否正在运行")
            print("建议运行 python check_ports.py --check 检查端口配置")
        elif "authentication failed" in str(e).lower():
            print("认证失败，请检查用户名和密码是否正确")
        import traceback

        logger.debug(f"错误详情: {traceback.format_exc()}")
    finally:
        # 断开连接
        pop3_client.disconnect()


if __name__ == "__main__":
    main()
