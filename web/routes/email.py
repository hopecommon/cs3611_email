"""
邮件路由 - 处理邮件相关功能
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
)
from flask_login import login_required, current_user
import uuid
import datetime
import os

email_bp = Blueprint("email", __name__)


@email_bp.route("/inbox")
@login_required
def inbox():
    """收件箱"""
    try:
        email_service = g.email_service
        page = request.args.get("page", 1, type=int)
        per_page = 20

        # 如果是邮箱用户，先尝试拉取新邮件
        if hasattr(current_user, "get_pop3_config"):
            try:
                fetch_result = _fetch_new_emails()
                if fetch_result.get("new_emails", 0) > 0:
                    flash(f"成功拉取 {fetch_result['new_emails']} 封新邮件", "success")
                elif not fetch_result.get(
                    "success"
                ) and "请重新登录" in fetch_result.get("error", ""):
                    flash(
                        '邮件拉取需要重新登录。<a href="/auth/email_login" class="alert-link">点击重新登录</a>',
                        "warning",
                    )
            except Exception as e:
                print(f"⚠️  拉取邮件失败: {e}")
                # 不影响页面显示，只是无法拉取新邮件

        # 获取邮件列表 - 按当前用户过滤
        emails = email_service.list_emails(
            user_email=current_user.email, limit=per_page, offset=(page - 1) * per_page
        )

        # 获取总数用于分页
        total = email_service.get_email_count(user_email=current_user.email)

        return render_template(
            "email/inbox.html", emails=emails, page=page, per_page=per_page, total=total
        )
    except Exception as e:
        flash(f"加载收件箱时出错: {str(e)}", "error")
        return render_template(
            "email/inbox.html", emails=[], page=1, per_page=20, total=0
        )


@email_bp.route("/sent")
@login_required
def sent():
    """发件箱"""
    try:
        email_service = g.email_service
        page = request.args.get("page", 1, type=int)
        per_page = 20

        # 获取已发送邮件列表，确保按当前用户过滤
        emails_list_of_dicts = email_service.list_sent_emails(
            from_addr=current_user.email,  # 按当前用户过滤
            limit=per_page,
            offset=(page - 1) * per_page,
        )

        # 获取总数用于分页 (确保按当前用户过滤)
        # TODO: 实现更高效的 EmailService.count_sent_emails(from_addr) 方法
        total_sent_for_user = len(
            email_service.list_sent_emails(from_addr=current_user.email, limit=100000)
        )

        # 日期转换逻辑 (与dashboard中的类似)
        def convert_date_in_emails_local(email_list_local):
            for email_dict in email_list_local:
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
                            current_app.logger.warning(
                                f"无法解析发件箱日期字符串: {email_dict.get('date')} for email {email_dict.get('message_id')}"
                            )
                            pass  # 保留原样或设为 None
                elif email_dict.get("date") and not isinstance(
                    email_dict["date"], datetime.datetime
                ):
                    pass  # 类型正确或已经是None
            return email_list_local

        emails_for_template = convert_date_in_emails_local(emails_list_of_dicts)

        return render_template(
            "email/sent.html",
            emails=emails_for_template,
            page=page,
            per_page=per_page,
            total=total_sent_for_user,
        )
    except Exception as e:
        current_app.logger.error(f"加载发件箱时出错: {e}", exc_info=True)
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
            # 获取表单数据
            to_addresses = request.form.get("to_addresses", "").strip()
            cc_addresses = request.form.get("cc_addresses", "").strip()
            bcc_addresses = request.form.get("bcc_addresses", "").strip()
            subject = request.form.get("subject", "").strip()
            content = request.form.get("content", "").strip()
            content_type = request.form.get("content_type", "html")
            priority = request.form.get("priority", "normal")
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

            # 生成邮件ID
            message_id = f"<{uuid.uuid4()}@localhost>"

            # 构建邮件内容
            if content_type == "html":
                # 简单的HTML包装
                html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{subject}</title>
</head>
<body>
    {content}
</body>
</html>"""
            else:
                html_content = content

            # 当前用户邮箱作为发件人
            from_addr = current_user.email

            if action == "send":
                # 发送邮件 - 这里先保存到发件箱，实际发送功能需要集成SMTP客户端
                email_service = g.email_service

                success = email_service.save_sent_email(
                    message_id=message_id,
                    from_addr=from_addr,
                    to_addrs=to_list,
                    cc_addrs=cc_list if cc_list else None,
                    bcc_addrs=bcc_list if bcc_list else None,
                    subject=subject,
                    content=html_content,
                    date=datetime.datetime.now(),
                )

                if success:
                    flash(f'邮件已发送给 {", ".join(to_list)}', "success")
                    return redirect(url_for("email.sent"))
                else:
                    flash("邮件发送失败，请重试", "error")

            elif action == "draft":
                # 保存草稿 - 这里可以扩展草稿功能
                flash("草稿保存功能待实现", "info")

        except Exception as e:
            flash(f"处理邮件时出错: {str(e)}", "error")

    return render_template("email/compose.html")


