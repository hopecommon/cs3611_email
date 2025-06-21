#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化Web邮件客户端 - 基于CLI底层实现
直接复用CLI的稳定逻辑，避免复杂的web层封装
"""

import os
import sys
import json
import datetime
from pathlib import Path
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    jsonify,
)
from werkzeug.utils import secure_filename

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

# 导入CLI模块
from cli.send_menu import SendEmailMenu
from cli.receive_menu import ReceiveEmailMenu
from cli.account_manager import AccountManager
from cli.provider_manager import ProviderManager
from common.models import Email, EmailAddress, Attachment
from common.utils import setup_logging, generate_message_id
from client.smtp_client import SMTPClient
from client.pop3_client_refactored import POP3Client

# 设置日志
logger = setup_logging("simple_web_client")

app = Flask(__name__)
app.config["SECRET_KEY"] = "your-secret-key-change-this"
app.config["UPLOAD_FOLDER"] = "uploads"

# 确保上传目录存在
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# 模拟CLI的主类，为web提供接口
class WebCLIBridge:
    """Web和CLI之间的桥接类"""

    def __init__(self):
        self.account_manager = AccountManager()
        self.provider_manager = ProviderManager()
        self.current_account = None
        self.smtp_client = None
        self.pop3_client = None

    def load_account(self, email):
        """加载邮箱账户"""
        try:
            # 获取所有账户名列表
            account_names = self.account_manager.list_accounts()

            # 遍历账户名，找到匹配的邮箱
            for account_name in account_names:
                account = self.account_manager.get_account(account_name)
                if account and account.get("email") == email:
                    self.current_account = account
                    logger.info(f"成功加载账户: {email}")
                    return True

            logger.warning(f"未找到邮箱账户: {email}")
            return False
        except Exception as e:
            logger.error(f"加载账户失败: {e}")
            return False

    def get_current_account_info(self):
        """获取当前账户信息"""
        if not self.current_account:
            return None
        return {
            "email": self.current_account.get("email"),
            "display_name": self.current_account.get("display_name", ""),
            "provider": self.current_account.get(
                "notes", "未知"
            ),  # notes字段包含服务商信息
        }

    def get_smtp_config(self):
        """获取SMTP配置"""
        if not self.current_account:
            logger.warning("当前没有加载的账户")
            return None

        smtp_config = self.current_account.get("smtp", {})
        if not smtp_config:
            logger.warning("账户中没有SMTP配置")
            return None

        # 添加用户名和密码到配置中
        smtp_config = smtp_config.copy()
        smtp_config["username"] = self.current_account.get("email")
        smtp_config["password"] = self.current_account.get("password")

        logger.info(f"获取SMTP配置: {smtp_config['host']}:{smtp_config['port']}")
        return smtp_config

    def get_pop3_config(self):
        """获取POP3配置"""
        if not self.current_account:
            logger.warning("当前没有加载的账户")
            return None

        pop3_config = self.current_account.get("pop3", {})
        if not pop3_config:
            logger.warning("账户中没有POP3配置")
            return None

        # 添加用户名和密码到配置中
        pop3_config = pop3_config.copy()
        pop3_config["username"] = self.current_account.get("email")
        pop3_config["password"] = self.current_account.get("password")

        logger.info(f"获取POP3配置: {pop3_config['host']}:{pop3_config['port']}")
        return pop3_config

    def add_account(self, account_data):
        """添加新账户"""
        try:
            # 提取参数
            email = account_data["email"]
            account_name = email  # 使用邮箱地址作为账户名
            display_name = account_data.get("display_name", "")
            provider = account_data.get("provider", "")

            # 提取密码
            password = account_data["smtp_config"]["password"]

            # 准备SMTP配置（移除密码，因为AccountManager会单独处理）
            smtp_config = account_data["smtp_config"].copy()
            smtp_config.pop("password", None)  # 移除密码字段
            smtp_config.pop("username", None)  # 移除用户名字段，AccountManager不需要

            # 准备POP3配置（移除密码）
            pop3_config = account_data["pop3_config"].copy()
            pop3_config.pop("password", None)  # 移除密码字段
            pop3_config.pop("username", None)  # 移除用户名字段

            # 添加用户名到配置中（AccountManager需要）
            smtp_config["username"] = account_data["smtp_config"]["username"]
            pop3_config["username"] = account_data["pop3_config"]["username"]

            # 构建notes
            notes = f"服务商: {provider}"

            # 调用AccountManager.add_account()
            return self.account_manager.add_account(
                account_name=account_name,
                email=email,
                password=password,
                smtp_config=smtp_config,
                pop3_config=pop3_config,
                display_name=display_name,
                notes=notes,
            )
        except Exception as e:
            logger.error(f"添加账户失败: {e}")
            return False

    def send_email_message(
        self,
        to_addresses,
        subject,
        content,
        cc_addresses=None,
        bcc_addresses=None,
        attachments=None,
    ):
        """发送邮件 - 直接使用CLI的SMTP客户端"""
        try:
            smtp_config = self.get_smtp_config()
            if not smtp_config:
                return {"success": False, "error": "未找到SMTP配置"}

            # 创建邮件对象
            email = Email(
                message_id=generate_message_id(),
                from_addr=EmailAddress(
                    name=self.current_account.get(
                        "display_name", self.current_account["email"]
                    ),
                    address=self.current_account["email"],
                ),
                to_addrs=[
                    EmailAddress(name=addr.strip(), address=addr.strip())
                    for addr in to_addresses
                ],
                subject=subject,
                text_content=content,
                date=datetime.datetime.now(),
            )

            # 处理抄送和密送
            if cc_addresses:
                email.cc_addrs = [
                    EmailAddress(name=addr.strip(), address=addr.strip())
                    for addr in cc_addresses
                ]
            if bcc_addresses:
                email.bcc_addrs = [
                    EmailAddress(name=addr.strip(), address=addr.strip())
                    for addr in bcc_addresses
                ]

            # 处理附件
            if attachments:
                email.attachments = []
                for attachment in attachments:
                    email.attachments.append(
                        Attachment(
                            filename=attachment["filename"],
                            content=attachment["content"],
                            content_type=attachment.get(
                                "content_type", "application/octet-stream"
                            ),
                        )
                    )

            # 创建SMTP客户端并发送 - 完全复用CLI逻辑
            smtp_client = SMTPClient(
                host=smtp_config["host"],
                port=smtp_config["port"],
                use_ssl=smtp_config.get("use_ssl", True),
                username=smtp_config["username"],
                password=smtp_config["password"],
                auth_method=smtp_config.get("auth_method", "AUTO"),
                timeout=30,
                save_sent_emails=False,  # web版本不保存到文件
            )

            # 发送邮件
            smtp_client.connect()
            success = smtp_client.send_email(email)
            smtp_client.disconnect()

            if success:
                logger.info(f"邮件发送成功: {subject}")
                return {"success": True, "message": "邮件发送成功"}
            else:
                logger.error(f"邮件发送失败: {subject}")
                return {"success": False, "error": "邮件发送失败"}

        except Exception as e:
            logger.error(f"发送邮件异常: {e}")
            return {"success": False, "error": f"发送邮件时出错: {str(e)}"}

    def receive_emails(self, limit=20):
        """接收邮件 - 直接使用CLI的POP3客户端"""
        try:
            pop3_config = self.get_pop3_config()
            if not pop3_config:
                return {"success": False, "error": "未找到POP3配置"}

            # 创建POP3客户端 - 完全复用CLI逻辑
            pop3_client = POP3Client(
                host=pop3_config["host"],
                port=pop3_config["port"],
                use_ssl=pop3_config.get("use_ssl", True),
                username=pop3_config["username"],
                password=pop3_config["password"],
            )

            # 连接并接收邮件
            pop3_client.connect()
            emails = pop3_client.retrieve_all_emails(limit=limit)
            pop3_client.disconnect()

            return {"success": True, "emails": emails}

        except Exception as e:
            logger.error(f"接收邮件异常: {e}")
            return {"success": False, "error": f"接收邮件时出错: {str(e)}"}

    def get_provider_by_email(self, email):
        """根据邮箱地址自动识别服务商"""
        return self.provider_manager.get_provider_by_email(email)

    def get_all_providers(self):
        """获取所有可用的邮箱服务商"""
        return self.provider_manager.list_providers()

    def get_provider_config(self, provider_id, use_ssl=True):
        """获取指定服务商的配置"""
        smtp_config = self.provider_manager.get_smtp_config(provider_id, use_ssl)
        pop3_config = self.provider_manager.get_pop3_config(provider_id, use_ssl)
        return smtp_config, pop3_config

    def get_provider_notes(self, provider_id):
        """获取服务商配置说明"""
        return self.provider_manager.get_provider_notes(provider_id)

    def delete_email(self, message_id, email_type="received"):
        """删除邮件 - 复用CLI的删除逻辑"""
        try:
            # 导入数据库服务
            from server.new_db_handler import EmailService

            db = EmailService()

            if email_type == "sent":
                # 删除已发送邮件（物理删除）
                success = db.delete_sent_email_metadata(message_id)
                email_type_name = "已发送邮件"
            else:
                # 软删除接收邮件（标记为已删除）
                success = db.update_email(message_id, is_deleted=True)
                email_type_name = "邮件"

            if success:
                logger.info(f"{email_type_name}删除成功: {message_id}")
                return {"success": True, "message": f"{email_type_name}删除成功"}
            else:
                logger.error(f"{email_type_name}删除失败: {message_id}")
                return {"success": False, "error": f"{email_type_name}删除失败"}

        except Exception as e:
            logger.error(f"删除邮件异常: {e}")
            return {"success": False, "error": f"删除邮件时出错: {str(e)}"}


# 创建全局桥接实例
cli_bridge = WebCLIBridge()


@app.route("/")
def index():
    """首页"""
    if "email" not in session:
        return redirect(url_for("login"))

    # 确保当前账户已加载
    if (
        not cli_bridge.current_account
        or cli_bridge.current_account.get("email") != session["email"]
    ):
        if not cli_bridge.load_account(session["email"]):
            flash("账户信息加载失败，请重新登录", "error")
            return redirect(url_for("logout"))

    account_info = cli_bridge.get_current_account_info()
    return render_template("simple_index.html", account=account_info)


@app.route("/login", methods=["GET", "POST"])
def login():
    """登录页面"""
    if request.method == "POST":
        email = request.form.get("email")

        if cli_bridge.load_account(email):
            session["email"] = email
            flash("登录成功！", "success")
            return redirect(url_for("index"))
        else:
            flash("账户不存在，请先添加账户", "error")
            return redirect(url_for("add_account"))

    return render_template("simple_login.html")


@app.route("/logout")
def logout():
    """登出"""
    session.pop("email", None)
    # 清除当前账户信息
    cli_bridge.current_account = None
    flash("已退出登录", "info")
    return redirect(url_for("login"))


@app.route("/add_account", methods=["GET", "POST"])
def add_account():
    """添加邮箱账户"""
    if request.method == "POST":
        # 基本信息
        email = request.form.get("email", "").strip()
        display_name = request.form.get("display_name", "").strip()
        provider = request.form.get("provider", "").strip()

        # SMTP配置
        smtp_host = request.form.get("smtp_host", "").strip()
        smtp_port = request.form.get("smtp_port", "587")
        smtp_ssl = request.form.get("smtp_ssl") == "on"
        smtp_username = request.form.get("smtp_username", "").strip()
        smtp_password = request.form.get("smtp_password", "").strip()
        auth_method = request.form.get("auth_method", "AUTO").strip()

        # POP3配置
        pop3_host = request.form.get("pop3_host", "").strip()
        pop3_port = request.form.get("pop3_port", "995")
        pop3_ssl = request.form.get("pop3_ssl") == "on"
        pop3_username = request.form.get("pop3_username", "").strip() or smtp_username
        pop3_password = request.form.get("pop3_password", "").strip() or smtp_password

        # 验证必要字段
        if not all(
            [
                email,
                smtp_host,
                smtp_port,
                smtp_username,
                smtp_password,
                pop3_host,
                pop3_port,
            ]
        ):
            flash("请填写所有必要字段", "error")
            return render_template("simple_add_account.html")

        # 构建账户数据
        account_data = {
            "email": email,
            "display_name": display_name or email.split("@")[0],
            "provider": provider or "自定义",
            "smtp_config": {
                "host": smtp_host,
                "port": int(smtp_port),
                "use_ssl": smtp_ssl,
                "username": smtp_username,
                "password": smtp_password,
                "auth_method": auth_method,
            },
            "pop3_config": {
                "host": pop3_host,
                "port": int(pop3_port),
                "use_ssl": pop3_ssl,
                "username": pop3_username,
                "password": pop3_password,
            },
        }

        try:
            if cli_bridge.add_account(account_data):
                flash("账户添加成功！", "success")
                session["email"] = account_data["email"]
                cli_bridge.load_account(account_data["email"])
                return redirect(url_for("index"))
            else:
                flash("账户添加失败，请检查配置", "error")
        except Exception as e:
            logger.error(f"添加账户异常: {e}")
            flash(f"添加账户时出错: {str(e)}", "error")

    return render_template("simple_add_account.html")


@app.route("/send", methods=["GET", "POST"])
def send_email_page():
    """发送邮件页面"""
    if "email" not in session:
        return redirect(url_for("login"))

    # 确保当前账户已加载
    if (
        not cli_bridge.current_account
        or cli_bridge.current_account.get("email") != session["email"]
    ):
        if not cli_bridge.load_account(session["email"]):
            flash("账户信息加载失败，请重新登录", "error")
            return redirect(url_for("logout"))

    if request.method == "POST":
        to_addresses = [
            addr.strip()
            for addr in request.form.get("to_addresses", "").split(",")
            if addr.strip()
        ]
        cc_addresses = [
            addr.strip()
            for addr in request.form.get("cc_addresses", "").split(",")
            if addr.strip()
        ]
        bcc_addresses = [
            addr.strip()
            for addr in request.form.get("bcc_addresses", "").split(",")
            if addr.strip()
        ]
        subject = request.form.get("subject", "")
        content = request.form.get("content", "")

        # 处理附件
        attachments = []
        files = request.files.getlist("attachments")
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                attachments.append(
                    {
                        "filename": filename,
                        "content": file.read(),
                        "content_type": file.content_type or "application/octet-stream",
                    }
                )

        # 发送邮件
        result = cli_bridge.send_email_message(
            to_addresses=to_addresses,
            subject=subject,
            content=content,
            cc_addresses=cc_addresses if cc_addresses else None,
            bcc_addresses=bcc_addresses if bcc_addresses else None,
            attachments=attachments if attachments else None,
        )

        if result["success"]:
            flash("邮件发送成功！", "success")
            return redirect(url_for("index"))
        else:
            flash(f'发送失败: {result["error"]}', "error")

    account_info = cli_bridge.get_current_account_info()
    return render_template("simple_send.html", account=account_info)


@app.route("/receive")
def receive_emails_page():
    """接收邮件页面"""
    if "email" not in session:
        return redirect(url_for("login"))

    # 确保当前账户已加载
    if (
        not cli_bridge.current_account
        or cli_bridge.current_account.get("email") != session["email"]
    ):
        if not cli_bridge.load_account(session["email"]):
            flash("账户信息加载失败，请重新登录", "error")
            return redirect(url_for("logout"))

    # 获取用户选择的邮件数量限制
    limit = request.args.get("limit", "20")
    try:
        if limit == "all":
            # 如果用户选择全部，设置一个较大的数字
            limit_num = 1000
        else:
            limit_num = int(limit)
            # 限制最大数量以避免性能问题
            if limit_num > 500:
                limit_num = 500
    except ValueError:
        limit_num = 20

    result = cli_bridge.receive_emails(limit=limit_num)

    if result["success"]:
        emails = result["emails"]

        # 从数据库获取已删除邮件列表，用于过滤
        try:
            from server.new_db_handler import EmailService

            db_service = EmailService()
            deleted_emails = db_service.list_emails(
                user_email=session["email"],
                include_deleted=True,
                include_spam=True,
                limit=2000,  # 获取足够多的已删除邮件记录
            )
            # 创建已删除邮件ID集合，只包含is_deleted=True的邮件
            deleted_message_ids = {
                email["message_id"]
                for email in deleted_emails
                if email.get("is_deleted", False)
            }
            logger.info(f"发现 {len(deleted_message_ids)} 封已删除邮件，将从显示中过滤")
        except Exception as e:
            logger.warning(f"获取已删除邮件列表失败: {e}")
            deleted_message_ids = set()

        # 将Email对象转换为字典格式，并过滤已删除邮件
        emails_dict = []
        filtered_count = 0
        for email in emails:
            email_dict = email.to_dict()

            # 检查是否为已删除邮件
            if email_dict.get("message_id") in deleted_message_ids:
                filtered_count += 1
                logger.debug(f"过滤已删除邮件: {email_dict.get('message_id')}")
                continue

            # 格式化日期字段以便模板使用
            if email_dict.get("date"):
                try:
                    from datetime import datetime

                    # 解析ISO格式的日期字符串
                    date_obj = datetime.fromisoformat(email_dict["date"])
                    # 为模板提供格式化的日期字段
                    email_dict["formatted_date"] = date_obj.strftime("%Y-%m-%d")
                    email_dict["formatted_time"] = date_obj.strftime("%H:%M:%S")
                    email_dict["formatted_datetime"] = date_obj.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                except Exception as e:
                    logger.warning(f"日期格式化失败: {e}")
                    email_dict["formatted_date"] = "未知日期"
                    email_dict["formatted_time"] = ""
                    email_dict["formatted_datetime"] = email_dict["date"]
            emails_dict.append(email_dict)

        if filtered_count > 0:
            logger.info(
                f"已过滤 {filtered_count} 封已删除邮件，显示 {len(emails_dict)} 封邮件"
            )

        # 根据实际获取的数量显示不同的消息
        if limit == "all":
            flash(f"成功接收 {len(emails)} 封邮件（全部邮件）", "success")
        else:
            flash(f"成功接收 {len(emails)} 封邮件（最新 {limit} 封）", "success")
    else:
        emails = []
        emails_dict = []
        flash(f'接收失败: {result["error"]}', "error")

    account_info = cli_bridge.get_current_account_info()
    return render_template(
        "simple_receive.html",
        account=account_info,
        emails=emails_dict,
        current_limit=limit,
    )


@app.route("/api/status")
def api_status():
    """API状态检查"""
    if "email" not in session:
        return jsonify({"authenticated": False})

    # 确保当前账户已加载
    if (
        not cli_bridge.current_account
        or cli_bridge.current_account.get("email") != session["email"]
    ):
        if not cli_bridge.load_account(session["email"]):
            return jsonify({"authenticated": False, "error": "账户加载失败"})

    account_info = cli_bridge.get_current_account_info()
    smtp_config = cli_bridge.get_smtp_config()
    pop3_config = cli_bridge.get_pop3_config()

    return jsonify(
        {
            "authenticated": True,
            "account": account_info,
            "smtp_available": bool(smtp_config),
            "pop3_available": bool(pop3_config),
        }
    )


@app.route("/api/detect_provider", methods=["POST"])
def api_detect_provider():
    """检测邮箱服务商API"""
    try:
        data = request.get_json()
        email = data.get("email", "").strip()

        if not email:
            return jsonify({"success": False, "error": "邮箱地址不能为空"})

        # 自动识别服务商
        result = cli_bridge.get_provider_by_email(email)

        if result:
            provider_id, provider_config = result
            # 获取详细配置
            smtp_config, pop3_config = cli_bridge.get_provider_config(provider_id)
            notes = cli_bridge.get_provider_notes(provider_id)

            return jsonify(
                {
                    "success": True,
                    "provider_id": provider_id,
                    "provider_name": provider_config.get("name", provider_id),
                    "smtp_config": smtp_config,
                    "pop3_config": pop3_config,
                    "notes": notes,
                    "detected": True,
                }
            )
        else:
            return jsonify(
                {
                    "success": True,
                    "provider_id": "custom",
                    "provider_name": "自定义服务器",
                    "detected": False,
                    "message": "未能自动识别邮箱服务商，请手动配置",
                }
            )

    except Exception as e:
        logger.error(f"检测邮箱服务商失败: {e}")
        return jsonify({"success": False, "error": f"检测失败: {str(e)}"})


@app.route("/api/providers")
def api_providers():
    """获取所有邮箱服务商列表API"""
    try:
        providers = cli_bridge.get_all_providers()
        provider_list = []

        for provider_id, provider_name in providers:
            if provider_id != "custom":
                # 获取详细配置
                smtp_config, pop3_config = cli_bridge.get_provider_config(provider_id)
                notes = cli_bridge.get_provider_notes(provider_id)

                provider_list.append(
                    {
                        "id": provider_id,
                        "name": provider_name,
                        "smtp_config": smtp_config,
                        "pop3_config": pop3_config,
                        "notes": notes,
                    }
                )

        # 添加自定义选项
        provider_list.append(
            {
                "id": "custom",
                "name": "自定义服务器",
                "smtp_config": None,
                "pop3_config": None,
                "notes": "手动配置服务器设置",
            }
        )

        return jsonify({"success": True, "providers": provider_list})

    except Exception as e:
        logger.error(f"获取服务商列表失败: {e}")
        return jsonify({"success": False, "error": f"获取失败: {str(e)}"})


@app.route("/api/delete_email", methods=["POST"])
def api_delete_email():
    """删除邮件API"""
    logger.info("删除邮件API被调用")

    if "email" not in session:
        logger.warning("删除邮件API: 用户未登录")
        return jsonify({"success": False, "error": "未登录"})

    logger.info(f"删除邮件API: 用户已登录 - {session['email']}")

    # 确保当前账户已加载
    if (
        not cli_bridge.current_account
        or cli_bridge.current_account.get("email") != session["email"]
    ):
        logger.info(f"删除邮件API: 重新加载账户 - {session['email']}")
        if not cli_bridge.load_account(session["email"]):
            logger.error("删除邮件API: 账户加载失败")
            return jsonify({"success": False, "error": "账户加载失败"})

    try:
        data = request.get_json()
        logger.info(f"删除邮件API: 接收到数据 - {data}")

        message_id = data.get("message_id", "").strip()
        email_type = data.get("email_type", "received").strip()

        if not message_id:
            logger.warning("删除邮件API: 邮件ID为空")
            return jsonify({"success": False, "error": "邮件ID不能为空"})

        logger.info(
            f"删除邮件API: 准备删除邮件 - ID: {message_id[:30]}..., 类型: {email_type}"
        )

        # 调用删除方法
        result = cli_bridge.delete_email(message_id, email_type)
        logger.info(f"删除邮件API: 删除结果 - {result}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"删除邮件API异常: {e}")
        import traceback

        logger.error(f"删除邮件API异常详情: {traceback.format_exc()}")
        return jsonify({"success": False, "error": f"删除失败: {str(e)}"})


@app.route("/api/debug")
def api_debug():
    """调试端点：查看当前账户状态"""
    try:
        debug_info = {
            "session_email": session.get("email"),
            "has_current_account": cli_bridge.current_account is not None,
            "account_list": cli_bridge.account_manager.list_accounts(),
            "current_account_info": None,
            "smtp_config_available": False,
            "pop3_config_available": False,
        }

        if cli_bridge.current_account:
            debug_info["current_account_info"] = {
                "email": cli_bridge.current_account.get("email"),
                "display_name": cli_bridge.current_account.get("display_name"),
                "has_smtp": "smtp" in cli_bridge.current_account,
                "has_pop3": "pop3" in cli_bridge.current_account,
                "smtp_keys": list(cli_bridge.current_account.get("smtp", {}).keys()),
                "pop3_keys": list(cli_bridge.current_account.get("pop3", {}).keys()),
            }

        smtp_config = cli_bridge.get_smtp_config()
        pop3_config = cli_bridge.get_pop3_config()

        debug_info["smtp_config_available"] = smtp_config is not None
        debug_info["pop3_config_available"] = pop3_config is not None

        if smtp_config:
            debug_info["smtp_config_keys"] = list(smtp_config.keys())
        if pop3_config:
            debug_info["pop3_config_keys"] = list(pop3_config.keys())

        return jsonify({"success": True, "debug": debug_info})

    except Exception as e:
        logger.error(f"调试信息获取失败: {e}")
        return jsonify({"success": False, "error": f"调试失败: {str(e)}"})


if __name__ == "__main__":
    print("🚀 启动简化Web邮件客户端...")
    print("📧 基于CLI底层实现，避免复杂封装")
    print("🌐 访问地址: http://localhost:3000")
    print("💡 直接复用CLI的稳定邮件发送逻辑")
    print("-" * 50)

    app.run(host="127.0.0.1", port=3000, debug=True)
