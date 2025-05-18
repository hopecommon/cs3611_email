#!/usr/bin/env python
"""
示例：发送带附件的邮件

此脚本演示如何使用邮件客户端发送一封带附件的邮件。
"""

import sys
import os
import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.models import Email, EmailAddress, Attachment, EmailStatus
from client.smtp_client import SMTPClient

# 设置日志
logger = setup_logging("example_send_attachment")

def main():
    """主函数"""
    # 获取邮箱账号信息
    print("请输入邮箱账号信息:")
    username = input("用户名: ")
    password = input("密码或授权码: ")
    recipient = input("收件人: ")
    
    # 获取附件信息
    attachment_path = input("请输入附件路径: ")
    
    # 检查附件是否存在
    if not os.path.exists(attachment_path):
        print(f"错误: 附件文件不存在: {attachment_path}")
        return
    
    # 读取附件内容
    try:
        with open(attachment_path, "rb") as f:
            attachment_content = f.read()
    except Exception as e:
        print(f"读取附件时出错: {e}")
        return
    
    # 获取附件文件名和类型
    attachment_filename = os.path.basename(attachment_path)
    
    # 猜测内容类型
    import mimetypes
    content_type, _ = mimetypes.guess_type(attachment_filename)
    if not content_type:
        content_type = "application/octet-stream"
    
    # 创建附件对象
    attachment = Attachment(
        filename=attachment_filename,
        content_type=content_type,
        content=attachment_content
    )
    
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
        subject=f"测试带附件的邮件 - {attachment_filename}",
        from_addr=EmailAddress(name="发件人", address=username),
        to_addrs=[EmailAddress(name="收件人", address=recipient)],
        text_content=f"这是一封带附件的测试邮件。\n\n附件: {attachment_filename}\n\n祝好，\n发件人",
        attachments=[attachment],
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
