"""
SMTP服务器模块 - 实现基本的SMTP服务
"""
import os
import socket
import threading
import ssl
import time
import datetime
import re
from typing import Dict, List, Optional, Tuple, Any, Set
import asyncio
import email
from email.parser import Parser
from email.message import EmailMessage

from common.utils import setup_logging, generate_message_id
from common.config import (
    SMTP_SERVER, MAX_CONNECTIONS, CONNECTION_TIMEOUT,
    SSL_CERT_FILE, SSL_KEY_FILE, AUTH_REQUIRED
)
from client.security import SecurityManager
from server.db_handler import DatabaseHandler

# 设置日志
logger = setup_logging('smtp_server')

class SMTPSession:
    """SMTP会话类，处理单个客户端连接"""
    
    def __init__(
        self, 
        client_socket: socket.socket, 
        client_address: Tuple[str, int],
        db_handler: DatabaseHandler,
        auth_required: bool = AUTH_REQUIRED,
        users: Optional[Dict[str, str]] = None
    ):
        """
        初始化SMTP会话
        
        Args:
            client_socket: 客户端套接字
            client_address: 客户端地址
            db_handler: 数据库处理器
            auth_required: 是否需要认证
            users: 用户名到密码的映射
        """
        self.socket = client_socket
        self.address = client_address
        self.db_handler = db_handler
        self.auth_required = auth_required
        self.users = users or {}
        
        # 会话状态
        self.authenticated = not auth_required
        self.authenticated_user = None
        self.helo_domain = None
        self.mail_from = None
        self.rcpt_to = []
        self.data_mode = False
        self.message_data = []
        
        # 设置超时
        self.socket.settimeout(CONNECTION_TIMEOUT)
        
        logger.info(f"新的SMTP会话: {client_address}")
    
    def handle(self) -> None:
        """处理SMTP会话"""
        try:
            # 发送欢迎消息
            self.send_response(220, f"SMTP Server Ready")
            
            # 处理命令
            while True:
                # 接收命令
                command = self.receive_command()
                if not command:
                    break
                
                # 处理命令
                if not self.process_command(command):
                    break
        except Exception as e:
            logger.error(f"处理SMTP会话时出错: {e}")
        finally:
            # 关闭连接
            try:
                self.socket.close()
            except:
                pass
            
            logger.info(f"SMTP会话结束: {self.address}")
    
    def receive_command(self) -> Optional[str]:
        """
        接收SMTP命令
        
        Returns:
            命令字符串，如果连接关闭则返回None
        """
        try:
            data = self.socket.recv(1024)
            if not data:
                return None
            
            command = data.decode('ascii', errors='ignore').strip()
            logger.debug(f"收到命令: {command}")
            return command
        except socket.timeout:
            logger.warning(f"连接超时: {self.address}")
            self.send_response(421, "Connection timed out")
            return None
        except Exception as e:
            logger.error(f"接收命令时出错: {e}")
            return None
    
    def send_response(self, code: int, message: str) -> None:
        """
        发送SMTP响应
        
        Args:
            code: 响应代码
            message: 响应消息
        """
        try:
            response = f"{code} {message}\r\n"
            self.socket.sendall(response.encode('ascii'))
            logger.debug(f"发送响应: {response.strip()}")
        except Exception as e:
            logger.error(f"发送响应时出错: {e}")
    
    def process_command(self, command: str) -> bool:
        """
        处理SMTP命令
        
        Args:
            command: 命令字符串
            
        Returns:
            是否继续处理
        """
        # 如果在DATA模式下
        if self.data_mode:
            return self.process_data(command)
        
        # 解析命令
        parts = command.split(' ', 1)
        cmd = parts[0].upper()
        arg = parts[1] if len(parts) > 1 else ""
        
        # 处理各种命令
        if cmd == "HELO":
            return self.process_helo(arg)
        elif cmd == "EHLO":
            return self.process_ehlo(arg)
        elif cmd == "AUTH":
            return self.process_auth(arg)
        elif cmd == "MAIL":
            return self.process_mail(arg)
        elif cmd == "RCPT":
            return self.process_rcpt(arg)
        elif cmd == "DATA":
            return self.process_data_command()
        elif cmd == "RSET":
            return self.process_rset()
        elif cmd == "NOOP":
            return self.process_noop()
        elif cmd == "QUIT":
            return self.process_quit()
        else:
            # 未知命令
            self.send_response(500, f"Unrecognized command: {cmd}")
            return True
    
    def process_helo(self, domain: str) -> bool:
        """
        处理HELO命令
        
        Args:
            domain: 客户端域名
            
        Returns:
            是否继续处理
        """
        if not domain:
            self.send_response(501, "Syntax error in parameters or arguments")
            return True
        
        self.helo_domain = domain
        self.send_response(250, f"Hello {domain}")
        return True
    
    def process_ehlo(self, domain: str) -> bool:
        """
        处理EHLO命令
        
        Args:
            domain: 客户端域名
            
        Returns:
            是否继续处理
        """
        if not domain:
            self.send_response(501, "Syntax error in parameters or arguments")
            return True
        
        self.helo_domain = domain
        
        # 发送功能列表
        self.send_response(250, f"Hello {domain}")
        
        # 如果需要认证，提供AUTH选项
        if self.auth_required and not self.authenticated:
            self.socket.sendall(b"250-AUTH PLAIN LOGIN\r\n")
        
        # 其他扩展
        self.socket.sendall(b"250-SIZE 10240000\r\n")
        self.socket.sendall(b"250-8BITMIME\r\n")
        self.socket.sendall(b"250 HELP\r\n")
        
        return True
    
    def process_auth(self, arg: str) -> bool:
        """
        处理AUTH命令
        
        Args:
            arg: 认证参数
            
        Returns:
            是否继续处理
        """
        if not self.auth_required:
            self.send_response(503, "Authentication not required")
            return True
        
        if self.authenticated:
            self.send_response(503, "Already authenticated")
            return True
        
        parts = arg.split(' ', 1)
        auth_type = parts[0].upper()
        
        if auth_type == "PLAIN":
            # AUTH PLAIN [base64-string]
            if len(parts) > 1:
                auth_string = parts[1]
                return self.process_auth_plain(auth_string)
            else:
                # 需要客户端发送认证字符串
                self.send_response(334, "")
                auth_string = self.receive_command()
                if auth_string:
                    return self.process_auth_plain(auth_string)
                return False
        elif auth_type == "LOGIN":
            # 交互式登录
            self.send_response(334, "VXNlcm5hbWU6")  # Base64编码的"Username:"
            username_b64 = self.receive_command()
            if not username_b64:
                return False
            
            self.send_response(334, "UGFzc3dvcmQ6")  # Base64编码的"Password:"
            password_b64 = self.receive_command()
            if not password_b64:
                return False
            
            return self.process_auth_login(username_b64, password_b64)
        else:
            self.send_response(504, f"Unrecognized authentication type: {auth_type}")
            return True
    
    def process_auth_plain(self, auth_string: str) -> bool:
        """
        处理AUTH PLAIN认证
        
        Args:
            auth_string: BASE64编码的认证字符串
            
        Returns:
            是否继续处理
        """
        username = SecurityManager.verify_auth_string(auth_string, self.users)
        
        if username:
            self.authenticated = True
            self.authenticated_user = username
            self.send_response(235, "Authentication successful")
        else:
            self.send_response(535, "Authentication failed")
        
        return True
    
    def process_auth_login(self, username_b64: str, password_b64: str) -> bool:
        """
        处理AUTH LOGIN认证
        
        Args:
            username_b64: BASE64编码的用户名
            password_b64: BASE64编码的密码
            
        Returns:
            是否继续处理
        """
        import base64
        
        try:
            username = base64.b64decode(username_b64).decode('utf-8')
            password = base64.b64decode(password_b64).decode('utf-8')
            
            if username in self.users and self.users[username] == password:
                self.authenticated = True
                self.authenticated_user = username
                self.send_response(235, "Authentication successful")
            else:
                self.send_response(535, "Authentication failed")
        except Exception as e:
            logger.error(f"处理AUTH LOGIN认证时出错: {e}")
            self.send_response(501, "Syntax error in parameters")
        
        return True
    
    def process_mail(self, arg: str) -> bool:
        """
        处理MAIL FROM命令
        
        Args:
            arg: 命令参数
            
        Returns:
            是否继续处理
        """
        if self.auth_required and not self.authenticated:
            self.send_response(530, "Authentication required")
            return True
        
        if not self.helo_domain:
            self.send_response(503, "HELO/EHLO first")
            return True
        
        # 解析MAIL FROM:<address>
        match = re.match(r'^FROM:<([^>]*)>', arg, re.IGNORECASE)
        if not match:
            self.send_response(501, "Syntax error in parameters")
            return True
        
        self.mail_from = match.group(1)
        self.rcpt_to = []
        self.send_response(250, "OK")
        return True
    
    def process_rcpt(self, arg: str) -> bool:
        """
        处理RCPT TO命令
        
        Args:
            arg: 命令参数
            
        Returns:
            是否继续处理
        """
        if not self.mail_from:
            self.send_response(503, "MAIL first")
            return True
        
        # 解析RCPT TO:<address>
        match = re.match(r'^TO:<([^>]*)>', arg, re.IGNORECASE)
        if not match:
            self.send_response(501, "Syntax error in parameters")
            return True
        
        recipient = match.group(1)
        self.rcpt_to.append(recipient)
        self.send_response(250, "OK")
        return True
    
    def process_data_command(self) -> bool:
        """
        处理DATA命令
        
        Returns:
            是否继续处理
        """
        if not self.rcpt_to:
            self.send_response(503, "RCPT first")
            return True
        
        self.data_mode = True
        self.message_data = []
        self.send_response(354, "Start mail input; end with <CRLF>.<CRLF>")
        return True
    
    def process_data(self, data: str) -> bool:
        """
        处理DATA模式下的数据
        
        Args:
            data: 数据行
            
        Returns:
            是否继续处理
        """
        # 检查数据结束标记
        if data == ".":
            return self.process_end_of_data()
        
        # 处理行开头的点（透明性规则）
        if data.startswith("."):
            data = data[1:]
        
        # 添加到消息数据
        self.message_data.append(data)
        return True
    
    def process_end_of_data(self) -> bool:
        """
        处理数据结束
        
        Returns:
            是否继续处理
        """
        self.data_mode = False
        
        # 组装消息
        message_text = "\r\n".join(self.message_data)
        
        # 生成消息ID
        message_id = generate_message_id()
        
        # 保存到数据库
        try:
            # 解析邮件
            parser = Parser()
            msg = parser.parsestr(message_text)
            
            # 获取主题
            subject = msg.get("Subject", "(No Subject)")
            
            # 保存邮件元数据
            self.db_handler.save_email_metadata(
                message_id=message_id,
                from_addr=self.mail_from,
                to_addrs=self.rcpt_to,
                subject=subject,
                date=datetime.datetime.now(),
                size=len(message_text)
            )
            
            # 保存邮件内容
            self.db_handler.save_email_content(
                message_id=message_id,
                content=message_text
            )
            
            logger.info(f"邮件已保存: {message_id}")
            self.send_response(250, f"OK: message queued as {message_id}")
        except Exception as e:
            logger.error(f"保存邮件时出错: {e}")
            self.send_response(554, f"Transaction failed: {e}")
        
        # 重置状态
        self.mail_from = None
        self.rcpt_to = []
        self.message_data = []
        
        return True
    
    def process_rset(self) -> bool:
        """
        处理RSET命令
        
        Returns:
            是否继续处理
        """
        # 重置状态
        self.mail_from = None
        self.rcpt_to = []
        self.data_mode = False
        self.message_data = []
        
        self.send_response(250, "OK")
        return True
    
    def process_noop(self) -> bool:
        """
        处理NOOP命令
        
        Returns:
            是否继续处理
        """
        self.send_response(250, "OK")
        return True
    
    def process_quit(self) -> bool:
        """
        处理QUIT命令
        
        Returns:
            是否继续处理
        """
        self.send_response(221, "Bye")
        return False
