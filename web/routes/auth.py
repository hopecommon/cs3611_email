"""
用户认证路由 - 处理登录、登出、注册
"""

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import logout_user, login_required

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """重定向到邮箱登录"""
    return redirect(url_for("email_auth.email_login"))


@auth_bp.route("/logout")
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash("您已成功登出。", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """重定向到邮箱登录（注册功能已集成到邮箱登录中）"""
    flash("请使用邮箱地址直接登录，系统会自动为新用户创建账户", "info")
    return redirect(url_for("email_auth.email_login"))


@auth_bp.route("/profile")
@login_required
def profile():
    """用户资料"""
    return render_template("auth/profile.html")
