# -*- coding: utf-8 -*-
"""
POP3服务器启动和配置示例脚本

本脚本演示如何启动和配置POP3服务器：
- 基本POP3服务器启动
- SSL/TLS配置
- 用户认证设置
- 邮件数据准备
- 服务器监控和管理

使用前请确保已正确配置数据库和邮件数据。
"""

import os
import sys
import time
import signal
import threading
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.pop3_server import StablePOP3Server
from server.new_db_handler import DatabaseHandler

from server.user_auth import UserAuth
from common.utils import setup_logging, generate_message_id
from common.models import Email, EmailAddress, EmailStatus
from common.config import SSL_CERT_FILE, SSL_KEY_FILE, EMAIL_STORAGE_DIR

# 设置日志
logger = setup_logging("pop3_server_example", verbose=True)

# ==================== 配置部分 ====================

# POP3服务器配置
POP3_CONFIG = {
    "host": "localhost",
    "port": 8110,  # 非SSL端口
    "ssl_port": 8995,  # SSL端口 (改为8995避免权限问题)
    "use_ssl": True,  # 使用SSL
    "max_connections": 30,  # 最大并发连接数
    "timeout": 600,  # 连接超时时间（秒）
    "enable_logging": True,  # 是否启用详细日志
}

# 数据库配置
DATABASE_CONFIG = {
    "db_path": "data/pop3_server.db",
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
pop3_server = None
db_handler = None
user_auth = None
server_thread = None
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

        return True

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        print(f"❌ 数据库初始化失败: {e}")
        return False


def create_sample_emails():
    """
    创建示例邮件数据
    """
    print("\n=== 创建示例邮件 ===")

    try:
        # 确保邮件存储目录存在
        os.makedirs(EMAIL_STORAGE_DIR, exist_ok=True)

        # 为每个用户创建示例邮件
        for user_config in TEST_USERS:
            user_email = user_config["email"]
            print(f"\n为用户 {user_config['username']} 创建邮件:")

            # 创建3封示例邮件
            for i in range(1, 4):
                email = Email(
                    message_id=generate_message_id(),
                    subject=f"测试邮件 {i} - 发给 {user_config['full_name']}",
                    from_addr=EmailAddress(name="系统测试", address="system@localhost"),
                    to_addrs=[
                        EmailAddress(name=user_config["full_name"], address=user_email)
                    ],
                    text_content=f"""这是第 {i} 封测试邮件。

邮件内容:
- 收件人: {user_config['full_name']} ({user_email})
- 发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 邮件编号: {i}

这是一封用于测试POP3服务器功能的示例邮件。
您可以使用POP3客户端连接到服务器来检索此邮件。

测试功能包括:
1. 邮件列表查看
2. 邮件内容检索
3. 邮件删除操作
4. 用户认证验证

祝您使用愉快！

--
系统自动生成的测试邮件
""",
                    date=datetime.now() - timedelta(hours=i),
                    status=EmailStatus.RECEIVED,
                )

                try:
                    # 生成邮件文件路径
                    # 清理邮件ID，移除尖括号和特殊字符
                    message_id = email.message_id.strip("<>").replace("@", "_at_")
                    import re

                    message_id = re.sub(r'[\\/*?:"<>|]', "_", message_id)

                    # 创建.eml文件路径
                    eml_filename = f"{message_id}.eml"
                    eml_filepath = os.path.join(EMAIL_STORAGE_DIR, eml_filename)

                    # 使用MIMEHandler保存邮件为.eml文件
                    from client.mime_handler import MIMEHandler

                    MIMEHandler.save_as_eml(email, eml_filepath)

                    # 保存邮件内容到数据库（读取刚生成的.eml文件内容）
                    with open(eml_filepath, "r", encoding="utf-8") as f:
                        eml_content = f.read()

                    db_handler.save_email_content(email.message_id, eml_content)

                    # 然后保存邮件元数据
                    success = db_handler.save_received_email_metadata(
                        email, eml_filepath
                    )
                    if success:
                        print(f"  ✅ 邮件 {i} 创建成功: {email.subject}")
                    else:
                        print(f"  ⚠️  邮件 {i} 元数据保存失败: {email.subject}")
                except Exception as e:
                    print(f"  ❌ 邮件 {i} 创建失败: {e}")
                    logger.error(f"邮件创建详细错误: {e}")

        # 显示邮件统计
        total_emails = 0
        for user_config in TEST_USERS:
            user_emails = db_handler.list_emails(user_email=user_config["email"])
            user_count = len(user_emails)
            total_emails += user_count
            print(f"  {user_config['username']}: {user_count} 封邮件")

        print(f"\n总共创建了 {total_emails} 封示例邮件")
        return True

    except Exception as e:
        logger.error(f"创建示例邮件失败: {e}")
        print(f"❌ 创建示例邮件失败: {e}")
        return False


def check_ssl_certificates():
    """
    检查SSL证书文件，如果不存在则自动生成
    """
    print("\n=== 检查SSL证书 ===")

    if not POP3_CONFIG["use_ssl"]:
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


def create_pop3_server():
    """
    创建POP3服务器实例
    """
    print("\n=== 创建POP3服务器 ===")

    try:
        global pop3_server
        pop3_server = StablePOP3Server(
            host=POP3_CONFIG["host"],
            port=(
                POP3_CONFIG["ssl_port"]
                if POP3_CONFIG["use_ssl"]
                else POP3_CONFIG["port"]
            ),
            use_ssl=POP3_CONFIG["use_ssl"],
            max_connections=POP3_CONFIG["max_connections"],
        )

        print(f"✅ POP3服务器创建成功")
        print(f"  监听地址: {POP3_CONFIG['host']}")
        if POP3_CONFIG["use_ssl"]:
            print(f"  SSL端口: {POP3_CONFIG['ssl_port']}")
        else:
            print(f"  非SSL端口: {POP3_CONFIG['port']}")
        print(f"  最大连接数: {POP3_CONFIG['max_connections']}")
        print(f"  连接超时: {POP3_CONFIG['timeout']}秒")

        return True

    except Exception as e:
        logger.error(f"POP3服务器创建失败: {e}")
        print(f"❌ POP3服务器创建失败: {e}")
        return False


def start_server():
    """
    启动POP3服务器
    """
    print("\n=== 启动POP3服务器 ===")

    try:
        # 在单独线程中启动服务器
        global server_thread
        server_thread = threading.Thread(target=pop3_server.start, daemon=True)
        server_thread.start()

        # 等待服务器启动
        time.sleep(2)

        print(f"✅ POP3服务器启动成功")
        print(f"  服务器状态: 运行中")
        print(f"  进程ID: {os.getpid()}")

        # 显示连接信息
        print(f"\n📧 邮件客户端连接信息:")
        print(f"  POP3服务器: {POP3_CONFIG['host']}")
        if POP3_CONFIG["use_ssl"]:
            print(f"  SSL端口: {POP3_CONFIG['ssl_port']}")
            print(f"  加密: SSL/TLS")
        else:
            print(f"  非SSL端口: {POP3_CONFIG['port']}")
            print(f"  加密: 无")

        # 显示测试用户信息
        print(f"\n👤 测试用户账号:")
        for user_config in TEST_USERS:
            user_emails = db_handler.list_emails(user_email=user_config["email"])
            print(f"  用户名: {user_config['username']}")
            print(f"  邮箱: {user_config['email']}")
            print(f"  密码: {user_config['password']}")
            print(f"  邮件数: {len(user_emails)} 封")
            print()

        return True

    except Exception as e:
        logger.error(f"POP3服务器启动失败: {e}")
        print(f"❌ POP3服务器启动失败: {e}")
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
            ssl_status = "SSL" if POP3_CONFIG["use_ssl"] else "非SSL"
            print(
                f"\r[{current_time}] 服务器运行中 ({ssl_status})... ",
                end="",
                flush=True,
            )

            # 每5秒更新一次
            if shutdown_event.wait(5):
                break

    except KeyboardInterrupt:
        print("\n\n收到停止信号...")
        shutdown_event.set()


def stop_server():
    """
    停止POP3服务器
    """
    print("\n=== 停止POP3服务器 ===")

    try:
        if pop3_server:
            pop3_server.stop()
            print("✅ POP3服务器已停止")

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
    print("POP3服务器示例")
    print("=" * 50)
    print("本示例演示如何启动和配置POP3服务器")
    print()

    print("功能特性:")
    print("- 完整的POP3协议支持")
    print("- 用户认证和权限管理")
    print("- 邮件检索和删除")
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

        if POP3_CONFIG["use_ssl"]:
            # 测试SSL端口
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((POP3_CONFIG["host"], POP3_CONFIG["ssl_port"]))
            sock.close()

            if result == 0:
                print(f"✅ SSL端口 {POP3_CONFIG['ssl_port']} 连接成功")
            else:
                print(f"❌ SSL端口 {POP3_CONFIG['ssl_port']} 连接失败")
        else:
            # 测试非SSL端口
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((POP3_CONFIG["host"], POP3_CONFIG["port"]))
            sock.close()

            if result == 0:
                print(f"✅ 非SSL端口 {POP3_CONFIG['port']} 连接成功")
            else:
                print(f"❌ 非SSL端口 {POP3_CONFIG['port']} 连接失败")

    except Exception as e:
        print(f"⚠️  连接测试失败: {e}")


def main():
    """
    主函数 - POP3服务器示例
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

        # 2. 创建示例邮件
        if not create_sample_emails():
            return 1

        # 3. 检查SSL证书
        if not check_ssl_certificates():
            print("⚠️  SSL证书检查失败，将只启动非SSL服务器")
            POP3_CONFIG["use_ssl"] = False

        # 4. 创建POP3服务器
        if not create_pop3_server():
            return 1

        # 5. 启动服务器
        if not start_server():
            return 1

        # 6. 测试连接
        test_server_connection()

        # 7. 监控服务器
        monitor_server()

    except KeyboardInterrupt:
        print("\n用户中断执行")
    except Exception as e:
        logger.error(f"服务器运行失败: {e}")
        print(f"❌ 服务器运行失败: {e}")
        return 1
    finally:
        # 8. 停止服务器
        stop_server()

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
