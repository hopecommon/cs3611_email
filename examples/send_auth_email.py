"""
向认证SMTP服务器发送测试邮件
"""

import os
import sys
import smtplib
import ssl
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.port_config import get_service_port

# 设置日志
logger = setup_logging("send_auth_email")


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


def send_email(
    host, port, sender, recipients, msg, username=None, password=None, use_ssl=True
):
    """发送邮件"""
    try:
        if use_ssl:
            # 创建SSL上下文
            context = ssl.create_default_context()
            # 禁用证书验证（仅用于测试自签名证书）
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            # 使用SSL连接
            with smtplib.SMTP_SSL(host, port, context=context) as client:
                client.set_debuglevel(1)  # 启用调试输出

                # 如果提供了用户名和密码，则进行认证
                if username and password:
                    client.login(username, password)

                # 发送邮件
                client.sendmail(sender, recipients, msg.as_string())
                print(f"邮件已成功发送到 {', '.join(recipients)}")
        else:
            # 使用普通连接
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

    parser = argparse.ArgumentParser(description="发送认证测试邮件")
    parser.add_argument("--host", default="localhost", help="SMTP服务器主机名")
    parser.add_argument("--port", type=int, default=8025, help="SMTP服务器端口")
    parser.add_argument("--sender", default="sender@example.com", help="发件人地址")
    parser.add_argument(
        "--recipient", default="recipient@example.com", help="收件人地址"
    )
    parser.add_argument("--subject", default="认证测试邮件", help="邮件主题")
    parser.add_argument("--content", default="这是一封认证测试邮件", help="邮件内容")
    parser.add_argument("--html", action="store_true", help="发送HTML邮件")
    parser.add_argument("--username", default="testuser", help="认证用户名")
    parser.add_argument("--password", default="testpass", help="认证密码")
    parser.add_argument("--ssl", action="store_true", help="使用SSL连接")
    parser.add_argument(
        "--no-ssl", dest="ssl", action="store_false", help="不使用SSL连接"
    )
    parser.set_defaults(ssl=True)  # 默认使用SSL
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
            <p>这是一封<strong>HTML格式</strong>的认证测试邮件。</p>
        </body>
        </html>
        """
        msg = create_html_email(
            args.sender, args.recipient, args.subject, args.content, html_content
        )
    else:
        msg = create_simple_email(
            args.sender, args.recipient, args.subject, args.content
        )

    # 从配置文件获取实际端口
    if args.ssl:
        # 优先使用配置文件中的端口，如果不存在则使用命令行参数
        port = get_service_port("smtp_ssl_port", args.port)
    else:
        port = get_service_port("smtp_port", args.port)

    print(f"从配置获取的端口: {port}")

    # 发送邮件
    send_email(
        args.host,
        port,
        args.sender,
        [args.recipient],
        msg,
        args.username,
        args.password,
        args.ssl,
    )


if __name__ == "__main__":
    main()
