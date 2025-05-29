"""
API路由 - 提供JSON API接口
"""

from flask import Blueprint, jsonify, request, g
from flask_login import login_required, current_user

api_bp = Blueprint("api", __name__)


@api_bp.route("/emails")
@login_required
def get_emails():
    """获取邮件列表API"""
    try:
        email_service = g.email_service
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        folder = request.args.get("folder", "inbox")

        if folder == "sent":
            emails = email_service.list_sent_emails(
                limit=per_page, offset=(page - 1) * per_page
            )
        else:
            emails = email_service.list_emails(
                limit=per_page, offset=(page - 1) * per_page
            )

        return jsonify(
            {"success": True, "emails": emails, "page": page, "per_page": per_page}
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/email/<message_id>")
@login_required
def get_email(message_id):
    """获取单个邮件API"""
    try:
        email_service = g.email_service
        email = email_service.get_email(message_id, include_content=True)

        if not email:
            return jsonify({"success": False, "error": "邮件不存在"}), 404

        return jsonify({"success": True, "email": email})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/email/<message_id>/mark_read", methods=["POST"])
@login_required
def mark_read(message_id):
    """标记邮件为已读API"""
    try:
        email_service = g.email_service
        success = email_service.mark_email_as_read(message_id)

        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
