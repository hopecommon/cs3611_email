# -*- coding: utf-8 -*-
"""
安全功能示例脚本

本脚本演示如何使用安全模块的各种功能：
- SSL/TLS连接配置
- 认证字符串生成和验证
- 数据加密和解密
- 密码哈希和验证
- 安全套接字管理

注意：本示例主要用于演示功能，实际使用时请根据具体需求调整。
"""

import os
import sys
import ssl
import socket
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from client.security import SecurityManager
from client.socket_utils import safe_socket, close_socket_safely, close_ssl_connection_safely
from common.utils import setup_logging
from common.config import SSL_CERT_FILE, SSL_KEY_FILE

# 设置日志
logger = setup_logging("security_example", verbose=True)

# ==================== 配置部分 ====================

# SSL证书配置（用于演示）
SSL_CONFIG = {
    "cert_file": SSL_CERT_FILE,
    "key_file": SSL_KEY_FILE,
    "verify_mode": ssl.CERT_NONE,  # 演示用，实际使用时应该验证证书
    "check_hostname": False        # 演示用，实际使用时应该检查主机名
}

# 测试服务器配置
TEST_SERVERS = {
    "smtp_ssl": {"host": "smtp.qq.com", "port": 465},
    "pop3_ssl": {"host": "pop3.qq.com", "port": 995},
    "imap_ssl": {"host": "imap.qq.com", "port": 993}
}

def demonstrate_ssl_context_creation():
    """
    演示SSL上下文创建功能
    """
    print("=== SSL上下文创建演示 ===")
    
    try:
        # 1. 创建客户端SSL上下文
        print("\n1. 创建客户端SSL上下文:")
        client_context = ssl.create_default_context()
        client_context.verify_mode = ssl.CERT_NONE  # 演示用
        client_context.check_hostname = False       # 演示用
        
        print(f"  协议版本: {client_context.protocol}")
        print(f"  验证模式: {client_context.verify_mode}")
        print(f"  检查主机名: {client_context.check_hostname}")
        print(f"  支持的密码套件数量: {len(client_context.get_ciphers())}")
        
        # 2. 创建服务器SSL上下文（如果证书文件存在）
        print("\n2. 创建服务器SSL上下文:")
        if os.path.exists(SSL_CONFIG["cert_file"]) and os.path.exists(SSL_CONFIG["key_file"]):
            try:
                server_context = SecurityManager.create_server_ssl_context(
                    SSL_CONFIG["cert_file"],
                    SSL_CONFIG["key_file"]
                )
                print(f"  服务器SSL上下文创建成功")
                print(f"  协议版本: {server_context.protocol}")
                print(f"  验证模式: {server_context.verify_mode}")
            except Exception as e:
                print(f"  服务器SSL上下文创建失败: {e}")
        else:
            print(f"  证书文件不存在，跳过服务器SSL上下文创建")
            print(f"  证书文件: {SSL_CONFIG['cert_file']}")
            print(f"  密钥文件: {SSL_CONFIG['key_file']}")
        
        # 3. 自定义SSL上下文
        print("\n3. 自定义SSL上下文:")
        custom_context = SecurityManager.create_ssl_context(
            verify_mode=ssl.CERT_NONE,
            check_hostname=False
        )
        print(f"  自定义SSL上下文创建成功")
        print(f"  验证模式: {custom_context.verify_mode}")
        print(f"  检查主机名: {custom_context.check_hostname}")
        
        return client_context
        
    except Exception as e:
        logger.error(f"SSL上下文创建演示失败: {e}")
        print(f"SSL上下文创建失败: {e}")
        return None

def demonstrate_ssl_connection():
    """
    演示SSL连接功能
    """
    print("\n=== SSL连接演示 ===")
    
    try:
        # 创建SSL上下文
        context = ssl.create_default_context()
        context.verify_mode = ssl.CERT_NONE
        context.check_hostname = False
        
        # 测试连接到各种SSL服务器
        for service, config in TEST_SERVERS.items():
            print(f"\n测试连接到 {service}: {config['host']}:{config['port']}")
            
            try:
                # 创建套接字
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)  # 10秒超时
                
                # 连接到服务器
                sock.connect((config["host"], config["port"]))
                print(f"  TCP连接成功")
                
                # 包装为SSL套接字
                ssl_sock = context.wrap_socket(
                    sock, 
                    server_hostname=config["host"]
                )
                print(f"  SSL握手成功")
                
                # 获取SSL信息
                cipher = ssl_sock.cipher()
                if cipher:
                    print(f"  密码套件: {cipher[0]}")
                    print(f"  协议版本: {cipher[1]}")
                    print(f"  密钥长度: {cipher[2]} 位")
                
                # 获取证书信息
                cert = ssl_sock.getpeercert()
                if cert:
                    print(f"  证书主题: {cert.get('subject', 'N/A')}")
                    print(f"  证书颁发者: {cert.get('issuer', 'N/A')}")
                
                # 安全关闭连接
                ssl_sock.close()
                print(f"  连接已关闭")
                
            except socket.timeout:
                print(f"  连接超时")
            except Exception as e:
                print(f"  连接失败: {e}")
        
    except Exception as e:
        logger.error(f"SSL连接演示失败: {e}")
        print(f"SSL连接演示失败: {e}")

