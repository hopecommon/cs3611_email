#!/usr/bin/env python3
"""
PGP命令行工具

提供PGP密钥管理、邮件加密解密的命令行界面
"""

import argparse
import sys
import os
import getpass
from pathlib import Path
from typing import Optional

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from pgp import PGPManager, KeyManager, EmailCrypto, PGPError
from common.utils import setup_logging
from common.models import Email, EmailAddress

logger = setup_logging("pgp_cli")


def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="PGP端到端加密工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 生成密钥对
  python pgp_cli.py generate --name "张三" --email "zhang@example.com"
  
  # 列出所有密钥
  python pgp_cli.py list
  
  # 导出公钥
  python pgp_cli.py export --email "zhang@example.com" --public
  
  # 导入公钥
  python pgp_cli.py import --file "public.asc"
  
  # 加密消息
  python pgp_cli.py encrypt --recipient "zhang@example.com" --message "hello"
  
  # 解密消息
  python pgp_cli.py decrypt --file "encrypted.asc"
        """
    )
    
    parser.add_argument(
        "--keyring-dir",
        type=str,
        help="PGP密钥环目录路径"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细输出"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # 生成密钥对命令
    generate_parser = subparsers.add_parser("generate", help="生成PGP密钥对")
    generate_parser.add_argument("--name", required=True, help="用户姓名")
    generate_parser.add_argument("--email", required=True, help="用户邮箱")
    generate_parser.add_argument("--comment", default="", help="密钥注释")
    generate_parser.add_argument("--key-size", type=int, default=4096, help="密钥长度")
    generate_parser.add_argument("--no-passphrase", action="store_true", help="不设置私钥密码")
    
    # 列出密钥命令
    list_parser = subparsers.add_parser("list", help="列出密钥")
    list_parser.add_argument("--type", choices=["public", "private", "both"], default="both", help="密钥类型")
    
    # 导入密钥命令
    import_parser = subparsers.add_parser("import", help="导入密钥")
    import_parser.add_argument("--file", required=True, help="密钥文件路径")
    import_parser.add_argument("--email", help="关联的邮箱地址")
    import_parser.add_argument("--private", action="store_true", help="导入私钥")
    
    # 导出密钥命令
    export_parser = subparsers.add_parser("export", help="导出密钥")
    export_parser.add_argument("--email", help="用户邮箱")
    export_parser.add_argument("--key-id", help="密钥ID")
    export_parser.add_argument("--public", action="store_true", help="导出公钥")
    export_parser.add_argument("--private", action="store_true", help="导出私钥")
    export_parser.add_argument("--output", help="输出文件路径")
    
    # 删除密钥命令
    delete_parser = subparsers.add_parser("delete", help="删除密钥")
    delete_parser.add_argument("--email", help="用户邮箱")
    delete_parser.add_argument("--key-id", help="密钥ID")
    delete_parser.add_argument("--type", choices=["public", "private", "both"], default="both", help="要删除的密钥类型")
    delete_parser.add_argument("--force", action="store_true", help="强制删除（不确认）")
    
    # 加密消息命令
    encrypt_parser = subparsers.add_parser("encrypt", help="加密消息")
    encrypt_parser.add_argument("--recipient", required=True, help="接收者邮箱")
    encrypt_parser.add_argument("--message", help="要加密的消息")
    encrypt_parser.add_argument("--file", help="要加密的文件路径")
    encrypt_parser.add_argument("--output", help="输出文件路径")
    encrypt_parser.add_argument("--sign", action="store_true", help="同时签名")
    encrypt_parser.add_argument("--sender", help="发送者邮箱（用于签名）")
    
    # 解密消息命令
    decrypt_parser = subparsers.add_parser("decrypt", help="解密消息")
    decrypt_parser.add_argument("--message", help="要解密的消息")
    decrypt_parser.add_argument("--file", help="要解密的文件路径")
    decrypt_parser.add_argument("--recipient", help="接收者邮箱")
    decrypt_parser.add_argument("--output", help="输出文件路径")
    
    # 签名消息命令
    sign_parser = subparsers.add_parser("sign", help="签名消息")
    sign_parser.add_argument("--message", help="要签名的消息")
    sign_parser.add_argument("--file", help="要签名的文件路径")
    sign_parser.add_argument("--sender", required=True, help="发送者邮箱")
    sign_parser.add_argument("--output", help="输出文件路径")
    
    # 验证签名命令
    verify_parser = subparsers.add_parser("verify", help="验证签名")
    verify_parser.add_argument("--message", help="要验证的签名消息")
    verify_parser.add_argument("--file", help="要验证的签名文件路径")
    verify_parser.add_argument("--sender", help="发送者邮箱")
    
    # 测试命令
    test_parser = subparsers.add_parser("test", help="测试PGP功能")
    test_parser.add_argument("--email", required=True, help="用户邮箱")
    
    return parser


def handle_generate_command(args, key_manager: KeyManager):
    """处理生成密钥对命令"""
    try:
        print(f"为用户 {args.name} <{args.email}> 生成PGP密钥对...")
        
        # 获取密码
        passphrase = None
        if not args.no_passphrase:
            passphrase = getpass.getpass("请输入私钥密码（留空则不设置）: ").strip()
            if passphrase:
                confirm_passphrase = getpass.getpass("请确认私钥密码: ").strip()
                if passphrase != confirm_passphrase:
                    print("❌ 密码不匹配")
                    return False
            else:
                passphrase = None
        
        # 生成密钥对
        key_id = key_manager.create_user_keypair(
            args.name, args.email, passphrase, args.comment, args.key_size
        )
        
        print(f"✅ PGP密钥对生成成功!")
        print(f"   密钥ID: {key_id}")
        print(f"   密钥长度: {args.key_size} bits")
        print(f"   已设置密码: {'是' if passphrase else '否'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 生成密钥对失败: {e}")
        return False


def handle_list_command(args, pgp_manager: PGPManager, key_manager: KeyManager):
    """处理列出密钥命令"""
    try:
        print("PGP密钥列表:")
        print("=" * 80)
        
        keys_info = pgp_manager.list_keys(args.type)
        
        if not keys_info:
            print("没有找到密钥")
            return True
        
        for key_id, info in keys_info.items():
            print(f"密钥ID: {key_id}")
            print(f"类型: {info['type']}")
            print(f"用户ID: {', '.join(info['userids'])}")
            print(f"创建时间: {info['created']}")
            print(f"算法: {info['algorithm']}")
            print(f"密钥长度: {info['key_size']} bits")
            print(f"指纹: {info['fingerprint']}")
            
            if info['type'] == 'private' and 'is_protected' in info:
                print(f"已加密: {'是' if info['is_protected'] else '否'}")
            
            print("-" * 80)
        
        # 显示用户映射
        user_keys = key_manager.list_user_keys()
        if user_keys:
            print("\n用户邮箱映射:")
            print("=" * 80)
            for email, info in user_keys.items():
                print(f"邮箱: {email}")
                print(f"密钥ID: {info['key_id']}")
                print(f"有私钥: {'是' if info['has_private_key'] else '否'}")
                print(f"有公钥: {'是' if info['has_public_key'] else '否'}")
                print("-" * 40)
        
        return True
        
    except Exception as e:
        print(f"❌ 列出密钥失败: {e}")
        return False


def handle_import_command(args, key_manager: KeyManager):
    """处理导入密钥命令"""
    try:
        if not os.path.exists(args.file):
            print(f"❌ 文件不存在: {args.file}")
            return False
        
        with open(args.file, 'r', encoding='utf-8') as f:
            key_data = f.read()
        
        print(f"导入{'私钥' if args.private else '公钥'}从 {args.file}...")
        
        if args.email:
            key_id = key_manager.import_user_key(args.email, key_data, args.private)
        else:
            # 使用PGP管理器直接导入
            key_id = key_manager.pgp_manager.import_key(key_data, args.private)
        
        print(f"✅ 密钥导入成功!")
        print(f"   密钥ID: {key_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入密钥失败: {e}")
        return False


def handle_export_command(args, key_manager: KeyManager):
    """处理导出密钥命令"""
    try:
        if not args.public and not args.private:
            print("❌ 请指定 --public 或 --private")
            return False
        
        key_data = None
        
        if args.email:
            if args.public:
                key_data = key_manager.export_user_public_key(args.email)
            elif args.private:
                key_data = key_manager.export_user_private_key(args.email)
        elif args.key_id:
            key_data = key_manager.pgp_manager.export_key(args.key_id, args.private)
        else:
            print("❌ 请指定 --email 或 --key-id")
            return False
        
        if not key_data:
            print("❌ 未找到指定的密钥")
            return False
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(key_data)
            print(f"✅ 密钥已导出到 {args.output}")
        else:
            print("导出的密钥:")
            print("=" * 80)
            print(key_data)
        
        return True
        
    except Exception as e:
        print(f"❌ 导出密钥失败: {e}")
        return False


def handle_encrypt_command(args, email_crypto: EmailCrypto, key_manager: KeyManager):
    """处理加密消息命令"""
    try:
        # 获取要加密的内容
        if args.message:
            content = args.message
        elif args.file:
            if not os.path.exists(args.file):
                print(f"❌ 文件不存在: {args.file}")
                return False
            with open(args.file, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            print("请输入要加密的消息（Ctrl+D结束）:")
            content = sys.stdin.read()
        
        # 查找接收者公钥
        recipient_key_id = key_manager.get_user_public_key_id(args.recipient)
        if not recipient_key_id:
            print(f"❌ 未找到接收者 {args.recipient} 的公钥")
            return False
        
        # 处理签名
        sender_key_id = None
        passphrase = None
        if args.sign:
            if not args.sender:
                print("❌ 签名需要指定发送者邮箱 --sender")
                return False
            
            sender_key_id = key_manager.get_user_private_key_id(args.sender)
            if not sender_key_id:
                print(f"❌ 未找到发送者 {args.sender} 的私钥")
                return False
            
            # 检查私钥是否需要密码
            private_key = key_manager.pgp_manager.private_keys[sender_key_id]
            if private_key.is_protected:
                passphrase = getpass.getpass("请输入私钥密码: ")
        
        print("正在加密...")
        
        if args.sign:
            encrypted_content = key_manager.pgp_manager.encrypt_and_sign(
                content, recipient_key_id, sender_key_id, passphrase
            )
        else:
            encrypted_content = key_manager.pgp_manager.encrypt_message(
                content, recipient_key_id
            )
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(encrypted_content)
            print(f"✅ 加密内容已保存到 {args.output}")
        else:
            print("加密结果:")
            print("=" * 80)
            print(encrypted_content)
        
        return True
        
    except Exception as e:
        print(f"❌ 加密失败: {e}")
        return False


def handle_decrypt_command(args, key_manager: KeyManager):
    """处理解密消息命令"""
    try:
        # 获取要解密的内容
        if args.message:
            content = args.message
        elif args.file:
            if not os.path.exists(args.file):
                print(f"❌ 文件不存在: {args.file}")
                return False
            with open(args.file, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            print("请输入要解密的消息（Ctrl+D结束）:")
            content = sys.stdin.read()
        
        # 查找私钥
        private_key_id = None
        if args.recipient:
            private_key_id = key_manager.get_user_private_key_id(args.recipient)
        else:
            # 尝试所有私钥
            for email, key_id in key_manager.user_keymap.items():
                if key_id in key_manager.pgp_manager.private_keys:
                    private_key_id = key_id
                    print(f"使用私钥: {email} ({key_id})")
                    break
        
        if not private_key_id:
            print("❌ 未找到可用的私钥")
            return False
        
        # 检查私钥密码
        private_key = key_manager.pgp_manager.private_keys[private_key_id]
        passphrase = None
        if private_key.is_protected:
            passphrase = getpass.getpass("请输入私钥密码: ")
        
        print("正在解密...")
        
        decrypted_content = key_manager.pgp_manager.decrypt_message(
            content, private_key_id, passphrase
        )
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(decrypted_content)
            print(f"✅ 解密内容已保存到 {args.output}")
        else:
            print("解密结果:")
            print("=" * 80)
            print(decrypted_content)
        
        return True
        
    except Exception as e:
        print(f"❌ 解密失败: {e}")
        return False


def handle_test_command(args, key_manager: KeyManager):
    """处理测试命令"""
    try:
        print(f"测试用户 {args.email} 的PGP设置...")
        
        # 验证设置
        validation = key_manager.validate_user_setup(args.email)
        
        print("\n验证结果:")
        print("=" * 40)
        print(f"有密钥对: {'是' if validation['has_keypair'] else '否'}")
        print(f"有私钥: {'是' if validation['has_private_key'] else '否'}")
        print(f"有公钥: {'是' if validation['has_public_key'] else '否'}")
        
        if validation['key_id']:
            print(f"密钥ID: {validation['key_id']}")
        
        if validation['errors']:
            print("\n❌ 错误:")
            for error in validation['errors']:
                print(f"   - {error}")
        
        if validation['warnings']:
            print("\n⚠️  警告:")
            for warning in validation['warnings']:
                print(f"   - {warning}")
        
        # 如果有完整的密钥对，进行加密解密测试
        if validation['has_keypair']:
            print("\n进行加密解密测试...")
            
            test_message = "这是一个PGP测试消息"
            key_id = validation['key_id']
            
            # 检查私钥密码
            private_key = key_manager.pgp_manager.private_keys[key_id]
            passphrase = None
            if private_key.is_protected:
                passphrase = getpass.getpass("请输入私钥密码进行测试: ")
            
            try:
                # 加密测试
                encrypted_msg = key_manager.pgp_manager.encrypt_message(test_message, key_id)
                print("✅ 加密测试成功")
                
                # 解密测试
                decrypted_msg = key_manager.pgp_manager.decrypt_message(
                    encrypted_msg, key_id, passphrase
                )
                
                if decrypted_msg == test_message:
                    print("✅ 解密测试成功")
                    print("✅ PGP功能正常!")
                else:
                    print("❌ 解密测试失败: 内容不匹配")
                    return False
                    
            except Exception as e:
                print(f"❌ 加密解密测试失败: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # 设置日志级别
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # 初始化PGP组件
        pgp_manager = PGPManager(args.keyring_dir)
        key_manager = KeyManager(pgp_manager)
        email_crypto = EmailCrypto(pgp_manager)
        
        # 处理命令
        success = False
        
        if args.command == "generate":
            success = handle_generate_command(args, key_manager)
        elif args.command == "list":
            success = handle_list_command(args, pgp_manager, key_manager)
        elif args.command == "import":
            success = handle_import_command(args, key_manager)
        elif args.command == "export":
            success = handle_export_command(args, key_manager)
        elif args.command == "encrypt":
            success = handle_encrypt_command(args, email_crypto, key_manager)
        elif args.command == "decrypt":
            success = handle_decrypt_command(args, key_manager)
        elif args.command == "test":
            success = handle_test_command(args, key_manager)
        else:
            print(f"❌ 未知命令: {args.command}")
            return 1
        
        return 0 if success else 1
        
    except PGPError as e:
        print(f"❌ PGP错误: {e}")
        return 1
    except Exception as e:
        print(f"❌ 程序错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())