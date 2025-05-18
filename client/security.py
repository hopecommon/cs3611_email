"""
安全模块 - 处理SSL/TLS和其他安全相关功能
"""
import os
import ssl
import socket
import hashlib
import base64
from typing import Optional, Tuple, Dict, Any, List
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import secrets

from common.utils import setup_logging
from common.config import SSL_CERT_FILE, SSL_KEY_FILE

# 设置日志
logger = setup_logging('security')

class SecurityManager:
    """安全管理类，处理加密和认证"""
    
    @staticmethod
    def create_ssl_context(
        cert_file: Optional[str] = None, 
        key_file: Optional[str] = None,
        ca_file: Optional[str] = None,
        verify_mode: int = ssl.CERT_REQUIRED,
        check_hostname: bool = True
    ) -> ssl.SSLContext:
        """
        创建SSL上下文
        
        Args:
            cert_file: 证书文件路径
            key_file: 密钥文件路径
            ca_file: CA证书文件路径
            verify_mode: 验证模式
            check_hostname: 是否检查主机名
            
        Returns:
            SSL上下文
            
        Raises:
            FileNotFoundError: 证书文件不存在
            ssl.SSLError: SSL配置错误
        """
        try:
            # 创建SSL上下文
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            
            # 设置验证模式
            context.verify_mode = verify_mode
            context.check_hostname = check_hostname
            
            # 加载CA证书
            if ca_file:
                if not os.path.exists(ca_file):
                    raise FileNotFoundError(f"CA证书文件不存在: {ca_file}")
                context.load_verify_locations(cafile=ca_file)
            
            # 加载证书和密钥
            if cert_file and key_file:
                if not os.path.exists(cert_file):
                    raise FileNotFoundError(f"证书文件不存在: {cert_file}")
                if not os.path.exists(key_file):
                    raise FileNotFoundError(f"密钥文件不存在: {key_file}")
                
                context.load_cert_chain(certfile=cert_file, keyfile=key_file)
            
            logger.info("已创建SSL上下文")
            return context
        except Exception as e:
            logger.error(f"创建SSL上下文失败: {e}")
            raise
    
    @staticmethod
    def create_server_ssl_context(
        cert_file: str = SSL_CERT_FILE, 
        key_file: str = SSL_KEY_FILE
    ) -> ssl.SSLContext:
        """
        创建服务器SSL上下文
        
        Args:
            cert_file: 证书文件路径
            key_file: 密钥文件路径
            
        Returns:
            SSL上下文
        """
        try:
            # 创建SSL上下文
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            
            # 加载证书和密钥
            if not os.path.exists(cert_file):
                raise FileNotFoundError(f"证书文件不存在: {cert_file}")
            if not os.path.exists(key_file):
                raise FileNotFoundError(f"密钥文件不存在: {key_file}")
            
            context.load_cert_chain(certfile=cert_file, keyfile=key_file)
            
            logger.info("已创建服务器SSL上下文")
            return context
        except Exception as e:
            logger.error(f"创建服务器SSL上下文失败: {e}")
            raise
    
    @staticmethod
    def wrap_socket(
        sock: socket.socket, 
        context: ssl.SSLContext, 
        server_side: bool = False,
        server_hostname: Optional[str] = None
    ) -> ssl.SSLSocket:
        """
        包装套接字为SSL套接字
        
        Args:
            sock: 原始套接字
            context: SSL上下文
            server_side: 是否为服务器端
            server_hostname: 服务器主机名（客户端使用）
            
        Returns:
            SSL套接字
        """
        try:
            if server_side:
                ssl_sock = context.wrap_socket(sock, server_side=True)
            else:
                ssl_sock = context.wrap_socket(
                    sock, 
                    server_side=False,
                    server_hostname=server_hostname
                )
            
            logger.info(f"已包装套接字为SSL套接字")
            return ssl_sock
        except Exception as e:
            logger.error(f"包装套接字失败: {e}")
            raise
    
    @staticmethod
    def generate_auth_string(username: str, password: str) -> str:
        """
        生成SMTP AUTH PLAIN认证字符串
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            BASE64编码的认证字符串
        """
        # AUTH PLAIN格式: \0username\0password
        auth_bytes = b'\0' + username.encode('utf-8') + b'\0' + password.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        return auth_b64
    
    @staticmethod
    def verify_auth_string(auth_string: str, users: Dict[str, str]) -> Optional[str]:
        """
        验证SMTP AUTH PLAIN认证字符串
        
        Args:
            auth_string: BASE64编码的认证字符串
            users: 用户名到密码的映射
            
        Returns:
            验证成功返回用户名，失败返回None
        """
        try:
            # 解码认证字符串
            auth_bytes = base64.b64decode(auth_string)
            parts = auth_bytes.split(b'\0')
            
            # AUTH PLAIN格式: \0username\0password
            if len(parts) != 3 or parts[0] != b'':
                return None
            
            username = parts[1].decode('utf-8')
            password = parts[2].decode('utf-8')
            
            # 验证用户名和密码
            if username in users and users[username] == password:
                return username
            
            return None
        except Exception as e:
            logger.error(f"验证认证字符串失败: {e}")
            return None
    
    @staticmethod
    def encrypt_data(data: bytes, key: bytes) -> bytes:
        """
        使用AES加密数据
        
        Args:
            data: 要加密的数据
            key: 加密密钥（16、24或32字节）
            
        Returns:
            加密后的数据
        """
        try:
            # 生成随机IV
            iv = secrets.token_bytes(16)
            
            # 创建加密器
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # 填充数据
            padder = padding.PKCS7(algorithms.AES.block_size).padder()
            padded_data = padder.update(data) + padder.finalize()
            
            # 加密数据
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            # 返回IV + 加密数据
            return iv + encrypted_data
        except Exception as e:
            logger.error(f"加密数据失败: {e}")
            raise
    
    @staticmethod
    def decrypt_data(encrypted_data: bytes, key: bytes) -> bytes:
        """
        使用AES解密数据
        
        Args:
            encrypted_data: 加密的数据（IV + 加密数据）
            key: 解密密钥
            
        Returns:
            解密后的数据
        """
        try:
            # 提取IV
            iv = encrypted_data[:16]
            ciphertext = encrypted_data[16:]
            
            # 创建解密器
            cipher = Cipher(
                algorithms.AES(key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # 解密数据
            padded_data = decryptor.update(ciphertext) + decryptor.finalize()
            
            # 去除填充
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
            data = unpadder.update(padded_data) + unpadder.finalize()
            
            return data
        except Exception as e:
            logger.error(f"解密数据失败: {e}")
            raise
    
    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        哈希密码
        
        Args:
            password: 密码
            salt: 盐值，如果为None则生成新的盐值
            
        Returns:
            (哈希密码, 盐值)元组
        """
        if salt is None:
            salt = secrets.token_bytes(16)
        
        # 使用PBKDF2算法哈希密码
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        
        return key, salt
    
    @staticmethod
    def verify_password(password: str, hashed_password: bytes, salt: bytes) -> bool:
        """
        验证密码
        
        Args:
            password: 待验证的密码
            hashed_password: 存储的哈希密码
            salt: 盐值
            
        Returns:
            密码是否匹配
        """
        key, _ = SecurityManager.hash_password(password, salt)
        return key == hashed_password