@email_bp.route("/view/<message_id>")
@login_required
def view(message_id):
    """查看邮件详情"""
    try:
        email_service = g.email_service
        email = email_service.get_email(message_id, include_content=True)

        if not email:
            flash("邮件不存在或已被删除", "error")
            return redirect(url_for("email.inbox"))

        # 标记为已读
        email_service.mark_email_as_read(message_id)

        return render_template("email/view.html", email=email)
    except Exception as e:
        flash(f"加载邮件时出错: {str(e)}", "error")
        return redirect(url_for("email.inbox"))


@email_bp.route("/view_sent/<message_id>")
@login_required
def view_sent(message_id):
    """查看已发送邮件详情"""
    try:
        email_service = g.email_service
        email = email_service.get_sent_email(message_id, include_content=True)

        if not email:
            flash("邮件不存在或已被删除", "error")
            return redirect(url_for("email.sent"))

        # 转换日期字符串为 datetime 对象
        if email.get("date") and isinstance(email["date"], str):
            try:
                email["date"] = datetime.datetime.fromisoformat(email["date"])
            except ValueError:
                for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                    try:
                        email["date"] = datetime.datetime.strptime(email["date"], fmt)
                        break
                    except ValueError:
                        continue
                else:
                    current_app.logger.warning(
                        f"无法解析已发送邮件详情页的日期: {email.get('date')} for email {message_id}"
                    )
                    # 如果所有格式都失败，可以选择保留字符串或设置为None
                    # email["date"] = None # 或者不改变，让模板处理
                    pass

        return render_template("email/view_sent.html", email=email)
    except Exception as e:
        current_app.logger.error(f"加载已发送邮件详情时出错: {e}", exc_info=True)
        flash(f"加载邮件时出错: {str(e)}", "error")
        return redirect(url_for("email.sent"))


@email_bp.route("/download_attachment/<message_id>/<filename>")
@login_required
def download_attachment(message_id, filename):
    """下载邮件附件"""
    try:
        from flask import send_file
        import os
        from common.config import EMAIL_STORAGE_DIR

        # 获取邮件内容
        email_service = g.email_service
        email = email_service.get_email(message_id, include_content=True)

        if not email:
            flash("邮件不存在", "error")
            return redirect(url_for("email.inbox"))

        # 解析邮件获取附件
        from common.email_format_handler import EmailFormatHandler

        content = email_service.content_manager.get_content(message_id, email)

        if not content:
            flash("无法获取邮件内容", "error")
            return redirect(url_for("email.view", message_id=message_id))

        # 解析邮件
        parsed_email = EmailFormatHandler.parse_mime_message(content)

        # 查找指定的附件
        target_attachment = None
        for attachment in parsed_email.attachments:
            if attachment.filename == filename:
                target_attachment = attachment
                break

        if not target_attachment:
            flash(f"附件 {filename} 不存在", "error")
            return redirect(url_for("email.view", message_id=message_id))

        # 创建临时文件
        import tempfile
        import base64

        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, filename)

        # 解码附件内容并保存到临时文件
        try:
            # 解码附件数据
            if hasattr(target_attachment, "content") and target_attachment.content:
                # 使用content属性
                if isinstance(target_attachment.content, str):
                    attachment_data = base64.b64decode(target_attachment.content)
                else:
                    attachment_data = target_attachment.content
            else:
                flash("附件数据为空", "error")
                return redirect(url_for("email.view", message_id=message_id))

            with open(temp_file_path, "wb") as f:
                f.write(attachment_data)

            # 发送文件
            return send_file(
                temp_file_path,
                as_attachment=True,
                download_name=filename,
                mimetype=target_attachment.content_type,
            )

        except Exception as decode_e:
            print(f"❌ 解码附件失败: {decode_e}")
            flash(f"附件解码失败: {str(decode_e)}", "error")
            return redirect(url_for("email.view", message_id=message_id))

    except Exception as e:
        print(f"❌ 下载附件失败: {e}")
        flash(f"下载附件失败: {str(e)}", "error")
        return redirect(url_for("email.inbox"))


