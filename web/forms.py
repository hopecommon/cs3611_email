"""
Flask-WTF表单定义 - 包含所有Web界面需要的表单
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField,
    TextAreaField,
    PasswordField,
    BooleanField,
    SelectField,
    SubmitField,
    HiddenField,
    SelectMultipleField,
    IntegerField,
    EmailField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    Optional,
    ValidationError,
    NumberRange,
)
from wtforms.widgets import TextArea


class CKTextAreaWidget(TextArea):
    """CKEditor文本区域组件"""

    def __call__(self, field, **kwargs):
        kwargs.setdefault("class_", "ckeditor")
        return super(CKTextAreaWidget, self).__call__(field, **kwargs)


class CKTextAreaField(TextAreaField):
    """CKEditor文本字段"""

    widget = CKTextAreaWidget()


class LoginForm(FlaskForm):
    """用户登录表单"""

    username = StringField(
        "用户名",
        validators=[DataRequired(message="请输入用户名")],
        render_kw={"placeholder": "请输入用户名", "class": "form-control"},
    )

    password = PasswordField(
        "密码",
        validators=[DataRequired(message="请输入密码")],
        render_kw={"placeholder": "请输入密码", "class": "form-control"},
    )

    remember_me = BooleanField("记住我", render_kw={"class": "form-check-input"})

    submit = SubmitField("登录", render_kw={"class": "btn btn-primary btn-block"})


class ComposeEmailForm(FlaskForm):
    """邮件撰写表单"""

    to_addresses = StringField(
        "收件人 *",
        validators=[DataRequired(message="请输入收件人地址")],
        render_kw={"placeholder": "多个邮箱地址请用逗号分隔", "class": "form-control"},
    )

    cc_addresses = StringField(
        "抄送",
        validators=[Optional()],
        render_kw={"placeholder": "抄送地址（可选）", "class": "form-control"},
    )

    bcc_addresses = StringField(
        "密送",
        validators=[Optional()],
        render_kw={"placeholder": "密送地址（可选）", "class": "form-control"},
    )

    subject = StringField(
        "主题 *",
        validators=[DataRequired(message="请输入邮件主题")],
        render_kw={"placeholder": "邮件主题", "class": "form-control"},
    )

    content_type = SelectField(
        "内容类型",
        choices=[("text", "纯文本"), ("html", "HTML富文本")],
        default="html",
        render_kw={"class": "form-select"},
    )

    content = CKTextAreaField(
        "邮件内容 *",
        validators=[DataRequired(message="请输入邮件内容")],
        render_kw={"rows": 15, "class": "form-control ckeditor"},
    )

    attachments = FileField(
        "附件",
        validators=[
            Optional(),
            FileAllowed(
                ["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "txt", "zip"],
                "不支持的文件类型",
            ),
        ],
        render_kw={"class": "form-control", "multiple": True},
    )

    priority = SelectField(
        "优先级",
        choices=[("low", "低"), ("normal", "普通"), ("high", "高")],
        default="normal",
        render_kw={"class": "form-select"},
    )

    submit = SubmitField("发送邮件", render_kw={"class": "btn btn-primary"})

    save_draft = SubmitField("保存草稿", render_kw={"class": "btn btn-secondary"})

    def validate_to_addresses(self, field):
        """验证收件人地址格式"""
        if field.data:
            addresses = [addr.strip() for addr in field.data.split(",") if addr.strip()]
            for addr in addresses:
                if "@" not in addr or "." not in addr.split("@")[-1]:
                    raise ValidationError(f"无效的邮箱地址: {addr}")


class SearchEmailForm(FlaskForm):
    """邮件搜索表单"""

    query = StringField(
        "搜索关键词",
        validators=[DataRequired(message="请输入搜索关键词")],
        render_kw={"placeholder": "输入搜索关键词", "class": "form-control"},
    )

    search_in = SelectMultipleField(
        "搜索范围",
        choices=[
            ("subject", "主题"),
            ("content", "内容"),
            ("from_addr", "发件人"),
            ("to_addrs", "收件人"),
        ],
        default=["subject", "content"],
        render_kw={"class": "form-select", "multiple": True},
    )

    folder = SelectField(
        "搜索文件夹",
        choices=[
            ("all", "所有邮件"),
            ("inbox", "收件箱"),
            ("sent", "发件箱"),
            ("spam", "垃圾邮件"),
        ],
        default="all",
        render_kw={"class": "form-select"},
    )

    date_from = StringField(
        "开始日期",
        validators=[Optional()],
        render_kw={"type": "date", "class": "form-control"},
    )

    date_to = StringField(
        "结束日期",
        validators=[Optional()],
        render_kw={"type": "date", "class": "form-control"},
    )

    submit = SubmitField("搜索", render_kw={"class": "btn btn-primary"})


class MarkEmailForm(FlaskForm):
    """邮件标记表单（用于批量操作）"""

    email_ids = HiddenField("邮件ID列表")

    action = SelectField(
        "操作",
        choices=[
            ("mark_read", "标记为已读"),
            ("mark_unread", "标记为未读"),
            ("mark_spam", "标记为垃圾邮件"),
            ("unmark_spam", "取消垃圾邮件标记"),
            ("delete", "删除邮件"),
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"},
    )

    submit = SubmitField("执行操作", render_kw={"class": "btn btn-warning"})


class SpamFilterConfigForm(FlaskForm):
    """垃圾邮件过滤配置表单"""

    threshold = StringField(
        "垃圾邮件阈值",
        validators=[DataRequired()],
        render_kw={
            "type": "number",
            "step": "0.1",
            "min": "0",
            "max": "10",
            "class": "form-control",
        },
    )

    keywords_subject = TextAreaField(
        "主题关键词（每行一个）",
        validators=[Optional()],
        render_kw={
            "rows": 5,
            "class": "form-control",
            "placeholder": "每行输入一个关键词",
        },
    )

    keywords_body = TextAreaField(
        "内容关键词（每行一个）",
        validators=[Optional()],
        render_kw={
            "rows": 5,
            "class": "form-control",
            "placeholder": "每行输入一个关键词",
        },
    )

    keywords_sender = TextAreaField(
        "发件人关键词（每行一个）",
        validators=[Optional()],
        render_kw={
            "rows": 5,
            "class": "form-control",
            "placeholder": "每行输入一个关键词",
        },
    )

    submit = SubmitField("保存配置", render_kw={"class": "btn btn-primary"})


class ReplyEmailForm(FlaskForm):
    """邮件回复表单"""

    original_message_id = HiddenField("原邮件ID")

    to_addresses = StringField(
        "收件人 *",
        validators=[DataRequired(message="请输入收件人地址")],
        render_kw={"class": "form-control", "readonly": True},
    )

    subject = StringField(
        "主题 *",
        validators=[DataRequired(message="请输入邮件主题")],
        render_kw={"class": "form-control", "readonly": True},
    )

    content = CKTextAreaField(
        "回复内容 *",
        validators=[DataRequired(message="请输入回复内容")],
        render_kw={"rows": 10, "class": "form-control ckeditor"},
    )

    attachments = FileField(
        "附件",
        validators=[
            Optional(),
            FileAllowed(
                ["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "txt", "zip"],
                "不支持的文件类型",
            ),
        ],
        render_kw={"class": "form-control", "multiple": True},
    )

    submit = SubmitField("发送回复", render_kw={"class": "btn btn-primary"})


class ForwardEmailForm(FlaskForm):
    """邮件转发表单"""

    original_message_id = HiddenField("原邮件ID")

    to_addresses = StringField(
        "收件人 *",
        validators=[DataRequired(message="请输入收件人地址")],
        render_kw={"placeholder": "多个邮箱地址请用逗号分隔", "class": "form-control"},
    )

    subject = StringField(
        "主题 *",
        validators=[DataRequired(message="请输入邮件主题")],
        render_kw={"class": "form-control"},
    )

    content = CKTextAreaField(
        "转发说明",
        validators=[Optional()],
        render_kw={
            "rows": 5,
            "class": "form-control ckeditor",
            "placeholder": "添加转发说明（可选）",
        },
    )

    include_attachments = BooleanField(
        "包含原邮件附件", default=True, render_kw={"class": "form-check-input"}
    )

    submit = SubmitField("转发邮件", render_kw={"class": "btn btn-primary"})


class MailConfigForm(FlaskForm):
    """邮箱配置表单"""

    mail_display_name = StringField(
        "显示名称",
        validators=[DataRequired()],
        render_kw={"placeholder": "您希望在邮件中显示的名称"},
    )

    # SMTP配置
    smtp_server = StringField(
        "SMTP服务器",
        validators=[DataRequired()],
        render_kw={"placeholder": "例如: smtp.gmail.com"},
    )
    smtp_port = IntegerField(
        "SMTP端口",
        validators=[DataRequired(), NumberRange(min=1, max=65535)],
        default=587,
    )
    smtp_use_tls = BooleanField("使用TLS", default=True)
    smtp_username = StringField(
        "SMTP用户名",
        validators=[DataRequired()],
        render_kw={"placeholder": "通常是您的邮箱地址"},
    )
    smtp_password = PasswordField(
        "SMTP密码",
        validators=[DataRequired()],
        render_kw={"placeholder": "邮箱密码或应用专用密码"},
    )

    # POP3配置
    pop3_server = StringField(
        "POP3服务器",
        validators=[DataRequired()],
        render_kw={"placeholder": "例如: pop.gmail.com"},
    )
    pop3_port = IntegerField(
        "POP3端口",
        validators=[DataRequired(), NumberRange(min=1, max=65535)],
        default=995,
    )
    pop3_use_ssl = BooleanField("使用SSL", default=True)
    pop3_username = StringField(
        "POP3用户名",
        validators=[DataRequired()],
        render_kw={"placeholder": "通常是您的邮箱地址"},
    )
    pop3_password = PasswordField(
        "POP3密码",
        validators=[DataRequired()],
        render_kw={"placeholder": "邮箱密码或应用专用密码"},
    )

    submit = SubmitField("保存配置")


class QuickSetupForm(FlaskForm):
    """快速设置表单 - 预设常见邮箱服务商"""

    provider = SelectField(
        "邮箱服务商",
        choices=[
            ("gmail", "Gmail (Google)"),
            ("outlook", "Outlook (Microsoft)"),
            ("qq", "QQ邮箱"),
            ("163", "163邮箱"),
            ("126", "126邮箱"),
            ("custom", "自定义设置"),
        ],
        validators=[DataRequired()],
    )

    mail_display_name = StringField(
        "显示名称", validators=[DataRequired()], render_kw={"placeholder": "您的名称"}
    )
    email_address = EmailField(
        "邮箱地址",
        validators=[DataRequired(), Email()],
        render_kw={"placeholder": "your@email.com"},
    )
    password = PasswordField(
        "邮箱密码",
        validators=[DataRequired()],
        render_kw={"placeholder": "邮箱密码或应用专用密码"},
    )

    submit = SubmitField("快速配置")


class TestEmailForm(FlaskForm):
    """测试邮件发送表单"""

    to_address = EmailField(
        "收件人",
        validators=[DataRequired(), Email()],
        render_kw={"placeholder": "test@example.com"},
    )
    subject = StringField(
        "主题",
        validators=[DataRequired()],
        default="邮箱配置测试",
        render_kw={"placeholder": "测试邮件主题"},
    )
    content = TextAreaField(
        "内容",
        validators=[DataRequired()],
        default="这是一封测试邮件，用于验证您的邮箱配置是否正确。",
        render_kw={"rows": 5, "placeholder": "邮件内容"},
    )
    submit = SubmitField("发送测试邮件")
