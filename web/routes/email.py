"""
邮件路由 - 处理邮件相关功能（重构版）
"""

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    g,
    current_app,
    jsonify,
)
from flask_login import login_required, current_user
import datetime
import os

# 导入简化的邮件服务
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from web.simple_email_service import get_email_service

email_bp = Blueprint("email", __name__)


@email_bp.route("/inbox")
@login_required
def inbox():
    """收件箱"""
    try:
        print(f"📥 访问收件箱 - 用户: {current_user.email}")

        # 获取简化的邮件服务
        email_service = get_email_service(current_user)

        # 先尝试接收新邮件
        try:
            receive_result = email_service.receive_emails(limit=20, only_new=True)
            if (
                receive_result.get("success")
                and receive_result.get("new_emails", 0) > 0
            ):
                flash(f"成功接收 {receive_result['new_emails']} 封新邮件", "success")
        except Exception as e:
            print(f"⚠️  接收新邮件失败: {e}")
            # 不影响页面显示

        # 获取邮件列表
        page = request.args.get("page", 1, type=int)
        per_page = 20

        inbox_result = email_service.get_inbox_emails(page=page, per_page=per_page)

        if inbox_result.get("success"):
            emails = inbox_result["emails"]
            total = inbox_result["total"]
        else:
            emails = []
            total = 0
            flash(f"获取邮件列表失败: {inbox_result.get('error', '未知错误')}", "error")

        return render_template(
            "email/inbox.html", emails=emails, page=page, per_page=per_page, total=total
        )

    except Exception as e:
        print(f"❌ 收件箱页面异常: {e}")
        flash(f"加载收件箱时出错: {str(e)}", "error")
        return render_template(
            "email/inbox.html", emails=[], page=1, per_page=20, total=0
        )


@email_bp.route("/sent")
@login_required
def sent():
    """发件箱"""
    try:
        print(f"📤 访问发件箱 - 用户: {current_user.email}")

        # 获取简化的邮件服务
        email_service = get_email_service(current_user)

        page = request.args.get("page", 1, type=int)
        per_page = 20

        sent_result = email_service.get_sent_emails(page=page, per_page=per_page)

        if sent_result.get("success"):
            emails = sent_result["emails"]
            total = sent_result["total"]

            # 日期格式转换
            for email_dict in emails:
                if email_dict.get("date") and isinstance(email_dict["date"], str):
                    try:
                        email_dict["date"] = datetime.datetime.fromisoformat(
                            email_dict["date"]
                        )
                    except ValueError:
                        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                            try:
                                email_dict["date"] = datetime.datetime.strptime(
                                    email_dict["date"], fmt
                                )
                                break
                            except ValueError:
                                continue
        else:
            emails = []
            total = 0
            flash(f"获取发件箱失败: {sent_result.get('error', '未知错误')}", "error")

        return render_template(
            "email/sent.html",
            emails=emails,
            page=page,
            per_page=per_page,
            total=total,
        )

    except Exception as e:
        print(f"❌ 发件箱页面异常: {e}")
        flash(f"加载发件箱时出错: {str(e)}", "error")
        return render_template(
            "email/sent.html", emails=[], page=1, per_page=20, total=0
        )


@email_bp.route("/compose", methods=["GET", "POST"])
@login_required
def compose():
    """写邮件"""
    if request.method == "POST":
        try:
            print(f"📝 处理邮件发送 - 用户: {current_user.email}")

            # 获取表单数据
            to_addresses = request.form.get("to_addresses", "").strip()
            cc_addresses = request.form.get("cc_addresses", "").strip()
            bcc_addresses = request.form.get("bcc_addresses", "").strip()
            subject = request.form.get("subject", "").strip()
            content = request.form.get("content", "").strip()
            content_type = request.form.get("content_type", "html")
            action = request.form.get("action", "send")

            # 基本验证
            if not to_addresses:
                flash("请输入收件人地址", "error")
                return render_template("email/compose.html")

            if not subject:
                flash("请输入邮件主题", "error")
                return render_template("email/compose.html")

            if not content:
                flash("请输入邮件内容", "error")
                return render_template("email/compose.html")

            # 处理收件人地址
            to_list = [addr.strip() for addr in to_addresses.split(",") if addr.strip()]
            cc_list = [
                addr.strip()
                for addr in cc_addresses.split(",")
                if cc_addresses and addr.strip()
            ]
            bcc_list = [
                addr.strip()
                for addr in bcc_addresses.split(",")
                if bcc_addresses and addr.strip()
            ]

            # 验证邮箱地址格式
            import re

            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

            for addr in to_list + cc_list + bcc_list:
                if not re.match(email_pattern, addr):
                    flash(f"无效的邮箱地址: {addr}", "error")
                    return render_template("email/compose.html")

            # 处理附件
            attachments = []
            uploaded_files = request.files.getlist("attachments")
            for file in uploaded_files:
                if file and file.filename:
                    attachments.append(file)

            if action == "send":
                # 发送邮件
                print(f"📧 发送邮件: {subject} -> {to_list}")

                email_service = get_email_service(current_user)
                send_result = email_service.send_email(
                    to_addresses=to_list,
                    subject=subject,
                    content=content,
                    cc_addresses=cc_list if cc_list else None,
                    bcc_addresses=bcc_list if bcc_list else None,
                    attachments=attachments if attachments else None,
                    content_type=content_type,
                )

                if send_result.get("success"):
                    flash("邮件发送成功！", "success")
                    return redirect(url_for("email.sent"))
                else:
                    flash(
                        f"邮件发送失败: {send_result.get('error', '未知错误')}", "error"
                    )
                    return render_template("email/compose.html")
            else:
                # 保存草稿（暂不实现）
                flash("草稿功能暂未实现", "info")
                return render_template("email/compose.html")

        except Exception as e:
            print(f"❌ 邮件发送异常: {e}")
            flash(f"发送邮件时出错: {str(e)}", "error")
            return render_template("email/compose.html")

    # GET请求，显示编辑页面
    return render_template("email/compose.html")


