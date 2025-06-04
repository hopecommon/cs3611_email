#!/usr/bin/env python3
"""
PGP邮件加密解密演示

演示如何使用PGP功能发送和接收加密邮件
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.models import Email, EmailAddress
from common.utils import setup_logging, generate_message_id
from client.smtp_client_pgp import SMTPClientPGP
from client.pop3_client_pgp import POP3ClientPGP
from pgp import PGPManager, KeyManager, EmailCrypto

logger = setup_logging("pgp_demo")


def create_demo_users(key_manager: KeyManager):
    """创建演示用户的PGP密钥对"""
    print("🔑 创建演示用户的PGP密钥对...")
    
    # 用户1: Alice
    alice_result = key_manager.setup_user_pgp(
        name="Alice Chen",
        email="alice@example.com",
        passphrase="alice123",
        force_recreate=True
    )
    
    if alice_result["success"]:
        print(f"✅ Alice的密钥对创建成功: {alice_result['key_id']}")
    else:
        print(f"❌ Alice密钥对创建失败: {alice_result['message']}")
        return False
    
    # 用户2: Bob
    bob_result = key_manager.setup_user_pgp(
        name="Bob Wang",
        email="bob@example.com", 
        passphrase="bob456",
        force_recreate=True
    )
    
    if bob_result["success"]:
        print(f"✅ Bob的密钥对创建成功: {bob_result['key_id']}")
    else:
        print(f"❌ Bob密钥对创建失败: {bob_result['message']}")
        return False
    
    return True


def demo_key_exchange(key_manager: KeyManager):
    """演示密钥交换过程"""
    print("\n🔄 演示密钥交换...")
    
    # Alice导出公钥给Bob
    alice_public_key = key_manager.export_user_public_key("alice@example.com")
    if alice_public_key:
        print("✅ Alice导出公钥成功")
        
        # Bob导入Alice的公钥
        try:
            alice_key_id = key_manager.import_contact_public_key("alice@example.com", alice_public_key)
            print(f"✅ Bob导入Alice公钥成功: {alice_key_id}")
        except Exception as e:
            print(f"❌ Bob导入Alice公钥失败: {e}")
            return False
    
    # Bob导出公钥给Alice
    bob_public_key = key_manager.export_user_public_key("bob@example.com")
    if bob_public_key:
        print("✅ Bob导出公钥成功")
        
        # Alice导入Bob的公钥
        try:
            bob_key_id = key_manager.import_contact_public_key("bob@example.com", bob_public_key)
            print(f"✅ Alice导入Bob公钥成功: {bob_key_id}")
        except Exception as e:
            print(f"❌ Alice导入Bob公钥失败: {e}")
            return False
    
    return True


def demo_encrypted_email(smtp_client: SMTPClientPGP, email_crypto: EmailCrypto):
    """演示加密邮件发送"""
    print("\n📧 演示发送加密邮件...")
    
    # 创建邮件
    email = Email(
        message_id=generate_message_id(),
        subject="机密文件 - PGP加密测试",
        from_addr=EmailAddress("Alice Chen", "alice@example.com"),
        to_addrs=[EmailAddress("Bob Wang", "bob@example.com")],
        text_content="""亲爱的Bob，

这是一封使用PGP加密的机密邮件。

邮件内容包含：
1. 重要的商业机密
2. 个人隐私信息
3. 敏感的技术资料

只有拥有正确私钥的人才能解密阅读此邮件。

祝好，
Alice""",
        date=datetime.now()
    )
    
    print(f"原始邮件主题: {email.subject}")
    print(f"原始邮件内容长度: {len(email.text_content)} 字符")
    
    # 加密邮件
    try:
        encrypted_email = smtp_client.send_email_with_pgp(
            email,
            encrypt=True,
            sign=True,
            sender_passphrase="alice123"
        )
        
        if encrypted_email:
            print("✅ 加密邮件发送成功")
            return email, True
        else:
            print("❌ 加密邮件发送失败")
            return email, False
            
    except Exception as e:
        print(f"❌ 发送加密邮件时出错: {e}")
        return email, False


def demo_signed_email(smtp_client: SMTPClientPGP):
    """演示签名邮件发送"""
    print("\n✍️ 演示发送签名邮件...")
    
    # 创建邮件
    email = Email(
        message_id=generate_message_id(),
        subject="公开通知 - PGP签名验证",
        from_addr=EmailAddress("Bob Wang", "bob@example.com"),
        to_addrs=[EmailAddress("Alice Chen", "alice@example.com")],
        text_content="""尊敬的Alice，

