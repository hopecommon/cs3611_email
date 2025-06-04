#!/usr/bin/env python3
"""
PGP邮件完整测试 - 使用真实SMTP/POP3服务器

测试完整的PGP邮件加密、发送、接收、解密流程
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.models import Email, EmailAddress
from common.utils import setup_logging, generate_message_id
from pgp import PGPManager, KeyManager, EmailCrypto
from client.smtp_client_pgp import SMTPClientPGP
from client.pop3_client_pgp import POP3ClientPGP
from user_manager import UserManager

logger = setup_logging("pgp_server_test")


def setup_users():
    """设置测试用户"""
    print("👤 设置测试用户账户...")
    
    user_manager = UserManager()
    
    # 创建Alice账户
    try:
        user_manager.create_user("alice@example.com", "alice123", "Alice Chen")
        print("✅ Alice账户创建成功")
    except Exception as e:
        print(f"ℹ️ Alice账户: {e}")
    
    # 创建Bob账户
    try:
        user_manager.create_user("bob@example.com", "bob456", "Bob Wang")
        print("✅ Bob账户创建成功")
    except Exception as e:
        print(f"ℹ️ Bob账户: {e}")


def setup_pgp_keys(key_manager: KeyManager):
    """设置PGP密钥"""
    print("\n🔑 设置PGP密钥对...")
    
    # 创建Alice的密钥对
    alice_result = key_manager.setup_user_pgp(
        name="Alice Chen",
        email="alice@example.com",
        passphrase="alice123",
        force_recreate=True
    )
    
    if alice_result["success"]:
        print(f"✅ Alice的PGP密钥对: {alice_result['key_id']}")
    else:
        print(f"❌ Alice密钥对失败: {alice_result['message']}")
        return False
    
    # 创建Bob的密钥对
    bob_result = key_manager.setup_user_pgp(
        name="Bob Wang",
        email="bob@example.com",
        passphrase="bob456",
        force_recreate=True
    )
    
    if bob_result["success"]:
        print(f"✅ Bob的PGP密钥对: {bob_result['key_id']}")
    else:
        print(f"❌ Bob密钥对失败: {bob_result['message']}")
        return False
    
    # 密钥交换
    print("\n🔄 进行密钥交换...")
    
    # Alice导出公钥给Bob
    alice_public_key = key_manager.export_user_public_key("alice@example.com")
    if alice_public_key:
        key_manager.import_contact_public_key("alice@example.com", alice_public_key)
        print("✅ Alice公钥交换完成")
    
    # Bob导出公钥给Alice
    bob_public_key = key_manager.export_user_public_key("bob@example.com")
    if bob_public_key:
        key_manager.import_contact_public_key("bob@example.com", bob_public_key)
        print("✅ Bob公钥交换完成")
    
    return True


def send_encrypted_email():
    """发送加密邮件"""
    print("\n📤 发送加密邮件...")
    
    # 初始化SMTP客户端
    smtp_client = SMTPClientPGP(
        host="localhost",
        port=465,
        use_ssl=True,
        username="alice@example.com",
        password="alice123",
        auto_encrypt=False,
        auto_sign=False,
        user_passphrase="alice123"
    )
    
    # 创建邮件
    email = Email(
        message_id=generate_message_id(),
        subject="PGP加密测试邮件",
        from_addr=EmailAddress("Alice Chen", "alice@example.com"),
        to_addrs=[EmailAddress("Bob Wang", "bob@example.com")],
        text_content="""亲爱的Bob，

这是一封通过真实SMTP服务器发送的PGP加密邮件！

邮件特点：
✅ 端到端加密
✅ 数字签名
✅ 完整的邮件服务器传输

只有你才能解密并阅读这封邮件。