@email_bp.route("/delete/<message_id>")
@login_required
def delete(message_id):
    """删除邮件"""
    try:
        email_service = g.email_service
        success = email_service.delete_email(message_id)

        if success:
            flash("邮件已删除", "success")
        else:
            flash("删除邮件失败", "error")
    except Exception as e:
        flash(f"删除邮件时出错: {str(e)}", "error")

    return redirect(url_for("email.inbox"))


@email_bp.route("/delete_sent/<message_id>", methods=["GET", "POST"])
@login_required
def delete_sent(message_id):
    """删除已发送邮件"""
    try:
        email_service = g.email_service
        success = email_service.delete_sent_email_metadata(message_id)

        if success:
            flash("邮件已从发件箱删除", "success")
        else:
            flash("删除邮件失败", "error")
    except Exception as e:
        current_app.logger.error(f"删除已发送邮件时出错: {e}", exc_info=True)
        flash(f"删除邮件时出错: {str(e)}", "error")

    return redirect(url_for("email.sent"))


@email_bp.route("/mark_spam/<message_id>")
@login_required
def mark_spam(message_id):
    """标记为垃圾邮件"""
    try:
        email_service = g.email_service
        success = email_service.mark_email_as_spam(message_id)

        if success:
            flash("邮件已标记为垃圾邮件", "info")
        else:
            flash("标记失败", "error")

        return redirect(url_for("email.inbox"))
    except Exception as e:
        flash(f"标记垃圾邮件时出错: {str(e)}", "error")
        return redirect(url_for("email.inbox"))


@email_bp.route("/refresh_inbox")
@login_required
def refresh_inbox():
    """手动刷新收件箱，拉取新邮件"""
    try:
        if hasattr(current_user, "get_pop3_config"):
            fetch_result = _fetch_new_emails()
            if fetch_result.get("success"):
                new_count = fetch_result.get("new_emails", 0)
                if new_count > 0:
                    flash(f"成功拉取 {new_count} 封新邮件！", "success")
                else:
                    flash("没有新邮件", "info")
            else:
                error_msg = fetch_result.get("error", "未知错误")
                if "请重新登录" in error_msg:
                    flash(
                        '邮件拉取需要重新登录以更新密码加密方式。<a href="/auth/email_login" class="alert-link">点击重新登录</a>',
                        "warning",
                    )
                else:
                    flash(f"拉取邮件失败: {error_msg}", "error")
        else:
            flash("当前用户不支持邮件拉取功能", "warning")
    except Exception as e:
        flash(f"刷新邮件时出错: {str(e)}", "error")

    return redirect(url_for("email.inbox"))