def demonstrate_auth_string_handling():
    """
    演示认证字符串处理功能
    """
    print("\n=== 认证字符串处理演示 ===")
    
    try:
        # 测试用户数据
        test_users = {
            "user1": "password1",
            "user2": "password2",
            "testuser": "testpass",
            "admin": "admin123"
        }
        
        # 测试认证字符串生成
        print("\n1. 认证字符串生成:")
        test_credentials = [
            ("user1", "password1"),
            ("testuser", "testpass"),
            ("admin", "admin123"),
            ("invalid", "wrongpass")
        ]
        
        auth_strings = []
        for username, password in test_credentials:
            auth_string = SecurityManager.generate_auth_string(username, password)
            auth_strings.append((username, password, auth_string))
            print(f"  {username}:{password} -> {auth_string}")
        
        # 测试认证字符串验证
        print("\n2. 认证字符串验证:")
        for username, password, auth_string in auth_strings:
            verified_user = SecurityManager.verify_auth_string(auth_string, test_users)
            if verified_user:
                print(f"  {auth_string[:20]}... -> 验证成功: {verified_user}")
            else:
                print(f"  {auth_string[:20]}... -> 验证失败")
        
        # 测试无效的认证字符串
        print("\n3. 无效认证字符串测试:")
        invalid_auth_strings = [
            "invalid_base64",
            "dGVzdA==",  # 只有"test"，格式不正确
            "",          # 空字符串
        ]
        
        for invalid_auth in invalid_auth_strings:
            result = SecurityManager.verify_auth_string(invalid_auth, test_users)
            print(f"  '{invalid_auth}' -> {result}")
        
    except Exception as e:
        logger.error(f"认证字符串处理演示失败: {e}")
        print(f"认证字符串处理失败: {e}")

def demonstrate_data_encryption():
    """
    演示数据加密和解密功能
    """
    print("\n=== 数据加密/解密演示 ===")
    
    try:
        # 测试数据
        test_data = [
            "简单的文本数据",
            "包含中文的数据测试",
            "Special characters: !@#$%^&*()_+-=[]{}|;':\",./<>?",
            "很长的数据" * 100,  # 测试长数据
            ""  # 空数据
        ]
        
        # 测试不同长度的密钥
        test_keys = [
            b"1234567890123456",  # 16字节 (AES-128)
            b"123456789012345678901234",  # 24字节 (AES-192)
            b"12345678901234567890123456789012"  # 32字节 (AES-256)
        ]
        
        for key_size, key in enumerate(test_keys, 1):
            print(f"\n{key_size}. 使用 {len(key)*8} 位密钥:")
            
            for i, data in enumerate(test_data, 1):
                if not data:  # 跳过空数据
                    continue
                    
                print(f"  测试数据 {i}: {data[:50]}{'...' if len(data) > 50 else ''}")
                
                try:
                    # 编码为字节
                    data_bytes = data.encode("utf-8")
                    print(f"    原始大小: {len(data_bytes)} 字节")
                    
                    # 加密
                    encrypted_data = SecurityManager.encrypt_data(data_bytes, key)
                    print(f"    加密后大小: {len(encrypted_data)} 字节")
                    
                    # 解密
                    decrypted_data = SecurityManager.decrypt_data(encrypted_data, key)
                    decrypted_text = decrypted_data.decode("utf-8")
                    
                    # 验证
                    if decrypted_text == data:
                        print(f"    加密/解密成功")
                    else:
                        print(f"    加密/解密失败: 数据不匹配")
                        
                except Exception as e:
                    print(f"    加密/解密失败: {e}")
        
        # 测试错误的密钥
        print(f"\n4. 错误密钥测试:")
        test_text = "测试数据"
        correct_key = test_keys[0]
        wrong_key = b"wrongkey12345678"
        
        try:
            # 用正确密钥加密
            encrypted = SecurityManager.encrypt_data(test_text.encode("utf-8"), correct_key)
            print(f"  用正确密钥加密成功")
            
            # 用错误密钥解密
            try:
                decrypted = SecurityManager.decrypt_data(encrypted, wrong_key)
                print(f"  用错误密钥解密成功（不应该发生）")
            except Exception as e:
                print(f"  用错误密钥解密失败（预期结果）: {type(e).__name__}")
                
        except Exception as e:
            print(f"  测试失败: {e}")
        
    except Exception as e:
        logger.error(f"数据加密/解密演示失败: {e}")
        print(f"数据加密/解密失败: {e}")