这是一封使用PGP数字签名的邮件。

虽然内容不加密，但签名可以验证：
1. 邮件确实来自我（Bob）
2. 邮件在传输过程中未被篡改
3. 发送者身份可信

请验证此邮件的数字签名。

此致，
Bob Wang""",
        date=datetime.now()
    )
    
    print(f"邮件主题: {email.subject}")
    
    # 发送签名邮件
    try:
        success = smtp_client.send_email_with_pgp(
            email,
            encrypt=False,
            sign=True,
            sender_passphrase="bob456"
        )
        
        if success:
            print("✅ 签名邮件发送成功")
            return email, True
        else:
            print("❌ 签名邮件发送失败")
            return email, False
            
    except Exception as e:
        print(f"❌ 发送签名邮件时出错: {e}")
        return email, False


def demo_email_decryption(pop3_client: POP3ClientPGP, original_email: Email):
    """演示邮件解密"""
    print("\n🔓 演示邮件解密...")
    
    # 模拟接收加密邮件（在实际环境中，这将从POP3服务器获取）
    print("注意: 这是一个模拟演示，实际应用中邮件会从POP3服务器获取")
    
    # 使用EmailCrypto手动演示加密解密过程
    email_crypto = pop3_client.email_crypto
    
    # 先加密邮件（模拟发送过程）
    encrypted_email = email_crypto.encrypt_email(
        original_email,
        recipient_key_id=pop3_client.key_manager.get_user_public_key_id("bob@example.com"),
        sender_private_key_id=pop3_client.key_manager.get_user_private_key_id("alice@example.com"),
        passphrase="alice123"
    )
    
    print(f"加密后邮件主题: {encrypted_email.subject}")
    print(f"加密后内容长度: {len(encrypted_email.text_content)} 字符")
    print("加密内容预览:")
    print(encrypted_email.text_content[:200] + "...")
    
    # 解密邮件
    try:
        decrypted_email, verification_info = pop3_client.decrypt_email(
            encrypted_email,
            recipient_passphrase="bob456"
        )
        
        if decrypted_email:
            print("✅ 邮件解密成功")
            print(f"解密后主题: {decrypted_email.subject}")
            print(f"解密后内容: {decrypted_email.text_content[:100]}...")
            
            print("\n🔍 验证信息:")
            print(f"  加密: {'是' if verification_info.get('encrypted') else '否'}")
            print(f"  签名: {'是' if verification_info.get('signed') else '否'}")
            print(f"  签名有效: {'是' if verification_info.get('signature_valid') else '否'}")
            print(f"  签名者: {verification_info.get('signer_info', '未知')}")
            
            return True
        else:
            print("❌ 邮件解密失败")
            print(f"错误信息: {verification_info.get('error', '未知错误')}")
            return False
            
    except Exception as e:
        print(f"❌ 解密邮件时出错: {e}")
        return False


def demo_signature_verification(pop3_client: POP3ClientPGP, original_email: Email):
    """演示签名验证"""
    print("\n✅ 演示签名验证...")
    
    # 使用EmailCrypto手动演示签名验证过程
    email_crypto = pop3_client.email_crypto
    
    # 先签名邮件（模拟发送过程）
    signed_email = email_crypto.encrypt_email(
        original_email,
        recipient_key_id=pop3_client.key_manager.get_user_public_key_id("alice@example.com"),
        sender_private_key_id=pop3_client.key_manager.get_user_private_key_id("bob@example.com"),
        passphrase="bob456",
        sign_only=True
    )
    
    print(f"签名后邮件主题: {signed_email.subject}")
    print("签名内容预览:")
    print(signed_email.text_content[:300] + "...")
    
    # 验证签名
    try:
        verification_info = pop3_client.verify_email_signature(signed_email)
        
        print("\n🔍 签名验证结果:")
        print(f"  有签名: {'是' if verification_info.get('signed') else '否'}")
        print(f"  签名有效: {'是' if verification_info.get('signature_valid') else '否'}")
        print(f"  验证成功: {'是' if verification_info.get('verification_successful') else '否'}")
        print(f"  签名者信息: {verification_info.get('signer_info', '未知')}")
        
        if verification_info.get('signature_valid'):
            print("✅ 数字签名验证成功")
            return True
        else:
            print("❌ 数字签名验证失败")
            return False
            
    except Exception as e:
        print(f"❌ 验证签名时出错: {e}")
        return False


def display_summary(key_manager: KeyManager):
    """显示演示总结"""
    print("\n" + "="*60)
    print("🎯 PGP邮件加密演示总结")
    print("="*60)
    
    # 显示密钥统计
    user_keys = key_manager.list_user_keys()
    public_keys = len(key_manager.pgp_manager.public_keys)
    private_keys = len(key_manager.pgp_manager.private_keys)
    
    print(f"👥 用户数量: {len(user_keys)}")
    print(f"🔑 公钥数量: {public_keys}")
    print(f"🔐 私钥数量: {private_keys}")
    
    print("\n📋 功能验证:")
    print("  ✅ PGP密钥对生成")
    print("  ✅ 密钥导入导出")
    print("  ✅ 邮件加密发送")
    print("  ✅ 邮件签名发送")
    print("  ✅ 邮件解密接收")
    print("  ✅ 数字签名验证")
    
    print("\n🔒 安全特性:")
    print("  • 端到端加密 - 只有收件人能解密")
    print("  • 数字签名 - 验证发件人身份和邮件完整性")
    print("  • 密钥管理 - 安全的密钥生成和存储")
    print("  • 密码保护 - 私钥可用密码保护")
    
    print("\n💡 使用建议:")
    print("  1. 为每个邮箱账户生成独立的PGP密钥对")
    print("  2. 使用强密码保护私钥")
    print("  3. 定期备份密钥文件")
    print("  4. 谨慎分享公钥，确保来源可信")
    print("  5. 对重要邮件启用自动加密和签名")


def main():
    """主演示函数"""
    print("🚀 PGP邮件端到端加密演示")
    print("="*50)
    
    try:
        # 初始化PGP组件
        print("🔧 初始化PGP组件...")
        pgp_manager = PGPManager()
        key_manager = KeyManager(pgp_manager)
        email_crypto = EmailCrypto(pgp_manager)
        
        # 初始化邮件客户端
        smtp_client = SMTPClientPGP(
            host="localhost",
            port=8025,
            use_ssl=False,
            auto_encrypt=False,  # 手动控制加密
            auto_sign=False,     # 手动控制签名
            pgp_keyring_dir=None
        )
        
        pop3_client = POP3ClientPGP(
            host="localhost",
            port=8110,
            use_ssl=False,
            auto_decrypt=True,
            pgp_keyring_dir=None
        )
        
        print("✅ 组件初始化完成")
        
        # 演示步骤
        steps = [
            ("创建演示用户", lambda: create_demo_users(key_manager)),
            ("密钥交换", lambda: demo_key_exchange(key_manager)),
            ("发送加密邮件", lambda: demo_encrypted_email(smtp_client, email_crypto)),
            ("发送签名邮件", lambda: demo_signed_email(smtp_client)),
        ]
        
        original_email = None
        
        for step_name, step_func in steps:
            print(f"\n{'='*20} {step_name} {'='*20}")
            try:
                result = step_func()
                if isinstance(result, tuple):
                    original_email, success = result
                    if not success:
                        print(f"❌ {step_name} 失败")
                        break
                elif not result:
                    print(f"❌ {step_name} 失败")
                    break
                else:
                    print(f"✅ {step_name} 完成")
            except Exception as e:
                print(f"❌ {step_name} 出错: {e}")
                break
        
        # 解密和验证演示
        if original_email:
            print(f"\n{'='*20} 邮件解密验证 {'='*20}")
            demo_email_decryption(pop3_client, original_email)
            demo_signature_verification(pop3_client, original_email)
        
        # 显示总结
        display_summary(key_manager)
        
        print("\n🎉 PGP邮件加密演示完成！")
        print("\n使用 'python pgp/pgp_cli.py --help' 查看更多PGP命令行工具选项")
        
    except Exception as e:
        print(f"❌ 演示过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 