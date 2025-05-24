# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
SMTP邮件发送示例脚本

本脚本演示如何使用客户端模块发送不同类型的邮件：
- 纯文本邮件
- HTML格式邮件
- 带附件的邮件
- 批量发送邮件

使用前请修改配置部分的邮箱设置。
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from client.smtp_client import SMTPClient
from client.mime_handler import MIMEHandler
from common.models import Email, EmailAddress, Attachment, EmailPriority
from common.utils import setup_logging, generate_message_id

# 设置日志
logger = setup_logging("smtp_example", verbose=True)

# ==================== 配置部分 ====================
# 请根据您的邮箱服务商修改以下配置

# SMTP服务器配置
SMTP_CONFIG = {
    "host": "smtp.qq.com",  # QQ邮箱SMTP服务器
    "port": 587,  # 非SSL端口
    "ssl_port": 465,  # SSL端口
    "use_ssl": True,  # 是否使用SSL
    "username": "your@qq.com",  # 请替换为您的邮箱地址
    "password": "your_auth_code",  # 请替换为您的授权码（不是QQ密码）
    "timeout": 30,  # 连接超时时间
    "max_retries": 3,  # 最大重试次数
}

# 邮件配置
EMAIL_CONFIG = {
    "from_name": "发件人姓名",
    "from_addr": "your@qq.com",  # 发件人地址，通常与username相同
    "to_addr": "recipient@example.com",  # 收件人地址
    "to_name": "收件人姓名",
}


def create_smtp_client():
    """
    创建并配置SMTP客户端

    Returns:
        SMTPClient: 配置好的SMTP客户端实例
    """
    try:
        client = SMTPClient(
            host=SMTP_CONFIG["host"],
            port=SMTP_CONFIG["port"],
            use_ssl=SMTP_CONFIG["use_ssl"],
            username=SMTP_CONFIG["username"],
            password=SMTP_CONFIG["password"],
            timeout=SMTP_CONFIG["timeout"],
            max_retries=SMTP_CONFIG["max_retries"],
        )
        logger.info("SMTP客户端创建成功")
        return client
    except Exception as e:
        logger.error(f"创建SMTP客户端失败: {e}")
        raise


def send_text_email():
    """
    发送纯文本邮件示例
    """
    print("\n=== 发送纯文本邮件 ===")

    try:
        # 创建SMTP客户端
        smtp_client = create_smtp_client()

        # 创建邮件对象
        email = Email(
            message_id=generate_message_id(),
            subject="纯文本邮件测试",
            from_addr=EmailAddress(
                name=EMAIL_CONFIG["from_name"], address=EMAIL_CONFIG["from_addr"]
            ),
            to_addrs=[
                EmailAddress(
                    name=EMAIL_CONFIG["to_name"], address=EMAIL_CONFIG["to_addr"]
                )
            ],
            text_content="这是一封纯文本测试邮件。\n\n发送时间: " + str(datetime.now()),
            date=datetime.now(),
            priority=EmailPriority.NORMAL,
        )

        # 连接并发送邮件
        smtp_client.connect()
        success = smtp_client.send_email(email)
        smtp_client.disconnect()

        if success:
            print("纯文本邮件发送成功！")
        else:
            print("纯文本邮件发送失败！")

    except Exception as e:
        logger.error(f"发送纯文本邮件失败: {e}")
        print(f"发送失败: {e}")


