#!/usr/bin/env python
"""
示例：发送HTML邮件

此脚本演示如何使用邮件客户端发送一封HTML格式的邮件。
"""

import sys
import os
import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.models import Email, EmailAddress, EmailStatus
from client.smtp_client import SMTPClient

# 设置日志
logger = setup_logging("example_send_html")

def main():
    """主函数"""
    # 获取邮箱账号信息
    print("请输入邮箱账号信息:")
    username = input("用户名: ")
    password = input("密码或授权码: ")
    recipient = input("收件人: ")
    
    # 创建SMTP客户端
    smtp_client = SMTPClient(
        host="smtp.qq.com",  # 使用QQ邮箱，可以根据需要修改
        port=465,            # QQ邮箱SSL端口
        use_ssl=True,        # 使用SSL加密
        username=username,
        password=password,
        auth_method="AUTO"   # 自动选择认证方法
    )
    
    # HTML内容
    html_content = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; }
            .header { color: #0066cc; font-size: 24px; }
            .content { margin: 20px 0; }
            .footer { color: #666666; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="header">HTML邮件测试</div>
        <div class="content">
            <p>这是一封<strong>HTML格式</strong>的测试邮件。</p>
            <p>HTML邮件支持：</p>
            <ul>
                <li>文本<span style="color: red;">格式化</span></li>
                <li>列表</li>
                <li>表格</li>
                <li>链接: <a href="https://www.example.com">示例链接</a></li>
            </ul>
        </div>
        <div class="footer">
            此邮件由邮件客户端示例脚本发送。
        </div>
    </body>
    </html>
    """
    
    # 创建邮件对象
    email = Email(
        message_id=f"<example.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.{id(smtp_client)}@example.com>",
        subject="测试HTML邮件",
        from_addr=EmailAddress(name="发件人", address=username),
        to_addrs=[EmailAddress(name="收件人", address=recipient)],
        text_content="这是一封HTML格式的测试邮件。如果您的邮件客户端不支持HTML，将显示此纯文本内容。",
        html_content=html_content,
        date=None,  # 自动设置为当前时间
        status=EmailStatus.DRAFT
    )
    
    # 发送邮件
    try:
        print("正在连接到SMTP服务器...")
        smtp_client.connect()
        
        print("正在发送邮件...")
        result = smtp_client.send_email(email)
        
        if result:
            print("邮件发送成功！")
        else:
            print("邮件发送失败！")
    except Exception as e:
        print(f"发送邮件时出错: {e}")
    finally:
        # 断开连接
        smtp_client.disconnect()

if __name__ == "__main__":
    main()
