"""
POP3服务器模块 - 实现基本的POP3服务
"""
import os
import socket
import threading
import ssl
import time
from typing import Dict, List, Optional, Tuple, Any, Set
import json

from common.utils import setup_logging
from common.config import (
    POP3_SERVER, MAX_CONNECTIONS, CONNECTION_TIMEOUT,
    SSL_CERT_FILE, SSL_KEY_FILE, AUTH_REQUIRED
)
from client.security import SecurityManager
from server.db_handler import DatabaseHandler

# 设置日志
logger = setup_logging('pop3_server')

class POP3Session:
    """POP3会话类，处理单个客户端连接"""
    
    def __init__(
        self, 
        client_socket: socket.socket, 
        client_address: Tuple[str, int],
        db_handler: DatabaseHandler,
        auth_required: bool = AUTH_REQUIRED,
        users: Optional[Dict[str, str]] = None
    ):
        """
        初始化POP3会话
        
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
        self.state = "AUTHORIZATION"  # AUTHORIZATION, TRANSACTION, UPDATE
        self.authenticated = not auth_required
        self.authenticated_user = None
        self.marked_for_deletion = set()  # 标记为删除的邮件ID
        
        # 设置超时
        self.socket.settimeout(CONNECTION_TIMEOUT)
        
        logger.info(f"新的POP3会话: {client_address}")
    
    def handle(self) -> None:
        """处理POP3会话"""
        try:
            # 发送欢迎消息
            self.send_response("+OK POP3 server ready")
            
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
            logger.error(f"处理POP3会话时出错: {e}")
        finally:
            # 如果在UPDATE状态，执行删除操作
            if self.state == "UPDATE":
                self.perform_deletions()
            
            # 关闭连接
            try:
                self.socket.close()
            except:
                pass
            
            logger.info(f"POP3会话结束: {self.address}")
    
    def receive_command(self) -> Optional[str]:
        """
        接收POP3命令
        
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
            self.send_response("-ERR Connection timed out")
            return None
        except Exception as e:
            logger.error(f"接收命令时出错: {e}")
            return None
    
    def send_response(self, response: str) -> None:
        """
        发送POP3响应
        
        Args:
            response: 响应消息
        """
        try:
            self.socket.sendall(f"{response}\r\n".encode('ascii'))
            logger.debug(f"发送响应: {response}")
        except Exception as e:
            logger.error(f"发送响应时出错: {e}")
    
    def process_command(self, command: str) -> bool:
        """
        处理POP3命令
        
        Args:
            command: 命令字符串
            
        Returns:
            是否继续处理
        """
        # 解析命令
        parts = command.split(' ', 1)
        cmd = parts[0].upper()
        arg = parts[1] if len(parts) > 1 else ""
        
        # 处理各种命令
        if cmd == "USER":
            return self.process_user(arg)
        elif cmd == "PASS":
            return self.process_pass(arg)
        elif cmd == "QUIT":
            return self.process_quit()
        elif cmd == "STAT":
            return self.process_stat()
        elif cmd == "LIST":
            return self.process_list(arg)
        elif cmd == "RETR":
            return self.process_retr(arg)
        elif cmd == "DELE":
            return self.process_dele(arg)
        elif cmd == "NOOP":
            return self.process_noop()
        elif cmd == "RSET":
            return self.process_rset()
        elif cmd == "TOP":
            return self.process_top(arg)
        elif cmd == "UIDL":
            return self.process_uidl(arg)
        else:
            # 未知命令
            self.send_response(f"-ERR Unrecognized command: {cmd}")
            return True
    
    def process_user(self, username: str) -> bool:
        """
        处理USER命令
        
        Args:
            username: 用户名
            
        Returns:
            是否继续处理
        """
        if self.state != "AUTHORIZATION":
            self.send_response("-ERR Command not valid in this state")
            return True
        
        if not username:
            self.send_response("-ERR Username required")
            return True
        
        # 保存用户名，等待密码
        self.authenticated_user = username
        self.send_response("+OK User name accepted, password please")
        return True
    
    def process_pass(self, password: str) -> bool:
        """
        处理PASS命令
        
        Args:
            password: 密码
            
        Returns:
            是否继续处理
        """
        if self.state != "AUTHORIZATION":
            self.send_response("-ERR Command not valid in this state")
            return True
        
        if not self.authenticated_user:
            self.send_response("-ERR USER first")
            return True
        
        if not password:
            self.send_response("-ERR Password required")
            return True
        
        # 验证密码
        if self.authenticated_user in self.users and self.users[self.authenticated_user] == password:
            self.authenticated = True
            self.state = "TRANSACTION"
            self.send_response("+OK Logged in")
        else:
            self.authenticated_user = None
            self.send_response("-ERR Authentication failed")
        
        return True
    
    def process_quit(self) -> bool:
        """
        处理QUIT命令
        
        Returns:
            是否继续处理
        """
        if self.state == "TRANSACTION":
            # 进入UPDATE状态
            self.state = "UPDATE"
            self.send_response("+OK POP3 server signing off")
        else:
            self.send_response("+OK POP3 server signing off")
        
        return False
    
    def process_stat(self) -> bool:
        """
        处理STAT命令
        
        Returns:
            是否继续处理
        """
        if self.state != "TRANSACTION":
            self.send_response("-ERR Command not valid in this state")
            return True
        
        # 获取邮箱统计信息
        emails = self.db_handler.list_emails(
            user_email=self.authenticated_user,
            include_deleted=False,
            include_spam=False
        )
        
        # 计算总大小
        count = len(emails)
        size = sum(email.get('size', 0) for email in emails)
        
        self.send_response(f"+OK {count} {size}")
        return True
    
    def process_list(self, arg: str) -> bool:
        """
        处理LIST命令
        
        Args:
            arg: 可选的邮件编号
            
        Returns:
            是否继续处理
        """
        if self.state != "TRANSACTION":
            self.send_response("-ERR Command not valid in this state")
            return True
        
        # 获取邮件列表
        emails = self.db_handler.list_emails(
            user_email=self.authenticated_user,
            include_deleted=False,
            include_spam=False
        )
        
        # 如果指定了邮件编号
        if arg:
            try:
                msg_num = int(arg)
                if 1 <= msg_num <= len(emails):
                    email = emails[msg_num - 1]
                    self.send_response(f"+OK {msg_num} {email.get('size', 0)}")
                else:
                    self.send_response(f"-ERR No such message")
            except ValueError:
                self.send_response(f"-ERR Invalid message number")
        else:
            # 返回所有邮件
            self.send_response(f"+OK {len(emails)} messages")
            for i, email in enumerate(emails, 1):
                self.send_response(f"{i} {email.get('size', 0)}")
            self.send_response(".")
        
        return True
    
    def process_retr(self, arg: str) -> bool:
        """
        处理RETR命令
        
        Args:
            arg: 邮件编号
            
        Returns:
            是否继续处理
        """
        if self.state != "TRANSACTION":
            self.send_response("-ERR Command not valid in this state")
            return True
        
        if not arg:
            self.send_response("-ERR Message number required")
            return True
        
        try:
            msg_num = int(arg)
            
            # 获取邮件列表
            emails = self.db_handler.list_emails(
                user_email=self.authenticated_user,
                include_deleted=False,
                include_spam=False
            )
            
            if 1 <= msg_num <= len(emails):
                email = emails[msg_num - 1]
                
                # 获取邮件内容
                content = self.db_handler.get_email_content(email['message_id'])
                
                if content:
                    # 标记为已读
                    self.db_handler.mark_email_as_read(email['message_id'])
                    
                    # 发送邮件内容
                    self.send_response(f"+OK {len(content.encode('utf-8'))} octets")
                    
                    # 发送邮件内容（按行）
                    for line in content.split('\n'):
                        # 处理行开头的点（透明性规则）
                        if line.startswith('.'):
                            line = '.' + line
                        self.send_response(line)
                    
                    # 结束标记
                    self.send_response(".")
                else:
                    self.send_response("-ERR Message content not found")
            else:
                self.send_response(f"-ERR No such message")
        except ValueError:
            self.send_response(f"-ERR Invalid message number")
        
        return True
    
    def process_dele(self, arg: str) -> bool:
        """
        处理DELE命令
        
        Args:
            arg: 邮件编号
            
        Returns:
            是否继续处理
        """
        if self.state != "TRANSACTION":
            self.send_response("-ERR Command not valid in this state")
            return True
        
        if not arg:
            self.send_response("-ERR Message number required")
            return True
        
        try:
            msg_num = int(arg)
            
            # 获取邮件列表
            emails = self.db_handler.list_emails(
                user_email=self.authenticated_user,
                include_deleted=False,
                include_spam=False
            )
            
            if 1 <= msg_num <= len(emails):
                email = emails[msg_num - 1]
                
                # 标记为删除
                self.marked_for_deletion.add(email['message_id'])
                
                self.send_response(f"+OK Message {msg_num} deleted")
            else:
                self.send_response(f"-ERR No such message")
        except ValueError:
            self.send_response(f"-ERR Invalid message number")
        
        return True
    
    def process_noop(self) -> bool:
        """
        处理NOOP命令
        
        Returns:
            是否继续处理
        """
        if self.state != "TRANSACTION":
            self.send_response("-ERR Command not valid in this state")
            return True
        
        self.send_response("+OK")
        return True
    
    def process_rset(self) -> bool:
        """
        处理RSET命令
        
        Returns:
            是否继续处理
        """
        if self.state != "TRANSACTION":
            self.send_response("-ERR Command not valid in this state")
            return True
        
        # 清除删除标记
        self.marked_for_deletion.clear()
        
        self.send_response("+OK")
        return True
    
    def process_top(self, arg: str) -> bool:
        """
        处理TOP命令
        
        Args:
            arg: "msg_num n"，其中n是要返回的行数
            
        Returns:
            是否继续处理
        """
        if self.state != "TRANSACTION":
            self.send_response("-ERR Command not valid in this state")
            return True
        
        parts = arg.split()
        if len(parts) != 2:
            self.send_response("-ERR Usage: TOP msg_num n")
            return True
        
        try:
            msg_num = int(parts[0])
            n_lines = int(parts[1])
            
            # 获取邮件列表
            emails = self.db_handler.list_emails(
                user_email=self.authenticated_user,
                include_deleted=False,
                include_spam=False
            )
            
            if 1 <= msg_num <= len(emails):
                email = emails[msg_num - 1]
                
                # 获取邮件内容
                content = self.db_handler.get_email_content(email['message_id'])
                
                if content:
                    # 分割头部和正文
                    parts = content.split('\r\n\r\n', 1)
                    header = parts[0]
                    body = parts[1] if len(parts) > 1 else ""
                    
                    # 发送头部
                    self.send_response(f"+OK")
                    
                    # 发送头部（按行）
                    for line in header.split('\n'):
                        # 处理行开头的点（透明性规则）
                        if line.startswith('.'):
                            line = '.' + line
                        self.send_response(line)
                    
                    # 发送空行
                    self.send_response("")
                    
                    # 发送正文的前n行
                    body_lines = body.split('\n')
                    for i, line in enumerate(body_lines):
                        if i >= n_lines:
                            break
                        
                        # 处理行开头的点（透明性规则）
                        if line.startswith('.'):
                            line = '.' + line
                        self.send_response(line)
                    
                    # 结束标记
                    self.send_response(".")
                else:
                    self.send_response("-ERR Message content not found")
            else:
                self.send_response(f"-ERR No such message")
        except ValueError:
            self.send_response(f"-ERR Invalid parameters")
        
        return True
    
    def process_uidl(self, arg: str) -> bool:
        """
        处理UIDL命令
        
        Args:
            arg: 可选的邮件编号
            
        Returns:
            是否继续处理
        """
        if self.state != "TRANSACTION":
            self.send_response("-ERR Command not valid in this state")
            return True
        
        # 获取邮件列表
        emails = self.db_handler.list_emails(
            user_email=self.authenticated_user,
            include_deleted=False,
            include_spam=False
        )
        
        # 如果指定了邮件编号
        if arg:
            try:
                msg_num = int(arg)
                if 1 <= msg_num <= len(emails):
                    email = emails[msg_num - 1]
                    self.send_response(f"+OK {msg_num} {email['message_id']}")
                else:
                    self.send_response(f"-ERR No such message")
            except ValueError:
                self.send_response(f"-ERR Invalid message number")
        else:
            # 返回所有邮件
            self.send_response(f"+OK")
            for i, email in enumerate(emails, 1):
                self.send_response(f"{i} {email['message_id']}")
            self.send_response(".")
        
        return True
    
    def perform_deletions(self) -> None:
        """执行删除操作"""
        for message_id in self.marked_for_deletion:
            self.db_handler.mark_email_as_deleted(message_id)
        
        logger.info(f"已删除{len(self.marked_for_deletion)}封邮件")
        self.marked_for_deletion.clear()