def send_html_email():
    """
    发送HTML格式邮件示例
    """
    print("\n=== 发送HTML邮件 ===")

    try:
        # 创建SMTP客户端
        smtp_client = create_smtp_client()

        # HTML内容
        html_content = """
        <html>
        <head>
            <meta charset="utf-8">
            <title>HTML邮件测试</title>
        </head>
        <body>
            <h1 style="color: #2E86AB;">HTML邮件测试</h1>
            <p>这是一封<strong>HTML格式</strong>的测试邮件。</p>
            <ul>
                <li>支持<em>富文本格式</em></li>
                <li>支持<span style="color: red;">彩色文字</span></li>
                <li>支持链接: <a href="https://www.example.com">示例链接</a></li>
            </ul>
            <p>发送时间: {}</p>
        </body>
        </html>
        """.format(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        # 创建邮件对象
        email = Email(
            message_id=generate_message_id(),
            subject="HTML邮件测试",
            from_addr=EmailAddress(
                name=EMAIL_CONFIG["from_name"], address=EMAIL_CONFIG["from_addr"]
            ),
            to_addrs=[
                EmailAddress(
                    name=EMAIL_CONFIG["to_name"], address=EMAIL_CONFIG["to_addr"]
                )
            ],
            html_content=html_content,
            text_content="这是HTML邮件的纯文本版本。",  # 备用纯文本内容
            date=datetime.now(),
            priority=EmailPriority.NORMAL,
        )

        # 连接并发送邮件
        smtp_client.connect()
        success = smtp_client.send_email(email)
        smtp_client.disconnect()

        if success:
            print("HTML邮件发送成功！")
        else:
            print("HTML邮件发送失败！")

    except Exception as e:
        logger.error(f"发送HTML邮件失败: {e}")
        print(f"发送失败: {e}")


def send_email_with_attachments():
    """
    发送带附件的邮件示例
    """
    print("\n=== 发送带附件的邮件 ===")

    try:
        # 创建SMTP客户端
        smtp_client = create_smtp_client()

        # 创建示例附件文件
        attachment_dir = Path("examples/temp_attachments")
        attachment_dir.mkdir(exist_ok=True)

        # 创建文本附件
        text_file = attachment_dir / "sample.txt"
        with open(text_file, "w", encoding="utf-8") as f:
            f.write("这是一个示例文本附件。\n")
            f.write("创建时间: " + str(datetime.now()))

        # 使用MIME处理器编码附件
        attachments = []
        if text_file.exists():
            attachment = MIMEHandler.encode_attachment(str(text_file))
            attachments.append(attachment)
            print(f"已添加附件: {attachment.filename}")

        # 创建邮件对象
        email = Email(
            message_id=generate_message_id(),
            subject="带附件的邮件测试",
            from_addr=EmailAddress(
                name=EMAIL_CONFIG["from_name"], address=EMAIL_CONFIG["from_addr"]
            ),
            to_addrs=[
                EmailAddress(
                    name=EMAIL_CONFIG["to_name"], address=EMAIL_CONFIG["to_addr"]
                )
            ],
            text_content="这是一封带附件的测试邮件。\n\n请查看附件内容。",
            attachments=attachments,
            date=datetime.now(),
            priority=EmailPriority.HIGH,
        )

        # 连接并发送邮件
        smtp_client.connect()
        success = smtp_client.send_email(email)
        smtp_client.disconnect()

        if success:
            print("带附件的邮件发送成功！")
        else:
            print("带附件的邮件发送失败！")

        # 清理临时文件
        if text_file.exists():
            text_file.unlink()
        if attachment_dir.exists() and not any(attachment_dir.iterdir()):
            attachment_dir.rmdir()

    except Exception as e:
        logger.error(f"发送带附件邮件失败: {e}")
        print(f"发送失败: {e}")


def send_batch_emails():
    """
    批量发送邮件示例
    """
    print("\n=== 批量发送邮件 ===")

    try:
        # 创建SMTP客户端
        smtp_client = create_smtp_client()

        # 收件人列表
        recipients = [
            {"name": "收件人1", "email": "recipient1@example.com"},
            {"name": "收件人2", "email": "recipient2@example.com"},
            # 可以添加更多收件人
        ]

        # 连接到SMTP服务器（复用连接）
        smtp_client.connect()

        success_count = 0
        total_count = len(recipients)

        for i, recipient in enumerate(recipients, 1):
            try:
                # 为每个收件人创建个性化邮件
                email = Email(
                    message_id=generate_message_id(),
                    subject=f"批量邮件测试 - 第{i}封",
                    from_addr=EmailAddress(
                        name=EMAIL_CONFIG["from_name"],
                        address=EMAIL_CONFIG["from_addr"],
                    ),
                    to_addrs=[
                        EmailAddress(name=recipient["name"], address=recipient["email"])
                    ],
                    text_content=f"亲爱的 {recipient['name']}，\n\n"
                    f"这是发送给您的第{i}封批量测试邮件。\n\n"
                    f"发送时间: {datetime.now()}",
                    date=datetime.now(),
                    priority=EmailPriority.NORMAL,
                )

                # 发送邮件
                success = smtp_client.send_email(email)
                if success:
                    success_count += 1
                    print(f"邮件 {i}/{total_count} 发送成功 -> {recipient['email']}")
                else:
                    print(f"邮件 {i}/{total_count} 发送失败 -> {recipient['email']}")

            except Exception as e:
                logger.error(f"发送邮件给 {recipient['email']} 失败: {e}")
                print(f"邮件 {i}/{total_count} 发送失败: {e}")

        # 断开连接
        smtp_client.disconnect()

        print(f"\n批量发送完成: {success_count}/{total_count} 封邮件发送成功")

    except Exception as e:
        logger.error(f"批量发送邮件失败: {e}")
        print(f"批量发送失败: {e}")


def main():
    """
    主函数 - 演示各种邮件发送功能
    """
    print("SMTP邮件发送示例")
    print("================")
    print("注意: 请先修改脚本中的邮箱配置信息")
    print()

    # 检查配置
    if SMTP_CONFIG["username"] == "your@qq.com":
        print("警告: 请先修改SMTP_CONFIG中的邮箱配置！")
        print("需要修改: username, password, from_addr, to_addr")
        return

    try:
        # 1. 发送纯文本邮件
        send_text_email()

        # 2. 发送HTML邮件
        send_html_email()

        # 3. 发送带附件的邮件
        send_email_with_attachments()

        # 4. 批量发送邮件（注释掉以避免发送过多测试邮件）
        # send_batch_emails()

        print("\n所有示例执行完成！")

    except KeyboardInterrupt:
        print("\n用户中断执行")
    except Exception as e:
        logger.error(f"示例执行失败: {e}")
        print(f"执行失败: {e}")


if __name__ == "__main__":
    main()
