"""
套接字工具模块 - 提供套接字相关的工具函数和类
"""

import socket
import ssl
import logging
from contextlib import contextmanager

# 设置日志
logger = logging.getLogger(__name__)

@contextmanager
def safe_socket(sock=None):
    """
    安全地管理套接字，确保在异常情况下也能正确关闭
    
    Args:
        sock: 要管理的套接字对象，如果为None则不做任何操作
        
    Yields:
        传入的套接字对象
    """
    try:
        yield sock
    finally:
        if sock:
            try:
                sock.close()
                logger.debug("套接字已安全关闭")
            except Exception as e:
                logger.debug(f"关闭套接字时出错: {e}")

def close_socket_safely(sock):
    """
    安全地关闭套接字
    
    Args:
        sock: 要关闭的套接字对象
        
    Returns:
        关闭是否成功
    """
    if sock:
        try:
            sock.close()
            logger.debug("套接字已安全关闭")
            return True
        except Exception as e:
            logger.debug(f"关闭套接字时出错: {e}")
    return False

def close_ssl_connection_safely(connection):
    """
    安全地关闭SSL连接
    
    Args:
        connection: 要关闭的连接对象
        
    Returns:
        关闭是否成功
    """
    if connection:
        # 尝试使用quit方法
        try:
            if hasattr(connection, 'quit'):
                connection.quit()
                logger.debug("连接已通过quit方法安全关闭")
                return True
        except Exception as e:
            logger.debug(f"使用quit方法关闭连接时出错: {e}")
        
        # 尝试使用close方法
        try:
            if hasattr(connection, 'close'):
                connection.close()
                logger.debug("连接已通过close方法安全关闭")
                return True
        except Exception as e:
            logger.debug(f"使用close方法关闭连接时出错: {e}")
        
        # 尝试直接关闭套接字
        if hasattr(connection, 'sock') and connection.sock:
            return close_socket_safely(connection.sock)
    
    return False
