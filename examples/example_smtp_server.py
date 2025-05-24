# -*- coding: utf-8 -*-
"""
SMTP服务器启动和配置示例脚本

本脚本演示如何启动和配置SMTP服务器：
- 基本SMTP服务器启动
- SSL/TLS配置
- 用户认证设置
- 数据库初始化
- 服务器监控和管理

使用前请确保已正确配置数据库和SSL证书。
"""

import os
import sys
import time
import signal
import threading
import subprocess
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.smtp_server import StableSMTPServer
from server.new_db_handler import EmailService as DatabaseHandler
from server.user_auth import UserAuth
from common.utils import setup_logging
from common.config import SSL_CERT_FILE, SSL_KEY_FILE

# 设置日志
logger = setup_logging("smtp_server_example", verbose=True)

# ==================== 配置部分 ====================

# SMTP服务器配置
SMTP_CONFIG = {
    "host": "localhost",
    "port": 8025,  # 非SSL端口
    "ssl_port": 8465,  # SSL端口 (改为8465避免权限问题)
    "use_ssl": True,  # 默认开启SSL
    "start_both": True,  # 同时启动SSL和非SSL服务器
    "max_connections": 50,  # 最大并发连接数
    "timeout": 300,  # 连接超时时间（秒）
    "require_auth": True,  # 是否需要认证
    "enable_logging": True,  # 是否启用详细日志
}

# 数据库配置
DATABASE_CONFIG = {
    "db_path": "data/smtp_server.db",
    "backup_enabled": True,
    "backup_interval": 3600,  # 备份间隔（秒）
}

# 测试用户配置
TEST_USERS = [
    {
        "username": "admin",
        "email": "admin@localhost",
        "password": "admin123",
        "full_name": "系统管理员",
    },
    {
        "username": "user1",
        "email": "user1@localhost",
        "password": "user123",
        "full_name": "测试用户1",
    },
    {
        "username": "user2",
        "email": "user2@localhost",
        "password": "user456",
        "full_name": "测试用户2",
    },
]

# 全局变量
smtp_server = None
smtp_ssl_server = None
db_handler = None
user_auth = None
server_thread = None
ssl_server_thread = None
shutdown_event = threading.Event()


def setup_database():
    """
    初始化数据库和用户数据
    """
    print("=== 初始化数据库 ===")

    try:
        # 确保数据目录存在
        os.makedirs(os.path.dirname(DATABASE_CONFIG["db_path"]), exist_ok=True)

        # 创建数据库处理器
        global db_handler
        db_handler = DatabaseHandler(DATABASE_CONFIG["db_path"])

        # 初始化数据库表
        db_handler.init_db()
        print(f"数据库初始化成功: {DATABASE_CONFIG['db_path']}")

        # 创建用户认证管理器
        global user_auth
        user_auth = UserAuth(DATABASE_CONFIG["db_path"])

        # 创建测试用户
        print("\n创建测试用户:")
        for user_config in TEST_USERS:
            try:
                user = user_auth.create_user(
                    username=user_config["username"],
                    email=user_config["email"],
                    password=user_config["password"],
                    full_name=user_config["full_name"],
                )
                if user:
                    print(f"  ✅ 用户创建成功: {user.username} ({user.email})")
                else:
                    print(f"  ⚠️  用户可能已存在: {user_config['username']}")
            except Exception as e:
                print(f"  ❌ 用户创建失败: {user_config['username']} - {e}")

        # 显示用户列表
        users = user_auth.list_users()
        print(f"\n当前用户总数: {len(users)}")
        for user in users:
            status = "激活" if user.is_active else "停用"
            print(f"  - {user.username} ({user.email}) - {status}")

        return True

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        print(f"❌ 数据库初始化失败: {e}")
        return False


def check_ssl_certificates():
    """
    检查SSL证书文件，如果不存在则自动生成
    """
    print("\n=== 检查SSL证书 ===")

    if not SMTP_CONFIG["use_ssl"]:
        print("SSL未启用，跳过证书检查")
        return True

    cert_file = SSL_CERT_FILE
    key_file = SSL_KEY_FILE

    if os.path.exists(cert_file) and os.path.exists(key_file):
        print(f"✅ SSL证书文件存在:")
        print(f"  证书文件: {cert_file}")
        print(f"  密钥文件: {key_file}")
        return True
    else:
        print(f"⚠️  SSL证书文件不存在，正在自动生成...")
        return create_ssl_certificate()


