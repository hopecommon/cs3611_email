#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
端口配置模块 - 管理服务器端口配置
提供统一的端口配置处理机制，遵循明确的优先级规则
"""

import os
import json
import logging
import socket
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Union

# 配置文件路径
CONFIG_DIR = Path("config")
PORT_CONFIG_FILE = CONFIG_DIR / "port_config.json"

# 默认端口配置
DEFAULT_CONFIG = {
    "pop3_port": 110,
    "pop3_ssl_port": 995,
    "smtp_port": 25,
    "smtp_ssl_port": 465,
}

# 最大端口号
MAX_PORT = 65535

# 设置日志
logger = logging.getLogger(__name__)


def ensure_config_dir():
    """确保配置目录存在"""
    CONFIG_DIR.mkdir(exist_ok=True)


def save_port_config(service_name, port):
    """
    保存服务端口配置

    Args:
        service_name: 服务名称，如 'pop3_port', 'pop3_ssl_port', 'smtp_port', 'smtp_ssl_port'
        port: 端口号
    """
    ensure_config_dir()

    # 读取现有配置
    config = get_port_config()

    # 更新配置
    config[service_name] = port

    # 保存配置
    try:
        with open(PORT_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        logger.info(f"已保存端口配置: {service_name}={port}")
    except Exception as e:
        logger.error(f"保存端口配置时出错: {e}")


def get_port_config():
    """
    获取端口配置

    Returns:
        包含所有服务端口配置的字典
    """
    ensure_config_dir()

    # 如果配置文件不存在，创建默认配置
    if not PORT_CONFIG_FILE.exists():
        try:
            with open(PORT_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            logger.info(f"已创建默认端口配置文件: {PORT_CONFIG_FILE}")
        except Exception as e:
            logger.error(f"创建默认端口配置文件时出错: {e}")
            return DEFAULT_CONFIG

    # 读取配置
    try:
        with open(PORT_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        return config
    except Exception as e:
        logger.error(f"读取端口配置时出错: {e}")
        return DEFAULT_CONFIG


def get_service_port(service_name, default_port=None):
    """
    获取指定服务的端口

    Args:
        service_name: 服务名称，如 'pop3_port', 'pop3_ssl_port', 'smtp_port', 'smtp_ssl_port'
        default_port: 默认端口，如果未指定则使用DEFAULT_CONFIG中的值

    Returns:
        服务端口号
    """
    config = get_port_config()

    # 如果服务名称不在配置中，使用默认端口
    if service_name not in config:
        if default_port is not None:
            return default_port
        return DEFAULT_CONFIG.get(service_name, 0)

    return config[service_name]


def is_port_available(host: str, port: int) -> bool:
    """
    检查指定端口是否可用

    Args:
        host: 主机地址
        port: 端口号

    Returns:
        如果端口可用返回True，否则返回False
    """
    if port <= 0 or port > MAX_PORT:
        return False

    try:
        # 使用connect_ex检测端口是否已被使用（比bind方法更准确）
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        # 返回值为0表示连接成功，即端口已被占用
        return result != 0
    except Exception as e:
        logger.debug(f"端口 {port} 检测出错: {e}")
        # 出错时保守处理，认为端口不可用
        return False


def find_available_port(
    host: str,
    start_port: int,
    max_attempts: int = 10,
    preferred_ports: List[int] = None,
) -> int:
    """
    查找可用端口

    Args:
        host: 主机地址
        start_port: 起始端口
        max_attempts: 尝试次数
        preferred_ports: 优先尝试的端口列表

    Returns:
        可用端口，如果找不到返回0
    """
    # 首先尝试优先端口
    if preferred_ports:
        for port in preferred_ports:
            if port > 0 and port <= MAX_PORT and is_port_available(host, port):
                return port

    # 然后从起始端口开始尝试
    port = start_port
    for _ in range(max_attempts):
        if port > MAX_PORT:
            break
        if is_port_available(host, port):
            return port
        port += 1

    return 0


def resolve_port(
    service_name: str,
    cmd_port: Optional[int] = None,
    use_ssl: bool = False,
    auto_detect: bool = False,
    is_client: bool = False,
) -> Tuple[int, bool, str]:
    """
    统一的端口解析函数，明确优先级，处理端口占用情况

    优先级：命令行参数 > 环境变量 > 用户配置文件 > 系统默认值

    Args:
        service_name: 服务名称前缀，如 'pop3', 'smtp'
        cmd_port: 命令行指定的端口
        use_ssl: 是否使用SSL
        auto_detect: 是否允许自动检测可用端口（只在非命令行指定时生效）
        is_client: 是否为客户端调用，客户端不关心端口占用，只关心能否连接

    Returns:
        (port, changed, message) 三元组:
            - port: 最终使用的端口
            - changed: 端口是否有变化
            - message: 说明信息
    """
    # 确定服务的端口配置键名
    port_key = f"{service_name}_ssl_port" if use_ssl else f"{service_name}_port"

    # 获取环境变量名
    env_var = f"{service_name.upper()}_{'SSL_' if use_ssl else ''}PORT"

    # 按优先级获取端口
    port = None
    source = ""

    # 1. 命令行参数优先级最高
    if cmd_port is not None:
        port = cmd_port
        source = "命令行参数"

    # 2. 环境变量次之
    elif env_var in os.environ:
        try:
            port = int(os.environ[env_var])
            source = "环境变量"
        except (ValueError, TypeError):
            logger.warning(f"环境变量 {env_var} 的值无效: {os.environ[env_var]}")
            # 继续尝试其他来源

    # 3. 然后是配置文件
    if port is None:
        config = get_port_config()
        if port_key in config:
            try:
                port = int(config[port_key])
                source = "配置文件"
            except (ValueError, TypeError):
                logger.warning(f"配置文件中 {port_key} 的值无效: {config[port_key]}")
                # 继续尝试默认值

    # 4. 最后是默认值
    if port is None:
        port = DEFAULT_CONFIG.get(port_key, 0)
        source = "系统默认值"

    # 验证端口有效性
    if port <= 0 or port > MAX_PORT:
        return 0, False, f"无效的端口: {port} (来自{source})"

    # 检查端口是否可用
    if is_client:
        # 客户端模式: 我们不关心端口是否被占用，只关心能否连接
        # 这里不做任何检查，因为客户端就是要连接到这个"被占用"的端口
        return port, False, f"使用端口 {port} (来自{source})"
    else:
        # 服务器模式: 需要检查端口是否被其他进程占用
        available = is_port_available(host="localhost", port=port)
        if not available:
            # 如果是命令行指定的端口，报错退出
            if cmd_port is not None:
                return 0, False, f"端口 {port} (来自{source})已被占用，请指定其他端口"

            # 如果允许自动检测端口
            if auto_detect:
                # 尝试查找可用端口
                new_port = find_available_port("localhost", port + 1)
                if new_port > 0:
                    return (
                        new_port,
                        True,
                        f"端口 {port} (来自{source})已被占用，已自动切换到端口 {new_port}",
                    )
                else:
                    return (
                        0,
                        False,
                        f"端口 {port} (来自{source})已被占用，且无法找到可用端口",
                    )
            else:
                return (
                    0,
                    False,
                    f"端口 {port} (来自{source})已被占用，请手动指定其他端口",
                )

    # 端口可用，返回
    return port, False, f"使用端口 {port} (来自{source})"


def update_configuration(
    auto_save: bool = False,
) -> Dict[str, Dict[str, Union[int, bool, str]]]:
    """
    检查并更新所有端口配置，返回各服务可用的端口信息

    Args:
        auto_save: 是否自动保存检测到的可用端口到配置文件

    Returns:
        包含各服务端口信息的字典，格式为:
        {
            'smtp': {'port': 25, 'changed': False, 'message': '...'},
            'smtp_ssl': {'port': 465, 'changed': False, 'message': '...'},
            'pop3': {'port': 110, 'changed': False, 'message': '...'},
            'pop3_ssl': {'port': 995, 'changed': False, 'message': '...'}
        }
    """
    result = {}
    services = [("smtp", False), ("smtp", True), ("pop3", False), ("pop3", True)]

    for service, use_ssl in services:
        key = f"{service}_ssl" if use_ssl else service
        port, changed, message = resolve_port(service, None, use_ssl, True)

        result[key] = {"port": port, "changed": changed, "message": message}

        # 如果端口已变更且允许自动保存
        if changed and auto_save and port > 0:
            port_key = f"{service}_ssl_port" if use_ssl else f"{service}_port"
            save_port_config(port_key, port)

    return result
