#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POP3服务器完整功能测试
"""

import os
import sys
import time
import socket
import subprocess
import threading
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common.utils import setup_logging

# 设置日志
logger = setup_logging("test_pop3_complete")

class POP3TestClient:
    """简单的POP3测试客户端"""
    
    def __init__(self, host="localhost", port=8110):
        self.host = host
        self.port = port
        self.sock = None
        
    def connect(self):
        """连接到POP3服务器"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((self.host, self.port))
            
            # 读取欢迎消息
            welcome = self.recv_response()
            if welcome.startswith("+OK"):
                print(f"[OK] 连接成功: {welcome}")
                return True
            else:
                print(f"[FAIL] 连接失败: {welcome}")
                return False
        except Exception as e:
            print(f"[FAIL] 连接异常: {e}")
            return False
    
    def send_command(self, command):
        """发送命令"""
        try:
            self.sock.send(f"{command}\r\n".encode('utf-8'))
            return True
        except Exception as e:
            print(f"[FAIL] 发送命令失败: {e}")
            return False
    
    def recv_response(self):
        """接收响应"""
        try:
            response = self.sock.recv(1024).decode('utf-8').strip()
            return response
        except Exception as e:
            print(f"[FAIL] 接收响应失败: {e}")
            return ""
    
    def recv_multiline_response(self):
        """接收多行响应（以.结束）"""
        lines = []
        try:
            while True:
                line = self.sock.recv(1024).decode('utf-8').strip()
                if line == ".":
                    break
                lines.append(line)
            return lines
        except Exception as e:
            print(f"[FAIL] 接收多行响应失败: {e}")
            return []
    
    def authenticate(self, username, password):
        """认证用户"""
        # 发送USER命令
        if not self.send_command(f"USER {username}"):
            return False
        
        user_resp = self.recv_response()
        if not user_resp.startswith("+OK"):
            print(f"[FAIL] USER命令失败: {user_resp}")
            return False
        
        print(f"[OK] USER命令成功: {user_resp}")
        
        # 发送PASS命令
        if not self.send_command(f"PASS {password}"):
            return False
        
        pass_resp = self.recv_response()
        if not pass_resp.startswith("+OK"):
            print(f"[FAIL] PASS命令失败: {pass_resp}")
            return False
        
        print(f"[OK] PASS命令成功: {pass_resp}")
        return True
    
    def stat(self):
        """获取邮件统计"""
        if not self.send_command("STAT"):
            return None
        
        stat_resp = self.recv_response()
        if stat_resp.startswith("+OK"):
            print(f"[OK] STAT命令成功: {stat_resp}")
            # 解析响应 "+OK 1 274"
            parts = stat_resp.split()
            if len(parts) >= 3:
                return int(parts[1]), int(parts[2])  # 邮件数量, 总大小
        else:
            print(f"[FAIL] STAT命令失败: {stat_resp}")
        
        return None
    
    def list_messages(self):
        """列出所有邮件"""
        if not self.send_command("LIST"):
            return []
        
        list_resp = self.recv_response()
        if not list_resp.startswith("+OK"):
            print(f"[FAIL] LIST命令失败: {list_resp}")
            return []
        
        print(f"[OK] LIST命令成功: {list_resp}")
        
        # 接收邮件列表
        messages = self.recv_multiline_response()
        print(f"[OK] 接收到 {len(messages)} 条邮件信息")
        
        return messages
    
    def retrieve_message(self, msg_num):
        """检索指定邮件"""
        if not self.send_command(f"RETR {msg_num}"):
            return None
        
        retr_resp = self.recv_response()
        if not retr_resp.startswith("+OK"):
            print(f"[FAIL] RETR命令失败: {retr_resp}")
            return None
        
        print(f"[OK] RETR命令成功: {retr_resp}")
        
        # 接收邮件内容
        content_lines = self.recv_multiline_response()
        content = "\n".join(content_lines)
        print(f"[OK] 接收到邮件内容，大小: {len(content)} 字符")
        
        return content
    
    def delete_message(self, msg_num):
        """删除指定邮件"""
        if not self.send_command(f"DELE {msg_num}"):
            return False
        
        dele_resp = self.recv_response()
        if dele_resp.startswith("+OK"):
            print(f"[OK] DELE命令成功: {dele_resp}")
            return True
        else:
            print(f"[FAIL] DELE命令失败: {dele_resp}")
            return False
    
    def quit(self):
        """退出连接"""
        if not self.send_command("QUIT"):
            return False
        
        quit_resp = self.recv_response()
        if quit_resp.startswith("+OK"):
            print(f"[OK] QUIT命令成功: {quit_resp}")
            return True
        else:
            print(f"[FAIL] QUIT命令失败: {quit_resp}")
            return False
    
    def close(self):
        """关闭连接"""
        if self.sock:
            self.sock.close()
            self.sock = None

