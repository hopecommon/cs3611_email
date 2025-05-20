"""
POP3工具模块 - 提供POP3服务器使用的工具函数
"""

import os
import socket
import logging
import ssl
from typing import List, Optional

from common.utils import setup_logging

# 设置日志
logger = setup_logging("pop3_utils")


def is_port_available(host: str, port: int) -> bool:
    """
    检查指定的端口是否可用

    Args:
        host: 主机名或IP地址
        port: 端口号

    Returns:
        如果端口可用，返回True；否则返回False
    """
    try:
        # 创建套接字
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # 设置超时时间
            s.settimeout(1)
            # 尝试绑定端口
            s.bind((host, port))
            # 如果能绑定成功，说明端口可用
            return True
    except Exception as e:
        # 如果绑定失败，说明端口不可用
        logger.debug(f"端口 {port} 不可用: {e}")
        return False


def find_available_port(
    host: str,
    start_port: int,
    max_attempts: int = 10,
    preferred_ports: Optional[List[int]] = None,
) -> int:
    """
    查找可用端口，优先使用首选端口列表

    Args:
        host: 主机名或IP地址
        start_port: 起始端口号
        max_attempts: 最大尝试次数
        preferred_ports: 首选端口列表，如果提供，将优先尝试这些端口

    Returns:
        可用的端口号，如果找不到则返回-1
    """
    # 首先尝试首选端口列表
    if preferred_ports:
        for port in preferred_ports:
            if is_port_available(host, port):
                logger.info(f"在首选端口列表中找到可用端口: {port}")
                return port

    # 然后尝试从起始端口开始的连续端口
    port = start_port
    for i in range(max_attempts):
        if is_port_available(host, port):
            logger.info(f"在连续端口范围内找到可用端口: {port}")
            return port
        port += 1

        # 每隔几个端口尝试一下端口减1的情况
        if i % 3 == 0 and start_port > 1024:
            alt_port = start_port - (i // 3) - 1
            if alt_port > 1024 and is_port_available(host, alt_port):
                logger.info(f"在备选端口范围内找到可用端口: {alt_port}")
                return alt_port

    return -1


def close_socket_safely(sock) -> bool:
    """
    安全地关闭套接字

    Args:
        sock: 要关闭的套接字

    Returns:
        是否成功关闭
    """
    if sock is None:
        return True
    
    try:
        sock.close()
        return True
    except Exception as e:
        logger.debug(f"关闭套接字时出错: {e}")
        return False


def create_ssl_context(cert_file: str, key_file: str) -> Optional[ssl.SSLContext]:
    """
    创建SSL上下文

    Args:
        cert_file: SSL证书文件路径
        key_file: SSL密钥文件路径

    Returns:
        SSL上下文，如果创建失败则返回None
    """
    try:
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        logger.info(f"已加载SSL证书: {cert_file}")
        return context
    except Exception as e:
        logger.error(f"加载SSL证书时出错: {e}")
        return None


def validate_host(host: str) -> str:
    """
    验证主机名是否有效，如果无效则回退到localhost

    Args:
        host: 主机名或IP地址

    Returns:
        有效的主机名或IP地址
    """
    # 确保host是有效的绑定地址
    if (
        host != "localhost"
        and host != "127.0.0.1"
        and not host.startswith("192.168.")
        and not host.startswith("10.")
    ):
        try:
            # 尝试解析域名
            socket.gethostbyname(host)
        except:
            # 如果解析失败，回退到localhost
            logger.warning(f"无法解析主机名 {host}，回退到localhost")
            host = "localhost"
    
    return host