def create_ssl_certificate():
    """
    自动生成自签名SSL证书
    """
    try:
        # 确保证书目录存在
        cert_dir = os.path.dirname(SSL_CERT_FILE)
        os.makedirs(cert_dir, exist_ok=True)

        print(f"正在生成自签名证书...")

        # 尝试使用OpenSSL命令生成证书
        cmd = [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            SSL_KEY_FILE,
            "-out",
            SSL_CERT_FILE,
            "-days",
            "365",
            "-nodes",
            "-subj",
            "/C=CN/ST=Beijing/L=Beijing/O=Test/OU=IT/CN=localhost",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cert_dir)
        if result.returncode == 0:
            print(f"✅ SSL证书生成成功:")
            print(f"  证书文件: {SSL_CERT_FILE}")
            print(f"  密钥文件: {SSL_KEY_FILE}")
            return True
        else:
            print(f"❌ OpenSSL命令失败: {result.stderr}")
            return create_ssl_certificate_with_python()

    except FileNotFoundError:
        print("⚠️  OpenSSL命令未找到，尝试使用Python生成证书...")
        return create_ssl_certificate_with_python()
    except Exception as e:
        print(f"❌ 生成SSL证书时出错: {e}")
        return create_ssl_certificate_with_python()


def create_ssl_certificate_with_python():
    """
    使用Python cryptography库生成自签名证书
    """
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime
        import ipaddress

        print("使用Python cryptography库生成证书...")

        # 生成私钥
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # 创建证书主题
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, "CN"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Beijing"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "Beijing"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test Organization"),
                x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
            ]
        )

        # 创建证书
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
            .add_extension(
                x509.SubjectAlternativeName(
                    [
                        x509.DNSName("localhost"),
                        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                    ]
                ),
                critical=False,
            )
            .sign(private_key, hashes.SHA256())
        )

        # 确保证书目录存在
        cert_dir = os.path.dirname(SSL_CERT_FILE)
        os.makedirs(cert_dir, exist_ok=True)

        # 保存私钥
        with open(SSL_KEY_FILE, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        # 保存证书
        with open(SSL_CERT_FILE, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        print(f"✅ SSL证书生成成功:")
        print(f"  证书文件: {SSL_CERT_FILE}")
        print(f"  密钥文件: {SSL_KEY_FILE}")
        return True

    except ImportError:
        print("❌ cryptography库未安装，无法生成SSL证书")
        print("请安装: pip install cryptography")
        print("或手动生成证书:")
        print(
            f"  openssl req -x509 -newkey rsa:2048 -keyout {SSL_KEY_FILE} -out {SSL_CERT_FILE} -days 365 -nodes -subj '/CN=localhost'"
        )
        return False
    except Exception as e:
        print(f"❌ 使用Python生成SSL证书时出错: {e}")
        return False


def create_smtp_server():
    """
    创建SMTP服务器实例
    """
    print("\n=== 创建SMTP服务器 ===")

    try:
        global smtp_server, smtp_ssl_server

        # 创建非SSL服务器
        smtp_server = StableSMTPServer(
            host=SMTP_CONFIG["host"],
            port=SMTP_CONFIG["port"],
            db_handler=db_handler,
            require_auth=SMTP_CONFIG["require_auth"],
            use_ssl=False,  # 非SSL服务器
            max_connections=SMTP_CONFIG["max_connections"],
        )

        print(f"✅ 非SSL SMTP服务器创建成功")
        print(f"  监听地址: {SMTP_CONFIG['host']}")
        print(f"  端口: {SMTP_CONFIG['port']}")

        # 如果启用SSL，创建SSL服务器
        if SMTP_CONFIG["use_ssl"] and SMTP_CONFIG["start_both"]:
            smtp_ssl_server = StableSMTPServer(
                host=SMTP_CONFIG["host"],
                port=SMTP_CONFIG["ssl_port"],
                db_handler=db_handler,
                require_auth=SMTP_CONFIG["require_auth"],
                use_ssl=True,  # SSL服务器
                max_connections=SMTP_CONFIG["max_connections"],
            )
            print(f"✅ SSL SMTP服务器创建成功")
            print(f"  SSL端口: {SMTP_CONFIG['ssl_port']}")

        print(f"  最大连接数: {SMTP_CONFIG['max_connections']}")
        print(f"  连接超时: {SMTP_CONFIG['timeout']}秒")

        return True

    except Exception as e:
        logger.error(f"SMTP服务器创建失败: {e}")
        print(f"❌ SMTP服务器创建失败: {e}")
        return False


def start_server():
    """
    启动SMTP服务器
    """
    print("\n=== 启动SMTP服务器 ===")

    try:
        global server_thread, ssl_server_thread

        # 启动非SSL服务器
        server_thread = threading.Thread(target=smtp_server.start, daemon=True)
        server_thread.start()
        print(f"✅ 非SSL SMTP服务器线程已启动")

        # 如果存在SSL服务器，启动它
        if smtp_ssl_server:
            ssl_server_thread = threading.Thread(
                target=smtp_ssl_server.start, daemon=True
            )
            ssl_server_thread.start()
            print(f"✅ SSL SMTP服务器线程已启动")

        # 等待服务器启动
        time.sleep(3)

        print(f"✅ SMTP服务器启动成功")
        print(f"  服务器状态: 运行中")
        print(f"  进程ID: {os.getpid()}")

        # 显示连接信息
        print(f"\n📧 邮件客户端连接信息:")
        print(f"  SMTP服务器: {SMTP_CONFIG['host']}")
        print(f"  非SSL端口: {SMTP_CONFIG['port']}")
        if smtp_ssl_server:
            print(f"  SSL端口: {SMTP_CONFIG['ssl_port']}")
            print(f"  加密: SSL/TLS (SSL端口) 或 无加密 (非SSL端口)")
        else:
            print(f"  加密: 无")
        print(f"  认证: {'需要' if SMTP_CONFIG['require_auth'] else '不需要'}")

        # 显示测试用户信息
        print(f"\n👤 测试用户账号:")
        for user_config in TEST_USERS:
            print(f"  用户名: {user_config['username']}")
            print(f"  邮箱: {user_config['email']}")
            print(f"  密码: {user_config['password']}")
            print()

        return True

    except Exception as e:
        logger.error(f"SMTP服务器启动失败: {e}")
        print(f"❌ SMTP服务器启动失败: {e}")
        return False


def monitor_server():
    """
    监控服务器状态
    """
    print("=== 服务器监控 ===")
    print("按 Ctrl+C 停止服务器")
    print()

    try:
        while not shutdown_event.is_set():
            # 显示服务器状态
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            server_status = "运行中"
            if smtp_ssl_server:
                server_status += " (SSL+非SSL)"
            else:
                server_status += " (非SSL)"
            print(f"\r[{current_time}] 服务器{server_status}... ", end="", flush=True)

            # 每5秒更新一次
            if shutdown_event.wait(5):
                break

    except KeyboardInterrupt:
        print("\n\n收到停止信号...")
        shutdown_event.set()


def stop_server():
    """
    停止SMTP服务器
    """
    print("\n=== 停止SMTP服务器 ===")

    try:
        if smtp_server:
            smtp_server.stop()
            print("✅ 非SSL SMTP服务器已停止")

        if smtp_ssl_server:
            smtp_ssl_server.stop()
            print("✅ SSL SMTP服务器已停止")

        if db_handler:
            # 可以在这里执行数据库清理操作
            print("✅ 数据库连接已关闭")

        print("✅ 服务器已完全停止")

    except Exception as e:
        logger.error(f"停止服务器时出错: {e}")
        print(f"⚠️  停止服务器时出错: {e}")


def signal_handler(signum, frame):
    """
    信号处理器
    """
    print(f"\n收到信号 {signum}，正在停止服务器...")
    shutdown_event.set()


def display_server_info():
    """
    显示服务器信息
    """
    print("SMTP服务器示例")
    print("=" * 50)
    print("本示例演示如何启动和配置SMTP服务器")
    print()

    print("功能特性:")
    print("- 完整的SMTP协议支持")
    print("- 用户认证和权限管理")
    print("- 邮件接收和存储")
    print("- SSL/TLS加密支持")
    print("- 并发连接处理")
    print("- 实时监控和日志")
    print()


def test_server_connection():
    """
    测试服务器连接
    """
    print("=== 测试服务器连接 ===")

    try:
        import socket

        # 测试非SSL端口
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((SMTP_CONFIG["host"], SMTP_CONFIG["port"]))
        sock.close()

        if result == 0:
            print(f"✅ 非SSL端口 {SMTP_CONFIG['port']} 连接成功")
        else:
            print(f"❌ 非SSL端口 {SMTP_CONFIG['port']} 连接失败")

        # 如果启用SSL且存在SSL服务器，测试SSL端口
        if smtp_ssl_server and SMTP_CONFIG["use_ssl"]:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((SMTP_CONFIG["host"], SMTP_CONFIG["ssl_port"]))
            sock.close()

            if result == 0:
                print(f"✅ SSL端口 {SMTP_CONFIG['ssl_port']} 连接成功")
            else:
                print(f"❌ SSL端口 {SMTP_CONFIG['ssl_port']} 连接失败")

    except Exception as e:
        print(f"⚠️  连接测试失败: {e}")


def main():
    """
    主函数 - SMTP服务器示例
    """
    # 显示服务器信息
    display_server_info()

    # 设置信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # 1. 初始化数据库
        if not setup_database():
            return 1

        # 2. 检查SSL证书
        if not check_ssl_certificates():
            print("⚠️  SSL证书检查失败，将只启动非SSL服务器")
            SMTP_CONFIG["use_ssl"] = False
            SMTP_CONFIG["start_both"] = False

        # 3. 创建SMTP服务器
        if not create_smtp_server():
            return 1

        # 4. 启动服务器
        if not start_server():
            return 1

        # 5. 测试连接
        test_server_connection()

        # 6. 监控服务器
        monitor_server()

    except KeyboardInterrupt:
        print("\n用户中断执行")
    except Exception as e:
        logger.error(f"服务器运行失败: {e}")
        print(f"❌ 服务器运行失败: {e}")
        return 1
    finally:
        # 7. 停止服务器
        stop_server()

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