def start_pop3_server():
    """启动POP3服务器"""
    print("启动POP3服务器...")
    
    try:
        process = subprocess.Popen([
            "python", "server/stable_pop3_server.py",
            "--host", "localhost",
            "--port", "8110",
            "--no-ssl"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # 等待服务器启动
        time.sleep(3)
        
        if process.poll() is None:
            print("[OK] POP3服务器启动成功")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"[FAIL] POP3服务器启动失败:")
            print(f"stdout: {stdout}")
            print(f"stderr: {stderr}")
            return None
    except Exception as e:
        print(f"[FAIL] 启动POP3服务器异常: {e}")
        return None

def test_pop3_functionality():
    """测试POP3功能"""
    print("\n=== POP3功能测试 ===")
    
    client = POP3TestClient()
    
    try:
        # 1. 连接测试
        print("\n1. 连接测试")
        if not client.connect():
            return False
        
        # 2. 认证测试
        print("\n2. 认证测试")
        if not client.authenticate("testuser", "testpass"):
            return False
        
        # 3. STAT命令测试
        print("\n3. STAT命令测试")
        stat_result = client.stat()
        if stat_result is None:
            return False
        
        msg_count, total_size = stat_result
        print(f"邮件数量: {msg_count}, 总大小: {total_size} 字节")
        
        # 4. LIST命令测试
        print("\n4. LIST命令测试")
        messages = client.list_messages()
        if not messages and msg_count > 0:
            print("[FAIL] LIST命令返回空列表但STAT显示有邮件")
            return False
        
        for i, msg_info in enumerate(messages, 1):
            print(f"  邮件 {i}: {msg_info}")
        
        # 5. RETR命令测试（如果有邮件）
        if msg_count > 0:
            print("\n5. RETR命令测试")
            content = client.retrieve_message(1)
            if content is None:
                return False
            
            print(f"邮件内容预览（前200字符）:")
            print(content[:200] + "..." if len(content) > 200 else content)
        
        # 6. QUIT命令测试
        print("\n6. QUIT命令测试")
        if not client.quit():
            return False
        
        print("\n[SUCCESS] 所有POP3功能测试通过！")
        return True
        
    except Exception as e:
        print(f"[FAIL] POP3功能测试异常: {e}")
        return False
    finally:
        client.close()

def main():
    """主函数"""
    print("POP3服务器完整功能测试")
    print("=" * 50)
    
    pop3_process = None
    
    try:
        # 启动POP3服务器
        pop3_process = start_pop3_server()
        if not pop3_process:
            print("[FAIL] 无法启动POP3服务器")
            return 1
        
        # 运行功能测试
        if test_pop3_functionality():
            print("\n[SUCCESS] POP3服务器完整功能测试成功！")
            return 0
        else:
            print("\n[FAIL] POP3服务器功能测试失败！")
            return 1
    
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n[FAIL] 测试过程中出错: {e}")
        return 1
    finally:
        # 清理资源
        if pop3_process:
            print("\n停止POP3服务器...")
            pop3_process.terminate()
            pop3_process.wait(timeout=5)
            print("POP3服务器已停止")

if __name__ == "__main__":
    sys.exit(main())
