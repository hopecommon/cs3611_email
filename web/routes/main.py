"""
主页路由 - 处理首页和仪表板
"""

from flask import Blueprint, render_template, redirect, url_for, flash, g, current_app
from flask_login import login_required, current_user
import datetime

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """首页 - 重定向到登录页面"""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    # 强制重定向到邮箱登录页面
    print("🔍 重定向到邮箱登录页面...")
    return redirect("/auth/email_login")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """用户仪表板"""
    print(
        f"🏠 仪表板访问 - 用户: {current_user.get_id()}, 已认证: {current_user.is_authenticated}"
    )

    try:
        print("📊 开始构建仪表板数据...")

        # 获取用户信息 - 兼容不同类型的用户对象
        if hasattr(current_user, "email"):
            # 邮箱用户
            print(f"📧 邮箱用户: {current_user.email}")
            user_info = {
                "email": current_user.email,
                "provider": getattr(current_user, "provider_name", "未知"),
                "login_time": (
                    current_user.last_login.strftime("%Y-%m-%d %H:%M:%S")
                    if hasattr(current_user, "last_login") and current_user.last_login
                    else "未知"
                ),
            }
        else:
            # 传统Web用户
            print(f"👤 Web用户: {current_user.username}")
            user_info = {
                "email": getattr(
                    current_user, "email", current_user.username + "@example.com"
                ),
                "provider": "Web账户",
                "login_time": (
                    current_user.last_login.strftime("%Y-%m-%d %H:%M:%S")
                    if hasattr(current_user, "last_login") and current_user.last_login
                    else "未知"
                ),
            }

        print(f"ℹ️  用户信息: {user_info}")

        # 检查邮箱配置
        smtp_config = None
        pop3_config = None

        if hasattr(current_user, "get_smtp_config"):
            smtp_config = current_user.get_smtp_config()
            print(f"📤 SMTP配置: {'可用' if smtp_config else '不可用'}")
        if hasattr(current_user, "get_pop3_config"):
            pop3_config = current_user.get_pop3_config()
            print(f"📥 POP3配置: {'可用' if pop3_config else '不可用'}")

        # 获取邮件统计（这里可以添加实际的邮件统计逻辑）
        email_stats = {"total": 0, "unread": 0, "today": 0}

        print("🎨 开始渲染仪表板模板...")
        result = render_template(
            "main/dashboard.html",
            user_info=user_info,
            email_stats=email_stats,
            smtp_ok=bool(smtp_config),
            pop3_ok=bool(pop3_config),
        )
        print("✅ 仪表板模板渲染成功")
        return result

    except Exception as e:
        print(f"❌ 仪表板异常: {e}")
        import traceback

        traceback.print_exc()
        flash(f"加载仪表板时出错：{str(e)}", "error")
        # 强制重定向到邮箱登录
        return redirect("/auth/email_login")


@main_bp.route("/about")
def about():
    """关于页面"""
    return render_template("main/about.html")


@main_bp.route("/help")
def help():
    """帮助页面"""
    return render_template("main/help.html")
