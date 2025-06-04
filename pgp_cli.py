#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PGP加密邮件客户端命令行界面 - 主入口文件
提供基于菜单的PGP加密邮件客户端操作界面

包含完整的PGP密钥管理、加密邮件发送和解密邮件接收功能
"""

import sys
import os
import getpass
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common.utils import setup_logging, generate_message_id, is_valid_email
from common.models import Email, EmailAddress
from server.user_auth import UserAuth

# 尝试导入PGP功能
try:
    from pgp import PGPManager, EmailCrypto
    PGP_AVAILABLE = True
except ImportError:
    PGP_AVAILABLE = False

# 设置日志
logger = setup_logging("pgp_cli_main")


class PGPEmailCLI:
    """PGP加密邮件命令行界面"""
    
    def __init__(self):
        """初始化PGP邮件CLI"""
        self.pgp_manager = None
        self.email_crypto = None
        self.current_user = None
        self.smtp_config = {
            "host": "localhost",
            "port": 465,
            "ssl": True,
            "username": "",
            "password": ""
        }
        self.pop3_config = {
            "host": "localhost", 
            "port": 995,
            "ssl": True,
            "username": "",
            "password": ""
        }
        
        if PGP_AVAILABLE:
            self.pgp_manager = PGPManager()
            self.email_crypto = EmailCrypto(self.pgp_manager)
        
        print("🔐 PGP加密邮件客户端已启动")
        if not PGP_AVAILABLE:
            print("⚠️ PGP功能不可用，请安装pgpy库")

    def main_menu(self):
        """主菜单"""
        while True:
            self.print_banner()
            self.print_main_menu()
            
            choice = input("请选择操作 (1-9): ").strip()
            
            if choice == "1":
                self.user_auth_menu()
            elif choice == "2":
                self.pgp_key_menu()
            elif choice == "3":
                self.send_encrypted_email()
            elif choice == "4":
                self.receive_and_decrypt_email()
            elif choice == "5":
                self.pgp_demo()
            elif choice == "6":
                self.smtp_config_menu()
            elif choice == "7":
                self.pop3_config_menu()
            elif choice == "8":
                self.system_status()
            elif choice == "9" or choice.lower() == "q":
                print("👋 感谢使用PGP加密邮件客户端，再见！")
                break
            else:
                print("❌ 无效选择，请重新输入")
            
            input("\n按回车键继续...")

    def print_banner(self):
        """打印横幅"""
        print("\n" + "=" * 70)
        print("🔐 PGP端到端加密邮件客户端")
        print("=" * 70)
        if self.current_user:
            print(f"当前用户: {self.current_user}")
        if PGP_AVAILABLE:
            keys = self.pgp_manager.list_keys()
            print(f"PGP密钥: {len(keys)} 个")
        print("=" * 70)

    def print_main_menu(self):
        """打印主菜单"""
        print("\n📋 主菜单:")
        print("1. 👤 用户认证")
        print("2. 🔑 PGP密钥管理")
        print("3. 📧 发送加密邮件")
        print("4. 📬 接收并解密邮件")
        print("5. 🎯 PGP功能演示")
        print("6. ⚙️ SMTP服务器配置")
        print("7. ⚙️ POP3服务器配置")
        print("8. 📊 系统状态")
        print("9. 🚪 退出")

    def user_auth_menu(self):
        """用户认证菜单"""
        print("\n👤 用户认证")
        print("-" * 30)
        
        if self.current_user:
            print(f"当前用户: {self.current_user}")
            logout = input("是否注销当前用户? (y/N): ").strip().lower()
            if logout == 'y':
                self.current_user = None
                print("✅ 已注销")
            return
        
        print("1. 登录现有用户")
        print("2. 创建新用户")
        print("3. 返回主菜单")
        
        choice = input("请选择 (1-3): ").strip()
        
        if choice == "1":
            self.login_user()
        elif choice == "2":
            self.create_user()
        elif choice == "3":
            return

    def login_user(self):
        """用户登录"""
        print("\n🔐 用户登录")
        
        username = input("用户名: ").strip()
        password = getpass.getpass("密码: ")
        
        try:
            auth = UserAuth()
            user = auth.authenticate(username, password)
            
            if user:
                self.current_user = username
                self.smtp_config["username"] = username
                self.smtp_config["password"] = password
                self.pop3_config["username"] = username
                self.pop3_config["password"] = password
                print(f"✅ 登录成功: {username}")
            else:
                print("❌ 用户名或密码错误")
                
        except Exception as e:
            print(f"❌ 登录失败: {e}")

    def create_user(self):
        """创建新用户"""
        print("\n📝 创建新用户")
        
        username = input("用户名: ").strip()
        email = input("邮箱: ").strip()
        password = getpass.getpass("密码: ")
        full_name = input("全名 (可选): ").strip()
        
        if not is_valid_email(email):
            print("❌ 邮箱格式无效")
            return
        
        try:
            auth = UserAuth()
            user = auth.create_user(username, email, password, full_name)
            
            if user:
                print(f"✅ 用户创建成功: {username}")
                # 自动登录
                self.current_user = username
                self.smtp_config["username"] = username
                self.smtp_config["password"] = password
                self.pop3_config["username"] = username
                self.pop3_config["password"] = password
            else:
                print("❌ 用户创建失败，用户名或邮箱可能已存在")
                
        except Exception as e:
            print(f"❌ 创建用户失败: {e}")

    def pgp_key_menu(self):
        """PGP密钥管理菜单"""
        if not PGP_AVAILABLE:
            print("❌ PGP功能不可用")
            return
        
        print("\n🔑 PGP密钥管理")
        print("-" * 30)
        print("1. 📋 列出所有密钥")
        print("2. 🔑 生成新密钥对")
        print("3. 📤 导出公钥")
        print("4. 📥 导入公钥")
        print("5. 🗑️ 删除密钥")
        print("6. ✅ 测试加密解密")
        print("7. 返回主菜单")
        
        choice = input("请选择 (1-7): ").strip()
        
        if choice == "1":
            self.list_pgp_keys()
        elif choice == "2":
            self.generate_pgp_keys()
        elif choice == "3":
            self.export_public_key()
        elif choice == "4":
            self.import_public_key()
        elif choice == "5":
            self.delete_pgp_key()
        elif choice == "6":
            self.test_pgp_encryption()
        elif choice == "7":
            return

    def list_pgp_keys(self):
        """列出PGP密钥"""
        print("\n📋 PGP密钥列表")
        
        keys = self.pgp_manager.list_keys()
        
        if not keys:
            print("❌ 没有找到任何PGP密钥")
            return
        
        print(f"\n总共 {len(keys)} 个密钥:")
        print("-" * 80)
        print(f"{'类型':<8} {'密钥ID':<20} {'用户信息':<30} {'创建时间':<20}")
        print("-" * 80)
        
        for key_id, key_info in keys.items():
            key_type = key_info['type']
            userids = ', '.join(key_info['userids'][:2])  # 显示前2个用户ID
            if len(userids) > 28:
                userids = userids[:25] + "..."
            created = key_info['created'][:10]  # 只显示日期
            
            print(f"{key_type:<8} {key_id:<20} {userids:<30} {created:<20}")

    def generate_pgp_keys(self):
        """生成PGP密钥对"""
        print("\n🔑 生成PGP密钥对")
        
        name = input("姓名: ").strip()
        email = input("邮箱: ").strip()
        comment = input("备注 (可选): ").strip()
        
        use_passphrase = input("是否使用密码保护私钥? (y/N): ").strip().lower()
        passphrase = None
        if use_passphrase == 'y':
            passphrase = getpass.getpass("私钥密码: ")
        
        if not is_valid_email(email):
            print("❌ 邮箱格式无效")
            return
        
        try:
            print("🔄 正在生成密钥对，请稍候...")
            public_id, private_id = self.pgp_manager.generate_key_pair(
                name=name,
                email=email,
                passphrase=passphrase,
                comment=comment
            )
            
            print(f"✅ 密钥对生成成功!")
            print(f"   公钥ID: {public_id}")
            print(f"   私钥ID: {private_id}")
            print(f"   邮箱: {email}")
            
        except Exception as e:
            print(f"❌ 密钥生成失败: {e}")

    def export_public_key(self):
        """导出公钥"""
        print("\n📤 导出公钥")
        
        # 列出公钥
        keys = self.pgp_manager.list_keys()
        public_keys = {k: v for k, v in keys.items() if v['type'] == 'public'}
        
        if not public_keys:
            print("❌ 没有找到公钥")
            return
        
        print("可用的公钥:")
        for i, (key_id, key_info) in enumerate(public_keys.items(), 1):
            print(f"{i}. {key_id} - {', '.join(key_info['userids'][:2])}")
        
        try:
            choice = int(input("选择要导出的公钥编号: ")) - 1
            key_id = list(public_keys.keys())[choice]
            
            exported_key = self.pgp_manager.export_key(key_id, is_private=False)
            
            filename = input("保存文件名 (回车使用默认): ").strip()
            if not filename:
                filename = f"public_key_{key_id[:8]}.asc"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(exported_key)
            
            print(f"✅ 公钥已导出到: {filename}")
            
        except Exception as e:
            print(f"❌ 导出公钥失败: {e}")

    def import_public_key(self):
        """导入公钥"""
        print("\n📥 导入公钥")
        
        filename = input("公钥文件路径: ").strip()
        
        if not os.path.exists(filename):
            print("❌ 文件不存在")
            return
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                key_data = f.read()
            
            key_id = self.pgp_manager.import_key(key_data, is_private=False)
            print(f"✅ 公钥导入成功: {key_id}")
            
        except Exception as e:
            print(f"❌ 导入公钥失败: {e}")

    def delete_pgp_key(self):
        """删除PGP密钥"""
        print("\n🗑️ 删除PGP密钥")
        
        keys = self.pgp_manager.list_keys()
        if not keys:
            print("❌ 没有找到任何密钥")
            return
        
        print("所有密钥:")
        for i, (key_id, key_info) in enumerate(keys.items(), 1):
            key_type = key_info['type']
            userids = ', '.join(key_info['userids'][:2])
            print(f"{i}. [{key_type}] {key_id} - {userids}")
        
        try:
            choice = int(input("选择要删除的密钥编号: ")) - 1
            key_id = list(keys.keys())[choice]
            key_info = keys[key_id]
            
            confirm = input(f"确认删除密钥 {key_id} [{key_info['type']}]? (y/N): ").strip().lower()
            if confirm == 'y':
                success = self.pgp_manager.delete_key(key_id, key_info['type'])
                if success:
                    print("✅ 密钥已删除")
                else:
                    print("❌ 删除失败")
            else:
                print("取消删除")
                
        except Exception as e:
            print(f"❌ 删除密钥失败: {e}")

    def test_pgp_encryption(self):
        """测试PGP加密解密"""
        print("\n✅ 测试PGP加密解密")
        
        # 选择用于测试的密钥对
        keys = self.pgp_manager.list_keys()
        public_keys = {k: v for k, v in keys.items() if v['type'] == 'public'}
        private_keys = {k: v for k, v in keys.items() if v['type'] == 'private'}
        
        if not public_keys or not private_keys:
            print("❌ 需要至少一对公钥和私钥")
            return
        
        # 选择公钥
        print("选择公钥用于加密:")
        for i, (key_id, key_info) in enumerate(public_keys.items(), 1):
            print(f"{i}. {key_id} - {', '.join(key_info['userids'][:2])}")
        
        try:
            choice = int(input("选择公钥编号: ")) - 1
            public_key_id = list(public_keys.keys())[choice]
            
            # 选择私钥
            print("\n选择私钥用于解密:")
            for i, (key_id, key_info) in enumerate(private_keys.items(), 1):
                print(f"{i}. {key_id} - {', '.join(key_info['userids'][:2])}")
            
            choice = int(input("选择私钥编号: ")) - 1
            private_key_id = list(private_keys.keys())[choice]
            
            # 输入测试消息
            test_message = input("输入测试消息: ").strip()
            if not test_message:
                test_message = "这是一条PGP加密测试消息！🔒"
            
            # 加密
            print("\n🔒 正在加密...")
            encrypted_message = self.pgp_manager.encrypt_message(test_message, public_key_id)
            print(f"✅ 加密完成，密文长度: {len(encrypted_message)} 字符")
            
            # 解密
            print("\n🔓 正在解密...")
            # 检查私钥是否需要密码
            private_key = self.pgp_manager.private_keys.get(private_key_id)
            passphrase = None
            if private_key and private_key.is_protected:
                passphrase = getpass.getpass("私钥密码: ")
            
            decrypted_message = self.pgp_manager.decrypt_message(encrypted_message, private_key_id, passphrase)
            print(f"✅ 解密完成")
            
            # 验证
            if decrypted_message == test_message:
                print("🎉 加密解密测试成功！")
                print(f"原始消息: {test_message}")
                print(f"解密消息: {decrypted_message}")
            else:
                print("❌ 加密解密测试失败，消息不匹配")
                
        except Exception as e:
            print(f"❌ 测试失败: {e}")

    def send_encrypted_email(self):
        """发送加密邮件"""
        if not PGP_AVAILABLE:
            print("❌ PGP功能不可用")
            return
        
        if not self.current_user:
            print("❌ 请先登录用户")
            return
        
        print("\n📧 发送加密邮件")
        print("-" * 30)
        
        # 输入邮件信息
        from_name = input("发件人姓名 (可选): ").strip()
        from_email = input("发件人邮箱: ").strip()
        to_email = input("收件人邮箱: ").strip()
        subject = input("邮件主题: ").strip()
        
        print("邮件正文 (输入完成后按回车，然后输入'END'结束):")
        body_lines = []
        while True:
            line = input()
            if line.strip() == 'END':
                break
            body_lines.append(line)
        body = '\n'.join(body_lines)
        
        if not is_valid_email(from_email) or not is_valid_email(to_email):
            print("❌ 邮箱格式无效")
            return
        
        # 选择收件人公钥
        keys = self.pgp_manager.list_keys()
        recipient_keys = []
        
        for key_id, key_info in keys.items():
            if key_info['type'] == 'public':
                for userid in key_info['userids']:
                    if to_email.lower() in userid.lower():
                        recipient_keys.append((key_id, key_info))
        
        if not recipient_keys:
            print(f"❌ 未找到收件人 {to_email} 的公钥")
            print("是否为收件人生成密钥? (y/N): ", end="")
            if input().strip().lower() == 'y':
                try:
                    pub_id, priv_id = self.pgp_manager.generate_key_pair(
                        name="收件人",
                        email=to_email,
                        passphrase=None
                    )
                    print(f"✅ 已为 {to_email} 生成密钥: {pub_id}")
                    recipient_key_id = pub_id
                except Exception as e:
                    print(f"❌ 生成密钥失败: {e}")
                    return
            else:
                return
        else:
            recipient_key_id = recipient_keys[0][0]
            print(f"✅ 找到收件人公钥: {recipient_key_id}")
        
        try:
            # 创建邮件对象
            email = Email(
                message_id=generate_message_id(),
                subject=subject,
                from_addr=EmailAddress(from_name, from_email),
                to_addrs=[EmailAddress("", to_email)],
                text_content=body,
                date=datetime.now()
            )
            
            # 加密邮件
            print("🔒 正在加密邮件...")
            encrypted_email = self.email_crypto.encrypt_email(
                email,
                recipient_key_id=recipient_key_id
            )
            
            print("📤 正在发送邮件...")
            import smtplib
            import ssl
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.utils import formataddr
            
            class AuthenticatedSMTPClient:
                """带认证的SMTP客户端"""
                
                def __init__(self, host="localhost", port=465, username=None, password=None):
                    self.host = host
                    self.port = port
                    self.username = username
                    self.password = password
                    self.connection = None
                
                def connect(self):
                    """连接并认证"""
                    # 创建不验证证书的SSL上下文（用于本地测试）
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    
                    # 连接SSL SMTP服务器
                    self.connection = smtplib.SMTP_SSL(
                        self.host, 
                        self.port, 
                        context=context,
                        timeout=30
                    )
                    
                    # 如果有认证信息，进行登录
                    if self.username and self.password:
                        self.connection.login(self.username, self.password)
                
                def send_email(self, email):
                    """发送邮件"""
                    if not self.connection:
                        raise Exception("未连接到SMTP服务器")
                    
                    # 构建邮件消息
                    msg = MIMEMultipart()
                    msg['Subject'] = email.subject
                    msg['From'] = formataddr((email.from_addr.name, email.from_addr.address))
                    msg['To'] = ', '.join(formataddr((addr.name, addr.address)) for addr in email.to_addrs)
                    msg['Date'] = email.date.strftime('%a, %d %b %Y %H:%M:%S %z')
                    msg['Message-ID'] = email.message_id
                    
                    # 添加PGP头部
                    if hasattr(email, 'headers') and email.headers:
                        for key, value in email.headers.items():
                            msg[key] = value
                    
                    # 添加邮件正文
                    text_part = MIMEText(email.text_content, 'plain', 'utf-8')
                    msg.attach(text_part)
                    
                    # 发送邮件
                    from_addr = email.from_addr.address
                    to_addrs = [addr.address for addr in email.to_addrs]
                    
                    self.connection.send_message(msg, from_addr, to_addrs)
                
                def disconnect(self):
                    """断开连接"""
                    if self.connection:
                        self.connection.quit()
                        self.connection = None
            
            smtp_client = AuthenticatedSMTPClient(
                host=self.smtp_config["host"],
                port=self.smtp_config["port"],
                username=self.smtp_config["username"],
                password=self.smtp_config["password"]
            )
            
            smtp_client.connect()
            smtp_client.send_email(encrypted_email)
            smtp_client.disconnect()
            
            print("✅ 加密邮件发送成功！")
            print(f"   主题: {encrypted_email.subject}")
            print(f"   收件人: {to_email}")
            if hasattr(encrypted_email, 'headers') and encrypted_email.headers:
                print(f"   加密状态: {encrypted_email.headers.get('X-PGP-Encrypted', '已加密')}")
            else:
                print("   加密状态: 已加密")
                
        except Exception as e:
            print(f"❌ 发送加密邮件失败: {e}")

    def receive_and_decrypt_email(self):
        """接收并解密邮件"""
        if not PGP_AVAILABLE:
            print("❌ PGP功能不可用")
            return
        
        if not self.current_user:
            print("❌ 请先登录用户")
            return
        
        print("\n📬 接收并解密邮件")
        print("-" * 30)
        print("(此功能需要完整的POP3客户端集成)")
        print("请使用 'python -m client.pop3_cli' 接收邮件")

    def pgp_demo(self):
        """PGP功能演示"""
        if not PGP_AVAILABLE:
            print("❌ PGP功能不可用")
            return
        
        print("\n🎯 PGP功能演示")
        print("=" * 40)
        
        print("正在运行完整的PGP演示...")
        
        try:
            # 运行演示脚本
            exec(open("demo_pgp_complete.py").read())
        except FileNotFoundError:
            print("❌ 演示脚本不存在: demo_pgp_complete.py")
        except Exception as e:
            print(f"❌ 演示运行失败: {e}")

    def smtp_config_menu(self):
        """SMTP服务器配置"""
        print("\n⚙️ SMTP服务器配置")
        print("-" * 30)
        print(f"当前配置:")
        print(f"  主机: {self.smtp_config['host']}")
        print(f"  端口: {self.smtp_config['port']}")
        print(f"  SSL: {self.smtp_config['ssl']}")
        print(f"  用户名: {self.smtp_config['username']}")
        
        print("\n1. 修改主机")
        print("2. 修改端口")
        print("3. 切换SSL")
        print("4. 返回主菜单")
        
        choice = input("请选择 (1-4): ").strip()
        
        if choice == "1":
            host = input("新主机地址: ").strip()
            if host:
                self.smtp_config["host"] = host
                print("✅ 主机已更新")
        elif choice == "2":
            try:
                port = int(input("新端口号: "))
                self.smtp_config["port"] = port
                # 自动推断SSL
                if port in [465, 587]:
                    self.smtp_config["ssl"] = True
                    print("✅ 端口已更新，自动启用SSL")
                else:
                    self.smtp_config["ssl"] = False
                    print("✅ 端口已更新，自动禁用SSL")
            except ValueError:
                print("❌ 端口号无效")
        elif choice == "3":
            self.smtp_config["ssl"] = not self.smtp_config["ssl"]
            print(f"✅ SSL已{'启用' if self.smtp_config['ssl'] else '禁用'}")
        elif choice == "4":
            return

    def pop3_config_menu(self):
        """POP3服务器配置"""
        print("\n⚙️ POP3服务器配置")
        print("-" * 30)
        print(f"当前配置:")
        print(f"  主机: {self.pop3_config['host']}")
        print(f"  端口: {self.pop3_config['port']}")
        print(f"  SSL: {self.pop3_config['ssl']}")
        print(f"  用户名: {self.pop3_config['username']}")
        
        print("\n1. 修改主机")
        print("2. 修改端口") 
        print("3. 切换SSL")
        print("4. 返回主菜单")
        
        choice = input("请选择 (1-4): ").strip()
        
        if choice == "1":
            host = input("新主机地址: ").strip()
            if host:
                self.pop3_config["host"] = host
                print("✅ 主机已更新")
        elif choice == "2":
            try:
                port = int(input("新端口号: "))
                self.pop3_config["port"] = port
                # 自动推断SSL
                if port in [995, 993]:
                    self.pop3_config["ssl"] = True
                    print("✅ 端口已更新，自动启用SSL")
                else:
                    self.pop3_config["ssl"] = False
                    print("✅ 端口已更新，自动禁用SSL")
            except ValueError:
                print("❌ 端口号无效")
        elif choice == "3":
            self.pop3_config["ssl"] = not self.pop3_config["ssl"]
            print(f"✅ SSL已{'启用' if self.pop3_config['ssl'] else '禁用'}")
        elif choice == "4":
            return

    def system_status(self):
        """系统状态"""
        print("\n📊 系统状态")
        print("=" * 50)
        
        # PGP状态
        print(f"🔐 PGP功能: {'✅ 可用' if PGP_AVAILABLE else '❌ 不可用'}")
        if PGP_AVAILABLE:
            keys = self.pgp_manager.list_keys()
            public_keys = [k for k, v in keys.items() if v['type'] == 'public']
            private_keys = [k for k, v in keys.items() if v['type'] == 'private']
            print(f"   公钥数量: {len(public_keys)}")
            print(f"   私钥数量: {len(private_keys)}")
            print(f"   密钥目录: {self.pgp_manager.keyring_dir}")
        
        # 用户状态
        print(f"\n👤 当前用户: {self.current_user or '未登录'}")
        
        # 服务器配置
        print(f"\n📤 SMTP配置: {self.smtp_config['host']}:{self.smtp_config['port']} (SSL: {self.smtp_config['ssl']})")
        print(f"📥 POP3配置: {self.pop3_config['host']}:{self.pop3_config['port']} (SSL: {self.pop3_config['ssl']})")
        
        # 测试服务器连接
        print(f"\n🔗 服务器连接测试:")
        try:
            import socket
            
            # 测试SMTP
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((self.smtp_config['host'], self.smtp_config['port']))
            sock.close()
            smtp_status = "✅ 可达" if result == 0 else "❌ 不可达"
            
            # 测试POP3
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((self.pop3_config['host'], self.pop3_config['port']))
            sock.close()
            pop3_status = "✅ 可达" if result == 0 else "❌ 不可达"
            
            print(f"   SMTP: {smtp_status}")
            print(f"   POP3: {pop3_status}")
            
        except Exception as e:
            print(f"   连接测试失败: {e}")


def main():
    """主函数"""
    try:
        print("🚀 启动PGP加密邮件客户端...")
        
        # 创建并启动PGP CLI
        pgp_cli = PGPEmailCLI()
        pgp_cli.main_menu()
        
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，程序退出")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序运行时出错: {e}")
        print(f"❌ 程序运行时出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 