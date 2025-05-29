"""
邮箱配置路由 - 处理真实邮箱账户的配置
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
import sqlite3
from pathlib import Path

from web.forms import QuickSetupForm, MailConfigForm, TestEmailForm
from web.models import WebUser

mail_config_bp = Blueprint("mail_config", __name__)

# 常见邮箱服务商预设配置
PROVIDER_PRESETS = {
    "gmail": {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_use_tls": True,
        "pop3_server": "pop.gmail.com",
        "pop3_port": 995,
        "pop3_use_ssl": True,
    },
    "outlook": {
        "smtp_server": "smtp-mail.outlook.com",
        "smtp_port": 587,
        "smtp_use_tls": True,
        "pop3_server": "outlook.office365.com",
        "pop3_port": 995,
        "pop3_use_ssl": True,
    },
    "qq": {
        "smtp_server": "smtp.qq.com",
        "smtp_port": 587,
        "smtp_use_tls": True,
        "pop3_server": "pop.qq.com",
        "pop3_port": 995,
        "pop3_use_ssl": True,
    },
    "163": {
        "smtp_server": "smtp.163.com",
        "smtp_port": 465,
        "smtp_use_tls": False,
        "pop3_server": "pop.163.com",
        "pop3_port": 995,
        "pop3_use_ssl": True,
    },
    "126": {
        "smtp_server": "smtp.126.com",
        "smtp_port": 465,
        "smtp_use_tls": False,
        "pop3_server": "pop.126.com",
        "pop3_port": 995,
        "pop3_use_ssl": True,
    },
}


@mail_config_bp.route("/")
@login_required
def index():
    """邮箱配置主页"""
    has_config = current_user.has_mail_config()
    return render_template("mail_config/index.html", has_config=has_config)


@mail_config_bp.route("/quick_setup", methods=["GET", "POST"])
@login_required
def quick_setup():
    """快速设置邮箱"""
    form = QuickSetupForm()

    if form.validate_on_submit():
        provider = form.provider.data
        mail_display_name = form.mail_display_name.data
        email_address = form.email_address.data
        password = form.password.data

        if provider in PROVIDER_PRESETS:
            # 使用预设配置
            preset = PROVIDER_PRESETS[provider]

            # 更新用户的邮箱配置
            success = _update_user_mail_config(
                current_user.username,
                mail_display_name=mail_display_name,
                smtp_server=preset["smtp_server"],
                smtp_port=preset["smtp_port"],
                smtp_use_tls=preset["smtp_use_tls"],
                smtp_username=email_address,
                smtp_password=password,
                pop3_server=preset["pop3_server"],
                pop3_port=preset["pop3_port"],
                pop3_use_ssl=preset["pop3_use_ssl"],
                pop3_username=email_address,
                pop3_password=password,
            )

            if success:
                flash(f"成功配置{provider.upper()}邮箱！", "success")
                return redirect(url_for("mail_config.test_config"))
            else:
                flash("配置保存失败，请重试", "error")
        else:
            flash("请选择有效的邮箱服务商", "error")

    return render_template("mail_config/quick_setup.html", form=form)


@mail_config_bp.route("/advanced_setup", methods=["GET", "POST"])
@login_required
def advanced_setup():
    """高级设置邮箱"""
    form = MailConfigForm()

    # 如果是GET请求且用户已有配置，则填充表单
    if request.method == "GET" and current_user.has_mail_config():
        form.mail_display_name.data = current_user.mail_display_name
        form.smtp_server.data = current_user.smtp_server
        form.smtp_port.data = current_user.smtp_port
        form.smtp_use_tls.data = current_user.smtp_use_tls
        form.smtp_username.data = current_user.smtp_username
        form.pop3_server.data = current_user.pop3_server
        form.pop3_port.data = current_user.pop3_port
        form.pop3_use_ssl.data = current_user.pop3_use_ssl
        form.pop3_username.data = current_user.pop3_username

    if form.validate_on_submit():
        success = _update_user_mail_config(
            current_user.username,
            mail_display_name=form.mail_display_name.data,
            smtp_server=form.smtp_server.data,
            smtp_port=form.smtp_port.data,
            smtp_use_tls=form.smtp_use_tls.data,
            smtp_username=form.smtp_username.data,
            smtp_password=form.smtp_password.data,
            pop3_server=form.pop3_server.data,
            pop3_port=form.pop3_port.data,
            pop3_use_ssl=form.pop3_use_ssl.data,
            pop3_username=form.pop3_username.data,
            pop3_password=form.pop3_password.data,
        )

        if success:
            flash("邮箱配置已保存！", "success")
            return redirect(url_for("mail_config.test_config"))
        else:
            flash("配置保存失败，请重试", "error")

    return render_template("mail_config/advanced_setup.html", form=form)


@mail_config_bp.route("/test_config", methods=["GET", "POST"])
@login_required
def test_config():
    """测试邮箱配置"""
    if not current_user.has_mail_config():
        flash("请先配置邮箱", "warning")
        return redirect(url_for("mail_config.index"))

    form = TestEmailForm()
    test_results = None

    if form.validate_on_submit():
        # 测试SMTP配置
        smtp_result = _test_smtp_config(
            form.to_address.data, form.subject.data, form.content.data
        )

        # 测试POP3配置
        pop3_result = _test_pop3_config()

        test_results = {"smtp": smtp_result, "pop3": pop3_result}

        if smtp_result["success"] and pop3_result["success"]:
            flash("邮箱配置测试成功！您现在可以正常收发邮件了", "success")
        else:
            flash("邮箱配置测试失败，请检查配置信息", "error")

    return render_template(
        "mail_config/test_config.html", form=form, test_results=test_results
    )


@mail_config_bp.route("/test_pop3_connection", methods=["POST"])
@login_required
def test_pop3_connection():
    """POP3连接测试API"""
    try:
        result = _test_pop3_config()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": f"测试请求失败: {str(e)}"})


@mail_config_bp.route("/delete_config", methods=["POST"])
@login_required
def delete_config():
    """删除邮箱配置"""
    success = _clear_user_mail_config(current_user.username)

    if success:
        flash("邮箱配置已删除", "info")
    else:
        flash("删除配置失败", "error")

    return redirect(url_for("mail_config.index"))


def _update_user_mail_config(username, **config_data):
    """更新用户邮箱配置"""
    try:
        from flask import current_app
        from web.models import WebUser

        db_path = current_app.config["DB_PATH"]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 加密密码
        user = WebUser.get_by_username(username)
        if not user:
            return False

        # 准备更新数据
        encrypted_smtp_password = user._encrypt_password(
            config_data.get("smtp_password", "")
        )
        encrypted_pop3_password = user._encrypt_password(
            config_data.get("pop3_password", "")
        )

        # 更新数据库
        update_sql = """
        UPDATE users SET 
            mail_display_name = ?,
            smtp_server = ?, smtp_port = ?, smtp_use_tls = ?, 
            smtp_username = ?, encrypted_smtp_password = ?, smtp_configured = 1,
            pop3_server = ?, pop3_port = ?, pop3_use_ssl = ?, 
            pop3_username = ?, encrypted_pop3_password = ?, pop3_configured = 1
        WHERE username = ?
        """

        cursor.execute(
            update_sql,
            (
                config_data.get("mail_display_name", ""),
                config_data.get("smtp_server", ""),
                config_data.get("smtp_port", 587),
                config_data.get("smtp_use_tls", True),
                config_data.get("smtp_username", ""),
                encrypted_smtp_password,
                config_data.get("pop3_server", ""),
                config_data.get("pop3_port", 995),
                config_data.get("pop3_use_ssl", True),
                config_data.get("pop3_username", ""),
                encrypted_pop3_password,
                username,
            ),
        )

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        print(f"更新邮箱配置失败: {e}")
        return False


def _clear_user_mail_config(username):
    """清除用户邮箱配置"""
    try:
        from flask import current_app

        db_path = current_app.config["DB_PATH"]
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 清空邮箱配置字段
        update_sql = """
        UPDATE users SET 
            mail_display_name = '', smtp_server = '', smtp_port = 587, smtp_use_tls = 1,
            smtp_username = '', encrypted_smtp_password = '', smtp_configured = 0,
            pop3_server = '', pop3_port = 995, pop3_use_ssl = 1,
            pop3_username = '', encrypted_pop3_password = '', pop3_configured = 0
        WHERE username = ?
        """

        cursor.execute(update_sql, (username,))
        conn.commit()
        conn.close()

        return True

    except Exception as e:
        print(f"清除邮箱配置失败: {e}")
        return False


def _test_smtp_config(to_address, subject, content):
    """测试SMTP配置 - 集成真实SMTP客户端"""
    try:
        # 获取用户的SMTP配置
        smtp_config = current_user.get_smtp_config()
        if not smtp_config:
            return {"success": False, "error": "SMTP配置不完整"}

        # 导入SMTP客户端
        import sys
        from pathlib import Path

        project_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(project_root))

        from client.smtp_client import SMTPClient
        from common.models import Email, EmailAddress
        from datetime import datetime

        # 创建SMTP客户端
        smtp_client = SMTPClient(
            host=smtp_config["host"],
            port=smtp_config["port"],
            use_ssl=not smtp_config["use_tls"],  # 如果use_tls为True，则use_ssl为False
            username=smtp_config["username"],
            password=smtp_config["password"],
            auth_method="AUTO",
            timeout=30,
            save_sent_emails=False,  # 测试时不保存邮件
        )

        # 创建邮件对象
        from common.utils import generate_message_id

        email = Email(
            message_id=generate_message_id(),
            subject=subject,
            from_addr=EmailAddress(
                name=current_user.mail_display_name or current_user.username,
                address=smtp_config["username"],
            ),
            to_addrs=[EmailAddress(name="", address=to_address)],
            cc_addrs=[],
            bcc_addrs=[],
            text_content=content,
            html_content="",
            date=datetime.now(),
            attachments=[],
        )

        # 发送邮件
        smtp_client.connect()
        success = smtp_client.send_email(email)
        smtp_client.disconnect()

        if success:
            return {
                "success": True,
                "message": f"测试邮件已发送到 {to_address}",
                "server": smtp_config["host"],
                "port": smtp_config["port"],
            }
        else:
            return {"success": False, "error": "邮件发送失败"}

    except Exception as e:
        return {"success": False, "error": f"SMTP测试失败: {str(e)}"}


def _test_pop3_config():
    """测试POP3配置 - 集成真实POP3客户端"""
    try:
        # 获取用户的POP3配置
        pop3_config = current_user.get_pop3_config()
        if not pop3_config:
            return {"success": False, "error": "POP3配置不完整"}

        # 导入POP3客户端
        import sys
        from pathlib import Path

        project_root = Path(__file__).resolve().parent.parent.parent
        sys.path.insert(0, str(project_root))

        from client.pop3_client_legacy import POP3Client

        # 创建POP3客户端
        pop3_client = POP3Client(
            host=pop3_config["host"],
            port=pop3_config["port"],
            use_ssl=pop3_config["use_ssl"],
            username=pop3_config["username"],
            password=pop3_config["password"],
            auth_method="AUTO",
            timeout=30,
        )

        # 测试连接和获取邮箱状态
        pop3_client.connect()
        msg_count, mailbox_size = pop3_client.get_mailbox_status()
        pop3_client.disconnect()

        return {
            "success": True,
            "message": f"成功连接到POP3服务器",
            "server": pop3_config["host"],
            "port": pop3_config["port"],
            "email_count": msg_count,
            "mailbox_size": mailbox_size,
        }

    except Exception as e:
        return {"success": False, "error": f"POP3测试失败: {str(e)}"}
