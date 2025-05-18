"""
配置文件模块 - 管理应用程序的所有配置参数
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件中的环境变量（如果存在）
load_dotenv()

# 基础路径
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据存储路径
DATA_DIR = os.path.join(BASE_DIR, "data")
EMAIL_STORAGE_DIR = os.path.join(DATA_DIR, "emails")
DB_PATH = os.path.join(DATA_DIR, "email_db.sqlite")

# 确保目录存在
os.makedirs(EMAIL_STORAGE_DIR, exist_ok=True)

# 服务器配置
SMTP_SERVER = {
    "host": str(os.getenv("SMTP_HOST", "localhost")),
    "port": int(os.getenv("SMTP_PORT", 25)),
    "use_ssl": os.getenv("SMTP_USE_SSL", "False").lower() == "true",
    "ssl_port": int(os.getenv("SMTP_SSL_PORT", 465)),
    "username": str(os.getenv("SMTP_USERNAME", "")),
    "password": str(os.getenv("SMTP_PASSWORD", "")),
    "auth_method": "AUTO",
}

POP3_SERVER = {
    "host": str(os.getenv("POP3_HOST", "localhost")),
    "port": int(os.getenv("POP3_PORT", 110)),
    "use_ssl": os.getenv("POP3_USE_SSL", "False").lower() == "true",
    "ssl_port": int(os.getenv("POP3_SSL_PORT", 995)),
    "username": str(os.getenv("POP3_USERNAME", "")),
    "password": str(os.getenv("POP3_PASSWORD", "")),
    "auth_method": "AUTO",
}

# 安全配置
SSL_CERT_FILE = os.getenv(
    "SSL_CERT_FILE", os.path.join(BASE_DIR, "certs", "server.crt")
)
SSL_KEY_FILE = os.getenv("SSL_KEY_FILE", os.path.join(BASE_DIR, "certs", "server.key"))

# 用户认证
AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "True").lower() == "true"

# 并发配置
MAX_CONNECTIONS = int(os.getenv("MAX_CONNECTIONS", 10))
CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", 60))  # 秒

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.path.join(BASE_DIR, "logs", "email_app.log")
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Web界面配置（如果启用）
WEB_HOST = os.getenv("WEB_HOST", "localhost")
WEB_PORT = int(os.getenv("WEB_PORT", 5000))
SECRET_KEY = os.getenv("SECRET_KEY", "dev_key_please_change_in_production")

# 垃圾邮件过滤配置
SPAM_FILTER_ENABLED = os.getenv("SPAM_FILTER_ENABLED", "False").lower() == "true"
SPAM_KEYWORDS = os.getenv("SPAM_KEYWORDS", "viagra,casino,lottery,prize,winner").split(
    ","
)
SPAM_THRESHOLD = float(os.getenv("SPAM_THRESHOLD", 0.7))  # 贝叶斯分类器阈值

# PGP配置
PGP_ENABLED = os.getenv("PGP_ENABLED", "False").lower() == "true"
PGP_HOME = os.getenv("PGP_HOME", os.path.join(BASE_DIR, "pgp"))
os.makedirs(PGP_HOME, exist_ok=True)

# 邮件撤回功能
RECALL_ENABLED = os.getenv("RECALL_ENABLED", "False").lower() == "true"
RECALL_TIMEOUT = int(os.getenv("RECALL_TIMEOUT", 3600))  # 允许撤回的时间窗口（秒）
