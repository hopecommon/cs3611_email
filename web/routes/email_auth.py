#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮箱认证路由 - 处理邮箱直接登录
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from web.email_auth import EmailAuthenticator, EmailUser, load_user_by_email
from email_providers_config import get_provider_config, is_supported_provider

email_auth_bp = Blueprint("email_auth", __name__)


@email_auth_bp.route("/email_login", methods=["GET", "POST"])
def email_login():
    """邮箱登录"""
    print(
        f"🔍 邮箱登录页面访问 - 方法: {request.method}, 已认证: {current_user.is_authenticated}"
    )

    # 临时禁用自动重定向，强制显示登录页面
    # 这样可以避免重定向循环，用户可以手动登录
    if current_user.is_authenticated:
        print(f"⚠️  用户已登录但强制显示登录页面以避免循环: {current_user.get_id()}")
        # 暂时注释掉自动重定向
        # return redirect(url_for("main.dashboard"))

    # 获取最近登录的账户
    try:
        authenticator = EmailAuthenticator()
        recent_accounts = authenticator.list_saved_accounts()[:4]  # 最多显示4个
        print(f"📋 获取到 {len(recent_accounts)} 个最近账户")
    except Exception as e:
        print(f"❌ 获取最近账户失败: {e}")
        recent_accounts = []

    if request.method == "POST":
        print("📝 处理登录表单提交")
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        remember = bool(request.form.get("remember"))

        # 基本验证
        if not email or not password:
            flash("请输入邮箱地址和密码", "error")
            return render_template(
                "auth/email_login.html", recent_accounts=recent_accounts
            )

        if "@" not in email:
            flash("请输入有效的邮箱地址", "error")
            return render_template(
                "auth/email_login.html", recent_accounts=recent_accounts
            )

        # 检查是否支持该邮箱服务商
        if not is_supported_provider(email):
            domain = email.split("@")[1]
            flash(f"暂不支持 {domain} 邮箱，请联系管理员添加支持", "error")
            return render_template(
                "auth/email_login.html", recent_accounts=recent_accounts
            )

        # 进行邮箱认证
        try:
            print(f"🔐 开始认证邮箱: {email}")
            user = authenticator.authenticate(email, password)
            if user:
                # 登录成功
                print(f"✅ 邮箱认证成功: {email}")
                login_user(user, remember=remember)
                provider_config = get_provider_config(email)
                flash(f"欢迎使用 {provider_config['name']} 邮箱！", "success")

                # 成功后重定向到仪表板
                print("🔄 认证成功，重定向到仪表板")
                return redirect(url_for("main.dashboard"))
            else:
                # 认证失败
                print(f"❌ 邮箱认证失败: {email}")
                provider_config = get_provider_config(email)
                if provider_config:
                    error_msg = f"{provider_config['name']} 认证失败，请检查邮箱地址和授权码是否正确"
                else:
                    error_msg = "邮箱认证失败，请检查邮箱地址和密码是否正确"
                flash(error_msg, "error")

        except Exception as e:
            print(f"❌ 登录过程异常: {e}")
            flash(f"登录过程中出现错误：{str(e)}", "error")

    print("📄 显示邮箱登录页面")
    return render_template("auth/email_login.html", recent_accounts=recent_accounts)


@email_auth_bp.route("/clear_session")
def clear_session():
    """清理session，解决重定向循环问题"""
    from flask import session
    from flask_login import logout_user

    print("🧹 清理用户session...")

    # 登出当前用户
    logout_user()

    # 清空session
    session.clear()

    print("✅ Session已清理")
    flash("会话已清理，请重新登录", "info")
    return redirect(url_for("email_auth.email_login"))


@email_auth_bp.route("/logout")
@login_required
def logout():
    """用户登出"""
    logout_user()
    flash("您已成功登出", "info")
    return redirect(url_for("email_auth.email_login"))


@email_auth_bp.route("/test_connection", methods=["POST"])
def test_connection():
    """测试邮箱连接（AJAX接口）"""
    try:
        email = request.json.get("email", "").strip().lower()
        password = request.json.get("password", "").strip()

        if not email or not password:
            return {"success": False, "message": "请输入邮箱地址和密码"}

        if not is_supported_provider(email):
            return {"success": False, "message": "不支持的邮箱服务商"}

        # 测试连接
        authenticator = EmailAuthenticator()
        user = authenticator.authenticate(email, password)

        if user:
            return {
                "success": True,
                "message": "邮箱连接测试成功",
                "provider": user.provider_name,
            }
        else:
            return {"success": False, "message": "邮箱认证失败，请检查邮箱地址和授权码"}

    except Exception as e:
        return {"success": False, "message": f"测试过程中出错：{str(e)}"}


@email_auth_bp.route("/providers")
def list_providers():
    """获取支持的邮箱服务商列表"""
    from email_providers_config import get_all_providers

    providers = get_all_providers()
    provider_list = []

    for domain, config in providers.items():
        provider_list.append(
            {
                "domain": domain,
                "name": config["name"],
                "auth_note": config["auth_note"],
                "help_url": config["help_url"],
            }
        )

    return render_template("auth/providers.html", providers=provider_list)
