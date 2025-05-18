#!/usr/bin/env python
"""
示例：接收邮件

此脚本演示如何使用邮件客户端接收邮件。
"""

import sys
import os
import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging
from common.config import EMAIL_STORAGE_DIR
from client.pop3_client import POP3Client

# 设置日志
logger = setup_logging("example_receive")

def main():
    """主函数"""
    # 获取邮箱账号信息
    print("请输入邮箱账号信息:")
    username = input("用户名: ")
    password = input("密码或授权码: ")
    
    # 创建POP3客户端
    pop3_client = POP3Client(
        host="pop.qq.com",  # 使用QQ邮箱，可以根据需要修改
        port=995,           # QQ邮箱SSL端口
        use_ssl=True,       # 使用SSL加密
        username=username,
        password=password,
        auth_method="AUTO"  # 自动选择认证方法
    )
    
    # 接收邮件
    try:
        print("正在连接到POP3服务器...")
        pop3_client.connect()
        
        # 获取邮箱状态
        status = pop3_client.get_mailbox_status()
        print(f"邮箱状态: {status[0]}封邮件, {status[1]}字节")
        
        # 获取邮件列表
        email_list = pop3_client.list_emails()
        print(f"邮箱中有{len(email_list)}封邮件")
        
        if not email_list:
            print("邮箱中没有邮件")
            return
        
        # 询问用户要下载多少封邮件
        try:
            num_emails = int(input(f"请输入要下载的邮件数量 (最多{len(email_list)}封): "))
            num_emails = min(num_emails, len(email_list))
        except ValueError:
            print("输入无效，默认下载最新的5封邮件")
            num_emails = min(5, len(email_list))
        
        # 获取最新的N封邮件
        latest_emails = email_list[-num_emails:]
        
        print(f"正在下载{len(latest_emails)}封邮件...")
        for i, (msg_num, msg_size) in enumerate(latest_emails):
            print(f"正在下载第{i+1}封邮件 (编号: {msg_num}, 大小: {msg_size}字节)...")
            email = pop3_client.retrieve_email(msg_num, delete=False)
            
            if email:
                print(f"  主题: {email.subject}")
                print(f"  发件人: {email.from_addr.name} <{email.from_addr.address}>")
                print(f"  日期: {email.date}")
                print(f"  附件数量: {len(email.attachments)}")
                
                # 保存邮件
                filepath = pop3_client.save_email_as_eml(email, EMAIL_STORAGE_DIR)
                print(f"  已保存到: {filepath}")
                
                # 如果有附件，询问是否保存
                if email.attachments:
                    save_attachments = input("  是否保存附件? (y/n): ").lower() == 'y'
                    if save_attachments:
                        # 创建附件保存目录
                        attachments_dir = os.path.join(EMAIL_STORAGE_DIR, "attachments")
                        os.makedirs(attachments_dir, exist_ok=True)
                        
                        # 保存附件
                        for j, attachment in enumerate(email.attachments):
                            attachment_path = os.path.join(attachments_dir, attachment.filename)
                            
                            # 检查文件是否已存在
                            if os.path.exists(attachment_path):
                                base, ext = os.path.splitext(attachment.filename)
                                attachment_path = os.path.join(attachments_dir, f"{base}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{ext}")
                            
                            # 保存附件
                            with open(attachment_path, "wb") as f:
                                f.write(attachment.content)
                            
                            print(f"    附件{j+1}: {attachment.filename} 已保存到 {attachment_path}")
            else:
                print(f"  无法获取邮件 {msg_num}")
        
        print(f"\n已成功下载{len(latest_emails)}封邮件")
    except Exception as e:
        print(f"接收邮件时出错: {e}")
    finally:
        # 断开连接
        pop3_client.disconnect()
        print("已断开与POP3服务器的连接")

if __name__ == "__main__":
    main()