@email_bp.route("/view/<message_id>")
@login_required
def view(message_id):
    """查看邮件详情"""
    try:
        print(f"👁️ 查看邮件: {message_id}")

        email_service = get_email_service(current_user)
        email_result = email_service.get_email_by_id(message_id)

        if email_result.get("success"):
            email = email_result["email"]
            return render_template("email/view.html", email=email)
        else:
            flash(f"邮件不存在或无权访问: {message_id}", "error")
            return redirect(url_for("email.inbox"))

    except Exception as e:
        print(f"❌ 查看邮件异常: {e}")
        flash(f"查看邮件时出错: {str(e)}", "error")
        return redirect(url_for("email.inbox"))


@email_bp.route("/delete/<message_id>")
@login_required
def delete(message_id):
    """删除邮件"""
    try:
        print(f"🗑️ 删除邮件: {message_id}")

        email_service = get_email_service(current_user)
        delete_result = email_service.delete_email(message_id)

        if delete_result.get("success"):
            flash("邮件删除成功", "success")
        else:
            flash(f"邮件删除失败: {delete_result.get('error', '未知错误')}", "error")

    except Exception as e:
        print(f"❌ 删除邮件异常: {e}")
        flash(f"删除邮件时出错: {str(e)}", "error")

    return redirect(url_for("email.inbox"))


@email_bp.route("/refresh_inbox")
@login_required
def refresh_inbox():
    """刷新收件箱"""
    try:
        print(f"🔄 刷新收件箱 - 用户: {current_user.email}")

        email_service = get_email_service(current_user)
        receive_result = email_service.receive_emails(limit=50, only_new=True)

        if receive_result.get("success"):
            new_count = receive_result.get("new_emails", 0)
            if new_count > 0:
                flash(f"成功接收 {new_count} 封新邮件", "success")
            else:
                flash("没有新邮件", "info")
        else:
            flash(f"刷新失败: {receive_result.get('error', '未知错误')}", "error")

    except Exception as e:
        print(f"❌ 刷新收件箱异常: {e}")
        flash(f"刷新收件箱时出错: {str(e)}", "error")

    return redirect(url_for("email.inbox"))


@email_bp.route("/test_connection")
@login_required
def test_connection():
    """测试邮箱连接"""
    try:
        print(f"🔧 测试邮箱连接 - 用户: {current_user.email}")

        email_service = get_email_service(current_user)
        test_result = email_service.test_connection()

        if test_result.get("success"):
            results = test_result.get("results", {})
            smtp_ok = results.get("smtp", False)
            pop3_ok = results.get("pop3", False)

            if smtp_ok and pop3_ok:
                flash("邮箱连接测试成功：SMTP和POP3都正常", "success")
            elif smtp_ok:
                flash("SMTP连接正常，POP3连接失败", "warning")
            elif pop3_ok:
                flash("POP3连接正常，SMTP连接失败", "warning")
            else:
                flash("邮箱连接测试失败：SMTP和POP3都无法连接", "error")
        else:
            flash(f"连接测试失败: {test_result.get('error', '未知错误')}", "error")

    except Exception as e:
        print(f"❌ 测试连接异常: {e}")
        flash(f"测试连接时出错: {str(e)}", "error")

    return redirect(url_for("main.dashboard"))


# 保留一些原有的路由以兼容性（简化实现）
@email_bp.route("/view_sent/<message_id>")
@login_required
def view_sent(message_id):
    """查看已发送邮件详情"""
    return view(message_id)  # 直接复用view函数


@email_bp.route("/download_attachment/<message_id>/<filename>")
@login_required
def download_attachment(message_id, filename):
    """下载附件（暂不实现）"""
    flash("附件下载功能暂未实现", "info")
    return redirect(url_for("email.view", message_id=message_id))


@email_bp.route("/delete_sent/<message_id>", methods=["GET", "POST"])
@login_required
def delete_sent(message_id):
    """删除已发送邮件"""
    return delete(message_id)  # 直接复用delete函数


@email_bp.route("/mark_spam/<message_id>")
@login_required
def mark_spam(message_id):
    """标记垃圾邮件（暂不实现）"""
    flash("垃圾邮件标记功能暂未实现", "info")
    return redirect(url_for("email.inbox"))


@email_bp.route("/search")
@login_required
def search():
    """搜索邮件（暂不实现）"""
    flash("邮件搜索功能暂未实现", "info")
    return redirect(url_for("email.inbox"))


@email_bp.route("/api/email/reauth", methods=["POST"])
@login_required
def reauth_email():
    """重新认证邮件账户"""
    try:
        from flask import session
        from flask_login import logout_user

        # 清理session并重定向到登录页面
        logout_user()
        session.clear()

        return jsonify(
            {
                "success": True,
                "message": "请重新登录",
                "redirect_url": url_for("email_auth.email_login"),
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": f"重新认证失败: {str(e)}"})
