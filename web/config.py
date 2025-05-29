"""
Flask Web应用配置 - 支持多环境配置
"""

import os
import secrets
from pathlib import Path


class Config:
    """基础配置类"""

    # 项目根目录
    BASE_DIR = Path(__file__).resolve().parent.parent

    # Flask配置
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    # 数据库配置 - 使用项目现有的数据库
    DB_PATH = os.path.join(BASE_DIR, "data", "emails.db.sqlite")
    EMAIL_STORAGE_DIR = os.path.join(BASE_DIR, "data", "emails")

    # 上传文件配置
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "data", "uploads")
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32MB 最大文件大小

    # 邮件配置
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False

    # 分页配置
    EMAILS_PER_PAGE = 20

    # 会话配置
    PERMANENT_SESSION_LIFETIME = 3600  # 1小时
    SESSION_COOKIE_SECURE = False  # 开发环境设为False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # CSRF保护
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    # 日志配置
    LOG_TO_STDOUT = os.environ.get("LOG_TO_STDOUT")

    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        # 确保必要的目录存在
        os.makedirs(Config.EMAIL_STORAGE_DIR, exist_ok=True)
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(os.path.join(Config.BASE_DIR, "logs"), exist_ok=True)


class DevelopmentConfig(Config):
    """开发环境配置"""

    DEBUG = True
    DEVELOPMENT = True

    # 开发环境数据库
    DB_PATH = os.path.join(Config.BASE_DIR, "data", "emails_dev.db")

    # 开发环境日志
    LOG_LEVEL = "DEBUG"


class TestingConfig(Config):
    """测试环境配置"""

    TESTING = True
    WTF_CSRF_ENABLED = False

    # 测试环境数据库
    DB_PATH = os.path.join(Config.BASE_DIR, "data", "emails_test.db")

    # 测试环境日志
    LOG_LEVEL = "INFO"


class ProductionConfig(Config):
    """生产环境配置"""

    DEBUG = False
    TESTING = False

    # 生产环境安全配置
    SESSION_COOKIE_SECURE = True

    # 生产环境日志
    LOG_LEVEL = "WARNING"

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # 生产环境特定初始化
        import logging
        from logging.handlers import RotatingFileHandler

        if not app.debug:
            if not os.path.exists("logs"):
                os.mkdir("logs")
            file_handler = RotatingFileHandler(
                "logs/email_web.log", maxBytes=10240, backupCount=10
            )
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"
                )
            )
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)

            app.logger.setLevel(logging.INFO)
            app.logger.info("Email Web应用启动")


# 配置字典
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
