#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮箱服务商配置 - 支持常见邮箱服务商的自动配置
"""

# 常见邮箱服务商配置
EMAIL_PROVIDERS = {
    "qq.com": {
        "name": "QQ邮箱",
        "smtp": {
            "host": "smtp.qq.com",
            "port": 587,
            "use_tls": True,
        },
        "pop3": {
            "host": "pop.qq.com",
            "port": 995,
            "use_ssl": True,
        },
        "help_url": "https://service.mail.qq.com/cgi-bin/help?subtype=1&&id=28&&no=1001256",
        "auth_note": "需要使用授权码，不是QQ密码",
    },
    "gmail.com": {
        "name": "Gmail",
        "smtp": {
            "host": "smtp.gmail.com",
            "port": 587,
            "use_tls": True,
        },
        "pop3": {
            "host": "pop.gmail.com",
            "port": 995,
            "use_ssl": True,
        },
        "help_url": "https://support.google.com/mail/answer/7126229",
        "auth_note": "需要开启两步验证并使用应用专用密码",
    },
    "outlook.com": {
        "name": "Outlook.com",
        "smtp": {
            "host": "smtp-mail.outlook.com",
            "port": 587,
            "use_tls": True,
        },
        "pop3": {
            "host": "outlook-mail.outlook.com",
            "port": 995,
            "use_ssl": True,
        },
        "help_url": "https://support.microsoft.com/zh-cn/office/outlook-com-pop-imap-smtp-设置-d088b986-291d-42b8-9564-9c414e2aa040",
        "auth_note": "需要在账户设置中启用POP/IMAP",
    },
    "hotmail.com": {
        "name": "Hotmail",
        "smtp": {
            "host": "smtp-mail.outlook.com",
            "port": 587,
            "use_tls": True,
        },
        "pop3": {
            "host": "outlook-mail.outlook.com",
            "port": 995,
            "use_ssl": True,
        },
        "help_url": "https://support.microsoft.com/zh-cn/office/outlook-com-pop-imap-smtp-设置-d088b986-291d-42b8-9564-9c414e2aa040",
        "auth_note": "需要在账户设置中启用POP/IMAP",
    },
    "163.com": {
        "name": "网易163邮箱",
        "smtp": {
            "host": "smtp.163.com",
            "port": 465,
            "use_tls": False,
            "use_ssl": True,
        },
        "pop3": {
            "host": "pop.163.com",
            "port": 995,
            "use_ssl": True,
        },
        "help_url": "https://help.mail.163.com/faqDetail.do?code=d7a5dc8471cd0c0e8b4b8f4f8e49998b374173cfe9171312",
        "auth_note": "需要开启SMTP/POP3服务并使用授权码",
    },
    "126.com": {
        "name": "网易126邮箱",
        "smtp": {
            "host": "smtp.126.com",
            "port": 465,
            "use_tls": False,
            "use_ssl": True,
        },
        "pop3": {
            "host": "pop.126.com",
            "port": 995,
            "use_ssl": True,
        },
        "help_url": "https://help.mail.163.com/faqDetail.do?code=d7a5dc8471cd0c0e8b4b8f4f8e49998b374173cfe9171312",
        "auth_note": "需要开启SMTP/POP3服务并使用授权码",
    },
    "yeah.net": {
        "name": "网易yeah邮箱",
        "smtp": {
            "host": "smtp.yeah.net",
            "port": 465,
            "use_tls": False,
            "use_ssl": True,
        },
        "pop3": {
            "host": "pop.yeah.net",
            "port": 995,
            "use_ssl": True,
        },
        "help_url": "https://help.mail.163.com/faqDetail.do?code=d7a5dc8471cd0c0e8b4b8f4f8e49998b374173cfe9171312",
        "auth_note": "需要开启SMTP/POP3服务并使用授权码",
    },
    "sina.com": {
        "name": "新浪邮箱",
        "smtp": {
            "host": "smtp.sina.com",
            "port": 587,
            "use_tls": True,
        },
        "pop3": {
            "host": "pop.sina.com",
            "port": 995,
            "use_ssl": True,
        },
        "help_url": "https://help.sina.com.cn/",
        "auth_note": "需要开启SMTP/POP3服务",
    },
    "sohu.com": {
        "name": "搜狐邮箱",
        "smtp": {
            "host": "smtp.sohu.com",
            "port": 587,
            "use_tls": True,
        },
        "pop3": {
            "host": "pop.sohu.com",
            "port": 995,
            "use_ssl": True,
        },
        "help_url": "https://help.sohu.com/",
        "auth_note": "需要开启SMTP/POP3服务",
    },
}


def get_provider_config(email_address):
    """
    根据邮箱地址获取服务商配置

    Args:
        email_address: 邮箱地址

    Returns:
        dict: 服务商配置，如果未找到则返回None
    """
    if not email_address or "@" not in email_address:
        return None

    domain = email_address.split("@")[1].lower()
    return EMAIL_PROVIDERS.get(domain)


def get_all_providers():
    """
    获取所有支持的邮箱服务商

    Returns:
        dict: 所有服务商配置
    """
    return EMAIL_PROVIDERS


def is_supported_provider(email_address):
    """
    检查是否支持该邮箱服务商

    Args:
        email_address: 邮箱地址

    Returns:
        bool: 是否支持
    """
    return get_provider_config(email_address) is not None


if __name__ == "__main__":
    # 测试
    test_emails = [
        "test@qq.com",
        "test@gmail.com",
        "test@163.com",
        "test@outlook.com",
        "test@unknown.com",
    ]

    print("🔍 测试邮箱服务商识别:")
    for email in test_emails:
        config = get_provider_config(email)
        if config:
            print(f"✅ {email} -> {config['name']}")
            print(f"   SMTP: {config['smtp']['host']}:{config['smtp']['port']}")
            print(f"   POP3: {config['pop3']['host']}:{config['pop3']['port']}")
        else:
            print(f"❌ {email} -> 不支持的服务商")
        print()
