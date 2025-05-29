"""
用户认证路由 - 处理登录、登出、注册
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, g
from flask_login import login_user, logout_user, login_required, current_user

from ..forms import LoginForm
from ..models import WebUser

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """用户登录"""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember = form.remember_me.data

        # 验证用户
        user = WebUser.authenticate(username, password)

        if user:
            login_user(user, remember=remember)
            flash(f"欢迎回来，{user.full_name}！", "success")

            # 重定向到原来要访问的页面或仪表板
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("main.dashboard"))
        else:
            flash("用户名或密码错误，请重试。", "error")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash("您已成功登出。", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """用户注册"""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        password_confirm = request.form.get("password_confirm", "").strip()
        full_name = request.form.get("full_name", "").strip()

        # 基本验证
        errors = []

        if not username:
            errors.append("请输入用户名")
        elif len(username) < 3:
            errors.append("用户名至少3个字符")

        if not email:
            errors.append("请输入邮箱地址")
        elif "@" not in email:
            errors.append("请输入有效的邮箱地址")

        if not password:
            errors.append("请输入密码")
        elif len(password) < 6:
            errors.append("密码至少6个字符")

        if password != password_confirm:
            errors.append("两次输入的密码不一致")

        if errors:
            for error in errors:
                flash(error, "error")
        else:
            # 尝试创建用户
            user = WebUser.create(username, email, password, full_name)

            if user:
                flash("注册成功！请使用您的用户名和密码登录。", "success")
                return redirect(url_for("auth.login"))
            else:
                flash("注册失败，用户名或邮箱可能已被使用。", "error")

    return render_template("auth/register.html")


@auth_bp.route("/profile")
@login_required
def profile():
    """用户资料"""
    return render_template("auth/profile.html")
