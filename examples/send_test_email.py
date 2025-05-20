"""
向SMTP服务器发送测试邮件
"""

import os
import sys
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging

# 设置日志
logger = setup_logging("send_test_email")


def create_simple_email(sender, recipient, subject, content):
    """创建简单邮件"""
    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    return msg


def create_html_email(sender, recipient, subject, text_content, html_content):
    """创建HTML邮件"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    # 添加文本部分
    part1 = MIMEText(text_content, "plain", "utf-8")
    # 添加HTML部分
    part2 = MIMEText(html_content, "html", "utf-8")

    # 按照顺序添加部分（先文本后HTML）
    msg.attach(part1)
    msg.attach(part2)

    return msg


def send_email(host, port, sender, recipients, msg, username=None, password=None):
    """发送邮件"""
    try:
        with smtplib.SMTP(host, port) as client:
            client.set_debuglevel(1)  # 启用调试输出

            # 如果提供了用户名和密码，则进行认证
            if username and password:
                client.login(username, password)

            # 发送邮件
            client.sendmail(sender, recipients, msg.as_string())
            print(f"邮件已成功发送到 {', '.join(recipients)}")
    except Exception as e:
        print(f"发送邮件失败: {e}")


def main():
    """主函数"""
    # 解析命令行参数
    import argparse

    parser = argparse.ArgumentParser(description="发送测试邮件")
    parser.add_argument("--host", default="localhost", help="SMTP服务器主机名")
    parser.add_argument("--port", type=int, default=8025, help="SMTP服务器端口")
    parser.add_argument("--sender", default="sender@example.com", help="发件人地址")
    parser.add_argument("--recipient", default="recipient@example.com", help="收件人地址")
    parser.add_argument("--subject", default="测试邮件", help="邮件主题")
    parser.add_argument("--content", default="这是一封测试邮件", help="邮件内容")
    parser.add_argument("--html", action="store_true", help="发送HTML邮件")
    parser.add_argument("--username", help="认证用户名")
    parser.add_argument("--password", help="认证密码")
    args = parser.parse_args()

    # 创建邮件
    if args.html:
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h1 {{ color: #0066cc; }}
                p {{ margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h1>{args.subject}</h1>
            <p>{args.content}</p>
            <p>这是一封<strong>HTML格式</strong>的测试邮件。</p>
        </body>
        </html>
        """
        msg = create_html_email(
            args.sender, args.recipient, args.subject, args.content, html_content
        )
    else:
        msg = create_simple_email(args.sender, args.recipient, args.subject, args.content)

    # 发送邮件
    send_email(
        args.host,
        args.port,
        args.sender,
        [args.recipient],
        msg,
        args.username,
        args.password,
    )


if __name__ == "__main__":
    main()
