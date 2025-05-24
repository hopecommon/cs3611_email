# -*- coding: utf-8 -*-
"""
POP3邮件接收示例脚本

本脚本演示如何使用客户端模块接收和处理邮件：
- 连接POP3服务器
- 获取邮箱状态
- 接收单个邮件
- 批量接收邮件
- 过滤邮件
- 保存邮件为.eml文件

使用前请修改配置部分的邮箱设置。
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from client.pop3_client_refactored import POP3Client
from common.utils import setup_logging
from common.config import EMAIL_STORAGE_DIR

# 设置日志
logger = setup_logging("pop3_example", verbose=True)

# ==================== 配置部分 ====================
# 请根据您的邮箱服务商修改以下配置

# POP3服务器配置
POP3_CONFIG = {
    "host": "pop.qq.com",  # QQ邮箱POP3服务器
    "port": 110,  # 非SSL端口
    "ssl_port": 995,  # SSL端口
    "use_ssl": True,  # 是否使用SSL
    "username": "your@qq.com",  # 请替换为您的邮箱地址
    "password": "your_auth_code",  # 请替换为您的授权码（不是QQ密码）
    "auth_method": "AUTO",  # 认证方法: AUTO, BASIC, APOP
    "timeout": 120,  # 连接超时时间（秒）
    "max_retries": 3,  # 最大重试次数
}

# 邮件存储配置
STORAGE_CONFIG = {
    "inbox_dir": os.path.join(EMAIL_STORAGE_DIR, "inbox"),
    "max_emails": 10,  # 最多接收的邮件数量
    "save_as_eml": True,  # 是否保存为.eml文件
}


def create_pop3_client():
    """
    创建并配置POP3客户端

    Returns:
        POP3Client: 配置好的POP3客户端实例
    """
    try:
        client = POP3Client(
            host=POP3_CONFIG["host"],
            port=(
                POP3_CONFIG["ssl_port"]
                if POP3_CONFIG["use_ssl"]
                else POP3_CONFIG["port"]
            ),
            use_ssl=POP3_CONFIG["use_ssl"],
            username=POP3_CONFIG["username"],
            password=POP3_CONFIG["password"],
            auth_method=POP3_CONFIG["auth_method"],
            timeout=POP3_CONFIG["timeout"],
            max_retries=POP3_CONFIG["max_retries"],
        )
        logger.info("POP3客户端创建成功")
        return client
    except Exception as e:
        logger.error(f"创建POP3客户端失败: {e}")
        raise


def get_mailbox_status():
    """
    获取邮箱状态示例
    """
    print("\n=== 获取邮箱状态 ===")

    try:
        # 创建POP3客户端
        pop3_client = create_pop3_client()

        # 连接到服务器
        pop3_client.connect()

        # 获取邮箱状态
        msg_count, mailbox_size = pop3_client.get_mailbox_status()

        print(f"邮箱状态:")
        print(f"  邮件数量: {msg_count} 封")
        print(f"  邮箱大小: {mailbox_size} 字节 ({mailbox_size/1024:.2f} KB)")

        # 列出邮件
        email_list = pop3_client.list_emails()
        print(f"\n邮件列表:")
        print("编号\t大小(字节)")
        print("-" * 20)
        for msg_num, size in email_list[:5]:  # 只显示前5封
            print(f"{msg_num}\t{size}")

        if len(email_list) > 5:
            print(f"... 还有 {len(email_list) - 5} 封邮件")

        # 断开连接
        pop3_client.disconnect()

    except Exception as e:
        logger.error(f"获取邮箱状态失败: {e}")
        print(f"获取状态失败: {e}")


def receive_single_email():
    """
    接收单个邮件示例
    """
    print("\n=== 接收单个邮件 ===")

    try:
        # 创建POP3客户端
        pop3_client = create_pop3_client()

        # 连接到服务器
        pop3_client.connect()

        # 获取邮件列表
        email_list = pop3_client.list_emails()

        if not email_list:
            print("邮箱中没有邮件")
            pop3_client.disconnect()
            return

        # 获取最新的邮件（最后一封）
        latest_msg_num = email_list[-1][0]
        print(f"正在获取邮件 #{latest_msg_num}...")

        # 接收邮件（不删除）
        email = pop3_client.retrieve_email(latest_msg_num, delete=False)

        if email:
            print(f"\n邮件信息:")
            print(f"  主题: {email.subject}")
            print(f"  发件人: {email.from_addr.name} <{email.from_addr.address}>")
            print(f"  收件人: {', '.join([addr.address for addr in email.to_addrs])}")
            print(f"  日期: {email.date}")
            print(f"  附件数量: {len(email.attachments)}")

            # 显示邮件内容预览
            if email.text_content:
                preview = email.text_content[:200]
                if len(email.text_content) > 200:
                    preview += "..."
                print(f"  内容预览: {preview}")
            elif email.html_content:
                print(f"  内容类型: HTML邮件")

            # 保存邮件为.eml文件
            if STORAGE_CONFIG["save_as_eml"]:
                os.makedirs(STORAGE_CONFIG["inbox_dir"], exist_ok=True)
                eml_path = pop3_client.save_email_as_eml(
                    email, STORAGE_CONFIG["inbox_dir"]
                )
                print(f"  已保存为: {eml_path}")
        else:
            print("获取邮件失败")

        # 断开连接
        pop3_client.disconnect()

    except Exception as e:
        logger.error(f"接收单个邮件失败: {e}")
        print(f"接收失败: {e}")


def receive_batch_emails():
    """
    批量接收邮件示例
    """
    print("\n=== 批量接收邮件 ===")

    try:
        # 创建POP3客户端
        pop3_client = create_pop3_client()

        # 连接到服务器
        pop3_client.connect()

        # 批量获取邮件（限制数量）
        print(f"正在获取最多 {STORAGE_CONFIG['max_emails']} 封邮件...")
        emails = pop3_client.retrieve_all_emails(
            delete=False, limit=STORAGE_CONFIG["max_emails"]  # 不删除邮件
        )

        if emails:
            print(f"\n成功获取 {len(emails)} 封邮件:")

            # 确保存储目录存在
            os.makedirs(STORAGE_CONFIG["inbox_dir"], exist_ok=True)

            for i, email in enumerate(emails, 1):
                print(f"\n邮件 {i}:")
                print(f"  主题: {email.subject}")
                print(f"  发件人: {email.from_addr.address}")
                print(f"  日期: {email.date}")

                # 保存邮件
                if STORAGE_CONFIG["save_as_eml"]:
                    try:
                        eml_path = pop3_client.save_email_as_eml(
                            email, STORAGE_CONFIG["inbox_dir"]
                        )
                        print(f"  已保存: {os.path.basename(eml_path)}")
                    except Exception as save_err:
                        print(f"  保存失败: {save_err}")
        else:
            print("没有获取到邮件")

        # 断开连接
        pop3_client.disconnect()

    except Exception as e:
        logger.error(f"批量接收邮件失败: {e}")
        print(f"批量接收失败: {e}")


def receive_filtered_emails():
    """
    过滤邮件接收示例
    """
    print("\n=== 过滤邮件接收 ===")

    try:
        # 创建POP3客户端
        pop3_client = create_pop3_client()

        # 连接到服务器
        pop3_client.connect()

        # 设置过滤条件
        since_date = datetime.now() - timedelta(days=7)  # 最近7天的邮件

        print(f"过滤条件:")
        print(f"  日期: {since_date.strftime('%Y-%m-%d')} 之后")
        print(f"  主题包含: '测试'")

        # 获取过滤后的邮件
        emails = pop3_client.retrieve_all_emails(
            delete=False,
            limit=STORAGE_CONFIG["max_emails"],
            since_date=since_date,
            subject_contains="测试",  # 主题包含"测试"的邮件
        )

        if emails:
            print(f"\n找到 {len(emails)} 封符合条件的邮件:")

            for i, email in enumerate(emails, 1):
                print(f"\n邮件 {i}:")
                print(f"  主题: {email.subject}")
                print(f"  发件人: {email.from_addr.address}")
                print(f"  日期: {email.date}")

                # 检查是否包含附件
                if email.attachments:
                    print(f"  附件: {len(email.attachments)} 个")
                    for j, attachment in enumerate(email.attachments, 1):
                        print(
                            f"    {j}. {attachment.filename} ({attachment.size} 字节)"
                        )
        else:
            print("没有找到符合条件的邮件")

        # 断开连接
        pop3_client.disconnect()

    except Exception as e:
        logger.error(f"过滤邮件接收失败: {e}")
        print(f"过滤接收失败: {e}")


def demonstrate_email_processing():
    """
    邮件处理功能演示
    """
    print("\n=== 邮件处理演示 ===")

    try:
        # 创建POP3客户端
        pop3_client = create_pop3_client()

        # 连接到服务器
        pop3_client.connect()

        # 获取一封邮件进行详细处理
        emails = pop3_client.retrieve_all_emails(limit=1)

        if emails:
            email = emails[0]
            print(f"处理邮件: {email.subject}")

            # 详细信息
            print(f"\n详细信息:")
            print(f"  Message-ID: {email.message_id}")
            print(f"  优先级: {email.priority}")
            print(f"  状态: {email.status}")
            print(f"  是否已读: {email.is_read}")

            # 处理抄送和密送
            if email.cc_addrs:
                print(f"  抄送: {', '.join([addr.address for addr in email.cc_addrs])}")
            if email.bcc_addrs:
                print(
                    f"  密送: {', '.join([addr.address for addr in email.bcc_addrs])}"
                )

            # 处理附件
            if email.attachments:
                print(f"\n附件处理:")
                attachment_dir = Path(STORAGE_CONFIG["inbox_dir"]) / "attachments"
                attachment_dir.mkdir(exist_ok=True)

                for i, attachment in enumerate(email.attachments, 1):
                    print(f"  附件 {i}: {attachment.filename}")
                    print(f"    类型: {attachment.content_type}")
                    print(f"    大小: {attachment.size} 字节")

                    # 保存附件
                    try:
                        from client.mime_handler import MIMEHandler

                        saved_path = MIMEHandler.decode_attachment(
                            attachment, str(attachment_dir)
                        )
                        print(f"    已保存: {saved_path}")
                    except Exception as e:
                        print(f"    保存失败: {e}")

            # 内容分析
            print(f"\n内容分析:")
            if email.text_content:
                word_count = len(email.text_content.split())
                print(f"  纯文本: {len(email.text_content)} 字符, {word_count} 词")
            if email.html_content:
                print(f"  HTML内容: {len(email.html_content)} 字符")
        else:
            print("没有邮件可处理")

        # 断开连接
        pop3_client.disconnect()

    except Exception as e:
        logger.error(f"邮件处理演示失败: {e}")
        print(f"处理演示失败: {e}")


def main():
    """
    主函数 - 演示各种邮件接收功能
    """
    print("POP3邮件接收示例")
    print("================")
    print("注意: 请先修改脚本中的邮箱配置信息")
    print()

    # 检查配置
    if POP3_CONFIG["username"] == "your@qq.com":
        print("警告: 请先修改POP3_CONFIG中的邮箱配置！")
        print("需要修改: username, password")
        return

    try:
        # 1. 获取邮箱状态
        get_mailbox_status()

        # 2. 接收单个邮件
        receive_single_email()

        # 3. 批量接收邮件
        receive_batch_emails()

        # 4. 过滤邮件接收
        receive_filtered_emails()

        # 5. 邮件处理演示
        demonstrate_email_processing()

        print("\n所有示例执行完成！")
        print(f"邮件保存目录: {STORAGE_CONFIG['inbox_dir']}")

    except KeyboardInterrupt:
        print("\n用户中断执行")
    except Exception as e:
        logger.error(f"示例执行失败: {e}")
        print(f"执行失败: {e}")


if __name__ == "__main__":
    main()
