#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
POP3服务器端口检测测试脚本

此脚本用于测试POP3服务器的端口检测和自动切换功能。
"""

import sys
import time
import socket
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.pop3_server import POP3Server, is_port_available
from common.utils import setup_logging
from common.port_config import get_service_port, save_port_config

# 设置日志
logger = setup_logging("test_pop3_port_detection")

def occupy_port(port):
    """
    占用指定端口
    
    Args:
        port: 要占用的端口号
        
    Returns:
        socket对象，如果成功占用端口；None，如果占用失败
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('localhost', port))
        s.listen(5)
        print(f"成功占用端口 {port}")
        return s
    except Exception as e:
        print(f"占用端口 {port} 失败: {e}")
        return None

def test_port_detection_basic():
    """测试基本的端口检测功能"""
    print("\n===== 测试基本端口检测 =====")
    
    # 测试端口可用性检测
    test_port = 8110
    if is_port_available('localhost', test_port):
        print(f"端口 {test_port} 可用")
    else:
        print(f"端口 {test_port} 不可用")
    
    # 占用端口
    sock = occupy_port(test_port)
    
    # 再次测试端口可用性
    if is_port_available('localhost', test_port):
        print(f"端口 {test_port} 可用 (意外结果)")
    else:
        print(f"端口 {test_port} 不可用 (预期结果)")
    
    # 释放端口
    if sock:
        sock.close()
        print(f"已释放端口 {test_port}")

def test_port_auto_switching():
    """测试端口自动切换功能"""
    print("\n===== 测试端口自动切换 =====")
    
    # 获取当前配置的端口
    original_port = get_service_port("pop3_port", 110)
    print(f"当前配置的POP3端口: {original_port}")
    
    # 占用这个端口
    sock = occupy_port(original_port)
    if not sock:
        print(f"无法占用端口 {original_port}，跳过测试")
        return
    
    try:
        # 创建POP3服务器，应该会自动切换到其他端口
        print(f"创建POP3服务器，预期会自动切换端口...")
        server = POP3Server(port=original_port, use_ssl=False)
        
        # 启动服务器
        server.start()
        
        # 检查端口是否已更改
        new_port = server.port
        if new_port != original_port:
            print(f"端口自动切换成功: {original_port} -> {new_port}")
        else:
            print(f"端口未切换，仍为: {original_port} (意外结果)")
        
        # 检查配置文件是否已更新
        config_port = get_service_port("pop3_port")
        if config_port == new_port:
            print(f"配置文件已更新为新端口: {config_port}")
        else:
            print(f"配置文件未更新，仍为: {config_port} (意外结果)")
        
        # 停止服务器
        server.stop()
        print("服务器已停止")
    except Exception as e:
        print(f"测试过程中出错: {e}")
    finally:
        # 释放占用的端口
        if sock:
            sock.close()
            print(f"已释放端口 {original_port}")
        
        # 恢复原始端口配置
        save_port_config("pop3_port", original_port)
        print(f"已恢复原始端口配置: {original_port}")

def test_ssl_port_auto_switching():
    """测试SSL端口自动切换功能"""
    print("\n===== 测试SSL端口自动切换 =====")
    
    # 获取当前配置的SSL端口
    original_ssl_port = get_service_port("pop3_ssl_port", 995)
    print(f"当前配置的POP3 SSL端口: {original_ssl_port}")
    
    # 占用这个端口
    sock = occupy_port(original_ssl_port)
    if not sock:
        print(f"无法占用端口 {original_ssl_port}，跳过测试")
        return
    
    try:
        # 创建POP3服务器，应该会自动切换到其他端口
        print(f"创建POP3 SSL服务器，预期会自动切换端口...")
        server = POP3Server(port=110, ssl_port=original_ssl_port, use_ssl=True)
        
        # 启动服务器
        server.start()
        
        # 检查端口是否已更改
        new_port = server.port
        if new_port != original_ssl_port:
            print(f"SSL端口自动切换成功: {original_ssl_port} -> {new_port}")
        else:
            print(f"SSL端口未切换，仍为: {original_ssl_port} (意外结果)")
        
        # 检查配置文件是否已更新
        config_port = get_service_port("pop3_ssl_port")
        if config_port == new_port:
            print(f"配置文件已更新为新SSL端口: {config_port}")
        else:
            print(f"配置文件未更新，仍为: {config_port} (意外结果)")
        
        # 停止服务器
        server.stop()
        print("服务器已停止")
    except Exception as e:
        print(f"测试过程中出错: {e}")
    finally:
        # 释放占用的端口
        if sock:
            sock.close()
            print(f"已释放端口 {original_ssl_port}")
        
        # 恢复原始端口配置
        save_port_config("pop3_ssl_port", original_ssl_port)
        print(f"已恢复原始SSL端口配置: {original_ssl_port}")

def main():
    """主函数"""
    print("开始测试POP3服务器端口检测和自动切换功能...")
    
    # 测试基本端口检测
    test_port_detection_basic()
    
    # 测试端口自动切换
    test_port_auto_switching()
    
    # 测试SSL端口自动切换
    test_ssl_port_auto_switching()
    
    print("\n所有测试完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
