#!/usr/bin/env python
"""
示例：发送纯文本邮件

此脚本演示如何使用邮件客户端发送一封简单的纯文本邮件。
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
logger = setup_logging("example_send_text")

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
    
    # 创建邮件对象
    email = Email(
        message_id=f"<example.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.{id(smtp_client)}@example.com>",
        subject="测试纯文本邮件",
        from_addr=EmailAddress(name="发件人", address=username),
        to_addrs=[EmailAddress(name="收件人", address=recipient)],
        text_content="这是一封测试纯文本邮件。\n\n这是第二段落。\n\n祝好，\n发件人",
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