def demonstrate_password_hashing():
    """
    演示密码哈希和验证功能
    """
    print("\n=== 密码哈希/验证演示 ===")
    
    try:
        # 测试密码
        test_passwords = [
            "simple",
            "complex_P@ssw0rd!",
            "中文密码测试",
            "very_long_password_" * 10
        ]
        
        print("1. 密码哈希测试:")
        hashed_passwords = []
        
        for i, password in enumerate(test_passwords, 1):
            print(f"\n  密码 {i}: {password}")
            
            # 哈希密码
            hashed, salt = SecurityManager.hash_password(password)
            hashed_passwords.append((password, hashed, salt))
            
            print(f"    盐值长度: {len(salt)} 字节")
            print(f"    哈希长度: {len(hashed)} 字节")
            print(f"    盐值: {salt.hex()[:32]}...")
            print(f"    哈希: {hashed.hex()[:32]}...")
        
        print("\n2. 密码验证测试:")
        for password, hashed, salt in hashed_passwords:
            # 正确密码验证
            is_valid = SecurityManager.verify_password(password, hashed, salt)
            print(f"  '{password}' (正确) -> {is_valid}")
            
            # 错误密码验证
            wrong_password = password + "_wrong"
            is_valid = SecurityManager.verify_password(wrong_password, hashed, salt)
            print(f"  '{wrong_password}' (错误) -> {is_valid}")
        
        print("\n3. 相同密码不同哈希测试:")
        same_password = "test_password"
        for i in range(3):
            hashed, salt = SecurityManager.hash_password(same_password)
            print(f"  第{i+1}次哈希: {hashed.hex()[:32]}... (盐值: {salt.hex()[:16]}...)")
        
    except Exception as e:
        logger.error(f"密码哈希/验证演示失败: {e}")
        print(f"密码哈希/验证失败: {e}")

def demonstrate_socket_utils():
    """
    演示安全套接字工具功能
    """
    print("\n=== 安全套接字工具演示 ===")
    
    try:
        print("1. 安全套接字上下文管理器:")
        
        # 创建测试套接字
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.settimeout(5)
        
        # 使用安全上下文管理器
        with safe_socket(test_sock) as sock:
            print(f"  套接字创建成功: {sock}")
            print(f"  套接字类型: {type(sock)}")
            # 这里可以进行套接字操作
            # 退出时会自动安全关闭
        
        print("  套接字已自动关闭")
        
        print("\n2. 手动安全关闭测试:")
        
        # 创建另一个测试套接字
        test_sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"  创建套接字: {test_sock2}")
        
        # 手动安全关闭
        success = close_socket_safely(test_sock2)
        print(f"  关闭结果: {success}")
        
        # 测试关闭已关闭的套接字
        success = close_socket_safely(test_sock2)
        print(f"  重复关闭结果: {success}")
        
        # 测试关闭None
        success = close_socket_safely(None)
        print(f"  关闭None结果: {success}")
        
        print("\n3. SSL连接安全关闭测试:")
        
        # 模拟SSL连接对象
        class MockSSLConnection:
            def __init__(self):
                self.closed = False
            
            def quit(self):
                if self.closed:
                    raise Exception("Already closed")
                self.closed = True
                print("    模拟SSL连接quit()调用")
            
            def close(self):
                print("    模拟SSL连接close()调用")
        
        mock_ssl_conn = MockSSLConnection()
        success = close_ssl_connection_safely(mock_ssl_conn)
        print(f"  SSL连接关闭结果: {success}")
        
    except Exception as e:
        logger.error(f"安全套接字工具演示失败: {e}")
        print(f"套接字工具演示失败: {e}")

def main():
    """
    主函数 - 演示各种安全功能
    """
    print("安全功能示例")
    print("============")
    print("注意: 本示例用于演示功能，实际使用时请根据安全要求调整配置")
    print()
    
    try:
        # 1. SSL上下文创建演示
        ssl_context = demonstrate_ssl_context_creation()
        
        # 2. SSL连接演示
        demonstrate_ssl_connection()
        
        # 3. 认证字符串处理演示
        demonstrate_auth_string_handling()
        
        # 4. 数据加密/解密演示
        demonstrate_data_encryption()
        
        # 5. 密码哈希/验证演示
        demonstrate_password_hashing()
        
        # 6. 安全套接字工具演示
        demonstrate_socket_utils()
        
        print("\n所有安全功能示例执行完成！")
        print("\n安全提示:")
        print("- 生产环境中应该验证SSL证书")
        print("- 使用强密码和适当的密钥长度")
        print("- 定期更新密码和密钥")
        print("- 妥善保管私钥和敏感数据")
        
    except KeyboardInterrupt:
        print("\n用户中断执行")
    except Exception as e:
        logger.error(f"示例执行失败: {e}")
        print(f"执行失败: {e}")

if __name__ == "__main__":
    main()
