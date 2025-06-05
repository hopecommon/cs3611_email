"""
Web邮件界面模块 - Flask Web应用
"""

__version__ = "1.0.0"
__author__ = "CS3611 Project Team"

from flask import Flask, g
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from pathlib import Path
import sys
import os

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 导入统一配置
from common.config import DB_PATH, EMAIL_STORAGE_DIR

# 导入蓝图
from web.routes.auth import auth_bp
from web.routes.main import main_bp
from web.routes.email import email_bp
from web.routes.mail_config import mail_config_bp
from web.routes.cli_api import cli_api_bp

# 导入模型
from web.models import WebUser
from server.user_auth import UserAuth

# 尝试导入新的邮箱认证系统
try:
    from web.routes.email_auth import email_auth_bp
    from web.simple_email_auth import load_user_by_email, get_user_by_id

    EMAIL_AUTH_AVAILABLE = True
    print("✅ 邮箱认证系统导入成功")
except ImportError as e:
    print(f"⚠️  邮箱认证系统导入失败: {e}")
    EMAIL_AUTH_AVAILABLE = False
    email_auth_bp = None
    load_user_by_email = None
    get_user_by_id = None


def create_app(config_name="development"):
    """Flask应用工厂函数"""
    app = Flask(__name__)

    # 配置 - 使用统一的数据库配置
    app.config.update(
        {
            "SECRET_KEY": "cs3611-email-web-secret-key-2024",
            "WTF_CSRF_ENABLED": True,
            "WTF_CSRF_TIME_LIMIT": 3600,
            "UPLOAD_FOLDER": str(project_root / "data" / "uploads"),
            "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,  # 16MB
            "DB_PATH": DB_PATH,  # 使用统一配置中的数据库路径
            "EMAIL_STORAGE_DIR": EMAIL_STORAGE_DIR,  # 使用统一配置中的邮件存储目录
        }
    )

    print(f"📊 Web应用使用数据库: {app.config['DB_PATH']}")

    # 确保上传目录存在
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # 初始化CSRF保护
    csrf = CSRFProtect(app)
    print("✅ CSRF保护已启用")

    # Flask-Login配置
    login_manager = LoginManager()
    login_manager.init_app(app)

    if EMAIL_AUTH_AVAILABLE:
        login_manager.login_view = "email_auth.email_login"
        login_manager.login_message = "请先登录您的邮箱账户"
        print("✅ 使用邮箱认证系统")
    else:
        login_manager.login_view = "auth.login"
        login_manager.login_message = "请先登录"
        print("⚠️  使用传统认证系统")

    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        """加载用户 - 支持邮箱用户"""
        try:
            print(f"🔍 尝试加载用户: {user_id}")

            # 优先尝试邮箱用户加载器
            if EMAIL_AUTH_AVAILABLE and get_user_by_id:
                try:
                    user = get_user_by_id(user_id)
                    if user:
                        print(f"✅ 邮箱用户加载成功: {user_id}")
                        return user
                    else:
                        print(f"⚠️  邮箱用户未找到: {user_id}")
                except Exception as e:
                    print(f"❌ 邮箱用户加载失败: {e}")

            # 如果用户ID看起来像邮箱地址，尝试直接用作邮箱地址
            if EMAIL_AUTH_AVAILABLE and load_user_by_email and "@" in user_id:
                try:
                    user = load_user_by_email(user_id)
                    if user:
                        print(f"✅ 邮箱用户（按邮箱）加载成功: {user_id}")
                        return user
                except Exception as e:
                    print(f"❌ 邮箱用户（按邮箱）加载失败: {e}")

            # 后备：尝试原有的WebUser加载器（为了兼容性）
            try:
                user = WebUser.get_by_username(user_id)
                if user:
                    print(f"✅ Web用户加载成功: {user_id}")
                    return user
                else:
                    print(f"⚠️  Web用户未找到: {user_id}")
            except Exception as e:
                print(f"❌ Web用户加载失败: {e}")

            print(f"❌ 所有用户加载方式都失败: {user_id}")
            return None

        except Exception as e:
            print(f"❌ 用户加载器出现异常: {e}")
            return None

    @app.before_request
    def before_request():
        """请求前处理 - 初始化用户认证服务和邮件服务"""
        g.user_auth = UserAuth(app.config["DB_PATH"])

        # 初始化邮件服务
        try:
            from server.new_db_handler import EmailService

            g.email_service = EmailService(app.config["DB_PATH"])
            print("✅ 邮件服务初始化成功")
        except Exception as e:
            print(f"❌ 邮件服务初始化失败: {e}")
            g.email_service = None

    @app.context_processor
    def inject_template_vars():
        """注入模板变量"""
        from flask_wtf.csrf import generate_csrf

        return {
            "app_name": "CS3611 邮件客户端",
            "app_version": __version__,
            "csrf_token": generate_csrf,
        }

    # 注册蓝图
    if EMAIL_AUTH_AVAILABLE and email_auth_bp:
        app.register_blueprint(email_auth_bp, url_prefix="/auth")  # 新的邮箱认证路由
        app.register_blueprint(
            auth_bp, url_prefix="/legacy_auth"
        )  # 原有的认证路由（兼容性）
        print("✅ 邮箱认证蓝图注册成功")
    else:
        app.register_blueprint(auth_bp, url_prefix="/auth")  # 使用原有的认证系统
        print("⚠️  使用传统认证蓝图")

    app.register_blueprint(main_bp)
    app.register_blueprint(email_bp, url_prefix="/email")
    app.register_blueprint(mail_config_bp, url_prefix="/mail_config")
    app.register_blueprint(cli_api_bp, url_prefix="/api/cli")

    return app