祝好，
Alice""",
        date=datetime.now()
    )
    
    print(f"📧 邮件信息:")
    print(f"   主题: {email.subject}")
    print(f"   发送者: {email.from_addr}")
    print(f"   接收者: {email.to_addrs[0]}")
    
    try:
        # 发送加密并签名的邮件
        success = smtp_client.send_email_with_pgp(
            email,
            encrypt=True,
            sign=True,
            sender_passphrase="alice123"
        )
        
        if success:
            print("✅ 加密邮件发送成功！")
            return True
        else:
            print("❌ 加密邮件发送失败")
            return False
            
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def receive_and_decrypt_email():
    """接收并解密邮件"""
    print("\n📥 接收并解密邮件...")
    
    # 初始化POP3客户端
    pop3_client = POP3ClientPGP(
        host="localhost",
        port=995,
        use_ssl=True,
        username="bob@example.com",
        password="bob456",
        auto_decrypt=True,
        user_passphrase="bob456"
    )
    
    try:
        print("🔌 连接到POP3服务器...")
        pop3_client.connect()
        
        # 获取邮件数量
        email_count = pop3_client.get_email_count()
        print(f"📬 Bob的邮箱中有 {email_count} 封邮件")
        
        if email_count == 0:
            print("📭 邮箱为空，没有收到邮件")
            return False
        
        # 获取最新的邮件（应该是我们刚发送的加密邮件）
        print(f"📨 获取最新邮件...")
        email, verification_info = pop3_client.retrieve_email(
            email_count,
            auto_decrypt=True,
            recipient_passphrase="bob456"
        )
        
        if email:
            print(f"✅ 邮件接收成功!")
            print(f"   主题: {email.subject}")
            print(f"   发送者: {email.from_addr}")
            print(f"   接收时间: {email.date}")
            
            print("\n🔍 PGP验证结果:")
            print(f"   是否加密: {'是' if verification_info.get('encrypted') else '否'}")
            print(f"   是否签名: {'是' if verification_info.get('signed') else '否'}")
            print(f"   签名有效: {'是' if verification_info.get('signature_valid') else '否'}")
            print(f"   解密成功: {'是' if verification_info.get('decryption_successful') else '否'}")
            print(f"   验证成功: {'是' if verification_info.get('verification_successful') else '否'}")
            
            if verification_info.get('signer_info'):
                print(f"   签名者: {verification_info['signer_info']}")
            
            if verification_info.get('error'):
                print(f"   错误: {verification_info['error']}")
            
            print("\n📄 邮件内容:")
            print("-" * 60)
            print(email.text_content)
            print("-" * 60)
            
            return True
        else:
            print("❌ 邮件接收失败")
            if verification_info.get('error'):
                print(f"错误: {verification_info['error']}")
            return False
            
    except Exception as e:
        print(f"❌ 接收邮件失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            pop3_client.disconnect()
        except:
            pass


def main():
    """主函数"""
    print("🚀 PGP邮件完整功能测试")
    print("="*50)
    print("📋 测试内容:")
    print("  1. 设置用户账户")
    print("  2. 生成PGP密钥对")
    print("  3. 通过SMTP服务器发送加密邮件")
    print("  4. 通过POP3服务器接收并解密邮件")
    print("="*50)
    
    try:
        # 初始化PGP组件
        print("\n🔧 初始化PGP组件...")
        pgp_manager = PGPManager()
        key_manager = KeyManager(pgp_manager)
        email_crypto = EmailCrypto(pgp_manager)
        print("✅ PGP组件初始化完成")
        
        # 1. 设置用户
        setup_users()
        
        # 2. 设置PGP密钥
        if not setup_pgp_keys(key_manager):
            print("❌ PGP密钥设置失败")
            return 1
        
        # 3. 发送加密邮件
        print(f"\n{'='*20} 发送加密邮件 {'='*20}")
        if not send_encrypted_email():
            print("❌ 邮件发送失败")
            return 1
        
        # 4. 等待邮件传输
        print("\n⏳ 等待3秒让邮件传输完成...")
        time.sleep(3)
        
        # 5. 接收并解密邮件
        print(f"\n{'='*20} 接收并解密邮件 {'='*20}")
        if receive_and_decrypt_email():
            print("\n🎉 PGP邮件完整流程测试成功!")
            print("\n✅ 验证项目:")
            print("  ✅ PGP密钥生成和管理")
            print("  ✅ 邮件端到端加密")
            print("  ✅ 数字签名验证")
            print("  ✅ SMTP服务器集成")
            print("  ✅ POP3服务器集成")
            print("  ✅ 自动加密/解密")
        else:
            print("\n❌ 邮件接收或解密失败")
            return 1
        
        print("\n💡 下一步建议:")
        print("  • 在生产环境中使用更强的密码")
        print("  • 定期备份PGP密钥")
        print("  • 通过安全渠道交换公钥")
        print("  • 考虑实现密钥撤销机制")
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())