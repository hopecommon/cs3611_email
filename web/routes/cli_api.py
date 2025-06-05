# -*- coding: utf-8 -*-
"""
CLI API路由 - 提供Web界面调用CLI功能的API接口
复用现有CLI模块，提供RESTful API
"""

from flask import Blueprint, request, jsonify, g
from flask_login import login_required, current_user
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from web.cli_integration import get_cli_bridge
from common.utils import setup_logging

# 设置日志
logger = setup_logging("cli_api")

cli_api_bp = Blueprint("cli_api", __name__)


@cli_api_bp.route("/account/info", methods=["GET"])
@login_required
def get_account_info():
    """获取当前账户信息"""
    try:
        bridge = get_cli_bridge()
        account_info = bridge.get_current_account_info()

        if account_info:
            return jsonify({"success": True, "data": account_info})
        else:
            return jsonify({"success": False, "error": "未找到账户信息"}), 404

    except Exception as e:
        logger.error(f"获取账户信息API失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@cli_api_bp.route("/account/list", methods=["GET"])
@login_required
def list_accounts():
    """列出所有账户"""
    try:
        bridge = get_cli_bridge()
        accounts = bridge.list_accounts()

        return jsonify({"success": True, "data": accounts})

    except Exception as e:
        logger.error(f"列出账户API失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@cli_api_bp.route("/account/switch", methods=["POST"])
@login_required
def switch_account():
    """切换账户"""
    try:
        data = request.get_json()
        account_name = data.get("account_name")

        if not account_name:
            return jsonify({"success": False, "error": "账户名称不能为空"}), 400

        bridge = get_cli_bridge()
        success = bridge.switch_account(account_name)

        if success:
            return jsonify(
                {"success": True, "message": f"已切换到账户: {account_name}"}
            )
        else:
            return jsonify({"success": False, "error": "切换账户失败"}), 500

    except Exception as e:
        logger.error(f"切换账户API失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@cli_api_bp.route("/email/stats", methods=["GET"])
@login_required
def get_email_stats():
    """获取邮件统计信息"""
    try:
        bridge = get_cli_bridge()
        email_service = bridge.get_email_service()

        # 获取当前用户邮箱
        user_email = getattr(current_user, "email", None)
        if not user_email:
            return jsonify({"success": False, "error": "无法获取用户邮箱"}), 400

        # 获取邮件统计
        stats = {
            "total_received": 0,
            "unread_received": 0,
            "total_sent": 0,
            "spam_count": 0,
        }

        try:
            # 获取接收邮件统计
            received_emails = email_service.list_emails(
                user_email=user_email, limit=10000
            )
            stats["total_received"] = len(received_emails)
            stats["unread_received"] = len(
                [e for e in received_emails if not e.get("is_read", False)]
            )

            # 获取发送邮件统计
            sent_emails = email_service.list_sent_emails(
                from_addr=user_email, limit=10000
            )
            stats["total_sent"] = len(sent_emails)

            # 获取垃圾邮件统计
            spam_emails = email_service.list_emails(
                user_email=user_email, is_spam=True, limit=10000
            )
            stats["spam_count"] = len(spam_emails)

        except Exception as e:
            logger.warning(f"获取邮件统计时出错: {e}")
            # 返回默认值，不影响API调用

        return jsonify({"success": True, "data": stats})

    except Exception as e:
        logger.error(f"获取邮件统计API失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@cli_api_bp.route("/email/receive", methods=["POST"])
@login_required
def receive_emails():
    """接收邮件"""
    try:
        data = request.get_json() or {}
        receive_type = data.get("type", "latest")  # all, latest, unread
        count = data.get("count", 5)  # 对于latest类型

        # 检查用户是否有邮件接收权限
        if not hasattr(current_user, "get_pop3_config"):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "当前用户不支持邮件接收功能，请先配置邮箱",
                    }
                ),
                400,
            )

        # 检查用户是否有POP3配置
        pop3_config = current_user.get_pop3_config()
        if not pop3_config:
            return (
                jsonify({"success": False, "error": "请先配置邮箱接收设置"}),
                400,
            )

        # 使用简化的邮件接收功能
        from web.simple_email_service import receive_simple_emails

        try:
            emails = receive_simple_emails(pop3_config, current_user.email, limit=count)
            new_count = len(emails)

            return jsonify(
                {
                    "success": True,
                    "message": (
                        f"成功接收 {new_count} 封邮件"
                        if new_count > 0
                        else "没有新邮件"
                    ),
                    "data": {
                        "new_emails": new_count,
                        "type": receive_type,
                        "emails": emails,
                    },
                }
            )
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    except Exception as e:
        logger.error(f"接收邮件API失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@cli_api_bp.route("/email/search", methods=["POST"])
@login_required
def search_emails():
    """搜索邮件"""
    try:
        data = request.get_json()
        search_type = data.get("type", "sender")  # sender, subject, content
        keyword = data.get("keyword", "")

        if not keyword:
            return jsonify({"success": False, "error": "搜索关键词不能为空"}), 400

        bridge = get_cli_bridge()
        email_service = bridge.get_email_service()

        # 获取当前用户邮箱
        user_email = getattr(current_user, "email", None)
        if not user_email:
            return jsonify({"success": False, "error": "无法获取用户邮箱"}), 400

        # 执行搜索
        search_fields = {
            "sender": ["from_addr"],
            "subject": ["subject"],
            "content": ["content"],
        }

        fields = search_fields.get(search_type, ["from_addr"])
        all_results = email_service.search_emails(keyword, search_fields=fields)

        # 过滤结果（账户隔离）
        filtered_results = []
        for email in all_results:
            # 检查是否属于当前用户
            if search_type == "sender" and email.get("type") == "sent":
                # 发送邮件：检查发件人
                if email.get("from_addr") == user_email:
                    filtered_results.append(email)
            else:
                # 接收邮件：检查收件人
                to_addrs = email.get("to_addrs", "")
                if user_email in str(to_addrs):
                    filtered_results.append(email)

        return jsonify(
            {
                "success": True,
                "data": {
                    "results": filtered_results,
                    "count": len(filtered_results),
                    "search_type": search_type,
                    "keyword": keyword,
                },
            }
        )

    except Exception as e:
        logger.error(f"搜索邮件API失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@cli_api_bp.route("/spam/keywords", methods=["GET"])
@login_required
def get_spam_keywords():
    """获取垃圾邮件关键词"""
    try:
        bridge = get_cli_bridge()
        spam_menu = bridge.spam_menu

        return jsonify(
            {
                "success": True,
                "data": {
                    "keywords": spam_menu.keywords,
                    "threshold": spam_menu.spam_filter.threshold,
                },
            }
        )

    except Exception as e:
        logger.error(f"获取垃圾邮件关键词API失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@cli_api_bp.route("/spam/keywords", methods=["POST"])
@login_required
def add_spam_keyword():
    """添加垃圾邮件关键词"""
    try:
        data = request.get_json()
        category = data.get("category", "subject")  # subject, body, sender
        keyword = data.get("keyword", "").strip()

        if not keyword:
            return jsonify({"success": False, "error": "关键词不能为空"}), 400

        if category not in ["subject", "body", "sender"]:
            return jsonify({"success": False, "error": "无效的关键词类别"}), 400

        bridge = get_cli_bridge()
        spam_menu = bridge.spam_menu

        # 检查关键词是否已存在
        if keyword in spam_menu.keywords.get(category, []):
            return jsonify({"success": False, "error": "关键词已存在"}), 400

        # 添加关键词
        spam_menu.keywords[category].append(keyword)
        success = spam_menu._save_keywords()

        if success:
            return jsonify(
                {"success": True, "message": f"成功添加{category}关键词: {keyword}"}
            )
        else:
            return jsonify({"success": False, "error": "保存关键词失败"}), 500

    except Exception as e:
        logger.error(f"添加垃圾邮件关键词API失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