def _fetch_new_emails():
    """从POP3服务器拉取新邮件"""
    try:
        import poplib
        import email
        from email.header import decode_header
        import uuid

        # 检查用户是否需要重新认证
        if hasattr(current_user, "needs_reauth") and current_user.needs_reauth:
            print("⚠️  用户需要重新认证")
            return {
                "success": False,
                "error": "账户使用旧的加密方式，请重新登录以更新密码加密方式",
            }

        # 获取用户的POP3配置
        pop3_config = current_user.get_pop3_config()
        if not pop3_config:
            return {"success": False, "error": "POP3配置不可用"}

        # 连接POP3服务器
        if pop3_config.get("use_ssl"):
            server = poplib.POP3_SSL(pop3_config["host"], pop3_config["port"])
        else:
            server = poplib.POP3(pop3_config["host"], pop3_config["port"])

        # 登录
        server.user(current_user.email)
        # 从config中获取密码，如果没有则跳过
        password = pop3_config.get("password")
        if not password:
            print("⚠️  POP3密码不可用，跳过邮件拉取")
            return {
                "success": False,
                "error": "POP3密码不可用，请重新登录以更新密码加密方式",
            }

        server.pass_(password)

        # 获取邮件数量
        num_messages = len(server.list()[1])
        print(f"📮 POP3服务器上有 {num_messages} 封邮件")

        if num_messages == 0:
            server.quit()
            return {"success": True, "new_emails": 0}

        new_emails = 0
        email_service = g.email_service

        # 只拉取最近10封邮件（避免一次性拉取太多）
        start_msg = max(1, num_messages - 9)
        for msg_num in range(start_msg, num_messages + 1):
            try:
                # 获取邮件
                raw_email = b"\n".join(server.retr(msg_num)[1])
                msg = email.message_from_bytes(raw_email)

                # 获取邮件头信息
                message_id = msg.get("Message-ID", f"<{uuid.uuid4()}@pop3-fetch>")
                from_addr = msg.get("From", "unknown@unknown.com")
                to_addr = msg.get("To", current_user.email)
                subject = msg.get("Subject", "无主题")
                date_str = msg.get("Date", "")

                # 解码主题
                if subject:
                    decoded_parts = decode_header(subject)
                    subject = "".join(
                        [
                            (
                                part.decode(encoding or "utf-8")
                                if isinstance(part, bytes)
                                else part
                            )
                            for part, encoding in decoded_parts
                        ]
                    )

                # 检查邮件是否已存在
                existing_email = email_service.get_email(message_id)
                if existing_email:
                    continue  # 跳过已存在的邮件

                # 获取邮件内容
                content = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                content = payload.decode(
                                    part.get_content_charset() or "utf-8",
                                    errors="ignore",
                                )
                            break
                        elif part.get_content_type() == "text/html":
                            payload = part.get_payload(decode=True)
                            if payload:
                                content = payload.decode(
                                    part.get_content_charset() or "utf-8",
                                    errors="ignore",
                                )
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        content = payload.decode(
                            msg.get_content_charset() or "utf-8", errors="ignore"
                        )

                # 解析日期
                email_date = datetime.datetime.now()
                if date_str:
                    try:
                        from email.utils import parsedate_to_datetime

                        email_date = parsedate_to_datetime(date_str)
                    except:
                        pass

                # 保存完整的邮件内容（包括原始邮件）
                raw_email_str = raw_email.decode("utf-8", errors="ignore")
                success = email_service.save_email(
                    message_id=message_id,
                    from_addr=from_addr,
                    to_addrs=[current_user.email],
                    subject=subject,
                    content=raw_email_str,  # 保存完整的原始邮件
                    date=email_date,
                )

                if success:
                    new_emails += 1
                    print(f"✅ 保存邮件: {subject[:50]}...")

            except Exception as e:
                print(f"❌ 处理邮件 {msg_num} 失败: {e}")
                continue

        server.quit()
        print(f"📬 成功拉取 {new_emails} 封新邮件")
        return {"success": True, "new_emails": new_emails}

    except Exception as e:
        print(f"❌ 拉取邮件失败: {e}")
        return {"success": False, "error": str(e)}


@email_bp.route("/search")
@login_required
def search():
    """邮件搜索页面"""
    query = request.args.get("q", "").strip()
    search_results = []

    if query:
        try:
            email_service = g.email_service
            # 搜索邮件
            search_results = email_service.search_emails(
                query=query,
                search_fields=["subject", "from_addr", "content"],
                include_sent=True,
                include_received=True,
                limit=50,
            )

            # 转换日期格式
            for email in search_results:
                if email.get("date") and isinstance(email["date"], str):
                    try:
                        email["date"] = datetime.datetime.fromisoformat(email["date"])
                    except ValueError:
                        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                            try:
                                email["date"] = datetime.datetime.strptime(
                                    email["date"], fmt
                                )
                                break
                            except ValueError:
                                continue
                        else:
                            current_app.logger.warning(
                                f"无法解析搜索结果中的日期: {email.get('date')}"
                            )

        except Exception as e:
            current_app.logger.error(f"搜索邮件时出错: {e}", exc_info=True)
            flash(f"搜索时出错: {str(e)}", "error")

    return render_template("email/search.html", query=query, results=search_results)
