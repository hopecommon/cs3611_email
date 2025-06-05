#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮箱认证路由 - 处理邮箱直接登录
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from web.simple_email_auth import authenticate_simple_email_user, load_user_by_email
from email_providers_config import get_provider_config, is_supported_provider

email_auth_bp = Blueprint("email_auth", __name__)


@email_auth_bp.route("/email_login", methods=["GET", "POST"])
def email_login():
    """邮箱登录"""
    print(
        f"🔍 邮箱登录页面访问 - 方法: {request.method}, 已认证: {current_user.is_authenticated}"
    )

    # 如果用户已经登录，直接跳转到dashboard
    if current_user.is_authenticated:
        print(f"✅ 用户已认证，跳转到dashboard: {current_user.get_id()}")
        return redirect(url_for("main.dashboard"))

    # 获取记住的邮箱地址
    remembered_email = session.get("remembered_email", "")
    remember_email = session.get("remember_email", False)

    if request.method == "POST":
        print("📝 处理登录表单提交")
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        remember = bool(request.form.get("remember"))

        # 基本验证
        if not email or not password:
            flash("请输入邮箱地址和密码", "error")
            return render_template(
                "auth/email_login.html",
                last_email=remembered_email,
                remember_email=remember_email,
            )

        if "@" not in email:
            flash("请输入有效的邮箱地址", "error")
            return render_template(
                "auth/email_login.html",
                last_email=remembered_email,
                remember_email=remember_email,
            )

        # 检查是否支持该邮箱服务商
        if not is_supported_provider(email):
            domain = email.split("@")[1]
            flash(f"暂不支持 {domain} 邮箱，请联系管理员添加支持", "error")
            return render_template(
                "auth/email_login.html",
                last_email=remembered_email,
                remember_email=remember_email,
            )

        # 进行邮箱认证
        try:
            print(f"🔐 开始认证邮箱: {email}")

            user = authenticate_simple_email_user(email, password)

            if user:
                # 登录成功
                print(f"✅ 邮箱认证成功: {email}")
                login_user(user, remember=remember)

                # 保存邮箱地址到session（如果用户选择记住）
                if remember:
                    session["remembered_email"] = email
                    session["remember_email"] = True
                    session.permanent = True  # 使session持久化
                    print(f"💾 已保存邮箱地址到session: {email}")
                else:
                    session.pop("remembered_email", None)
                    session.pop("remember_email", None)
                    print("🗑️ 已清除session中的邮箱地址")

                provider_config = get_provider_config(email)
                flash(f"欢迎使用 {provider_config['name']} 邮箱！登录成功", "success")

                # 获取next参数，如果没有则跳转到dashboard
                next_page = request.args.get("next")
                if next_page:
                    print(f"🔄 跳转到指定页面: {next_page}")
                    return redirect(next_page)
                else:
                    print("🔄 跳转到dashboard")
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
            import traceback

            traceback.print_exc()
            flash(f"登录过程中出现错误：{str(e)}", "error")

    print("📄 显示邮箱登录页面")
    return render_template(
        "auth/email_login.html",
        last_email=remembered_email,
        remember_email=remember_email,
    )


@email_auth_bp.route("/clear_session")
def clear_session():
    """清理session，解决重定向循环问题"""
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
    # 检查是否需要保留邮箱地址
    keep_email = session.get("remember_email", False)
    remembered_email = session.get("remembered_email", "")

    logout_user()

    # 清除session但保留邮箱地址（如果用户选择记住）
    if keep_email and remembered_email:
        # 清除所有数据但保留邮箱地址
        temp_email = remembered_email
        temp_remember = True
        session.clear()
        session["remembered_email"] = temp_email
        session["remember_email"] = temp_remember
        print(f"🔄 登出但保留邮箱地址: {temp_email}")
    else:
        session.clear()
        print("🗑️ 登出并清除所有session数据")

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

        # 使用简化认证测试连接
        user = authenticate_simple_email_user(email, password)
        if user:
            return {
                "success": True,
                "message": f"连接成功！支持 {user.provider_name}",
                "provider": user.provider_name,
            }
        else:
            return {"success": False, "message": "认证失败，请检查邮箱地址和密码"}

    except Exception as e:
        return {"success": False, "message": f"连接测试失败：{str(e)}"}


@email_auth_bp.route("/providers")
def list_providers():
    """列出支持的邮箱服务商"""
    from email_providers_config import get_all_providers

    providers = get_all_providers()
    return render_template("auth/providers.html", providers=providers)
