# -*- coding: utf-8 -*-
"""
邮件服务商配置管理器 - 负责管理预设的邮件服务商配置
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 添加项目根目录到Python路径
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from common.utils import setup_logging

# 设置日志
logger = setup_logging("provider_manager")


class ProviderManager:
    """邮件服务商配置管理器"""

    def __init__(self):
        """初始化服务商管理器"""
        self.config_file = (
            Path(__file__).resolve().parent.parent / "config" / "email_providers.json"
        )
        self.providers = self._load_providers()

    def _load_providers(self) -> Dict:
        """加载邮件服务商配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("providers", {})
            else:
                logger.warning(f"邮件服务商配置文件不存在: {self.config_file}")
                return {}
        except Exception as e:
            logger.error(f"加载邮件服务商配置失败: {e}")
            return {}

    def get_provider_by_email(self, email: str) -> Optional[Tuple[str, Dict]]:
        """根据邮箱地址自动识别服务商"""
        try:
            domain = email.split("@")[1].lower()

            for provider_id, provider_config in self.providers.items():
                if domain in provider_config.get("domains", []):
                    return provider_id, provider_config

            return None
        except Exception as e:
            logger.error(f"识别邮件服务商失败: {e}")
            return None

    def get_provider(self, provider_id: str) -> Optional[Dict]:
        """获取指定服务商配置"""
        return self.providers.get(provider_id)

    def list_providers(self) -> List[Tuple[str, str]]:
        """列出所有可用的服务商"""
        providers = []
        for provider_id, config in self.providers.items():
            if provider_id != "custom":  # 自定义配置不在列表中显示
                providers.append((provider_id, config.get("name", provider_id)))

        # 添加自定义选项
        providers.append(("custom", "自定义服务器"))
        return providers

    def get_smtp_config(self, provider_id: str, use_ssl: bool = True) -> Optional[Dict]:
        """获取SMTP配置"""
        provider = self.get_provider(provider_id)
        if not provider:
            return None

        smtp_config = provider.get("smtp", {}).copy()
        if smtp_config:
            # 根据SSL设置选择端口
            if use_ssl and "ssl_port" in smtp_config:
                smtp_config["port"] = smtp_config["ssl_port"]
            smtp_config["use_ssl"] = use_ssl

        return smtp_config

    def get_pop3_config(self, provider_id: str, use_ssl: bool = True) -> Optional[Dict]:
        """获取POP3配置"""
        provider = self.get_provider(provider_id)
        if not provider:
            return None

        pop3_config = provider.get("pop3", {}).copy()
        if pop3_config:
            # 根据SSL设置选择端口
            if use_ssl and "ssl_port" in pop3_config:
                pop3_config["port"] = pop3_config["ssl_port"]
            pop3_config["use_ssl"] = use_ssl

        return pop3_config

    def get_imap_config(self, provider_id: str, use_ssl: bool = True) -> Optional[Dict]:
        """获取IMAP配置"""
        provider = self.get_provider(provider_id)
        if not provider:
            return None

        imap_config = provider.get("imap", {}).copy()
        if imap_config:
            # 根据SSL设置选择端口
            if use_ssl and "ssl_port" in imap_config:
                imap_config["port"] = imap_config["ssl_port"]
            imap_config["use_ssl"] = use_ssl

        return imap_config

    def get_provider_notes(self, provider_id: str) -> str:
        """获取服务商配置说明"""
        provider = self.get_provider(provider_id)
        if provider:
            return provider.get("notes", "")
        return ""

    def validate_email_format(self, email: str) -> bool:
        """验证邮箱格式"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def suggest_provider(self, email: str) -> Optional[str]:
        """根据邮箱地址建议服务商"""
        result = self.get_provider_by_email(email)
        if result:
            provider_id, _ = result
            return provider_id
        return "custom"

    def get_setup_instructions(self, provider_id: str) -> List[str]:
        """获取服务商设置说明"""
        instructions = []

        if provider_id == "qq":
            instructions = [
                "1. 登录QQ邮箱网页版",
                "2. 进入设置 -> 账户",
                "3. 开启SMTP/POP3/IMAP服务",
                "4. 生成授权码",
                "5. 使用授权码作为密码",
            ]
        elif provider_id == "gmail":
            instructions = [
                "1. 登录Gmail网页版",
                "2. 进入Google账户设置",
                "3. 开启两步验证",
                "4. 生成应用专用密码",
                "5. 使用应用专用密码作为密码",
            ]
        elif provider_id == "163":
            instructions = [
                "1. 登录163邮箱网页版",
                "2. 进入设置 -> POP3/SMTP/IMAP",
                "3. 开启相应服务",
                "4. 设置客户端授权密码",
                "5. 使用授权密码作为密码",
            ]
        elif provider_id == "126":
            instructions = [
                "1. 登录126邮箱网页版",
                "2. 进入设置 -> POP3/SMTP/IMAP",
                "3. 开启相应服务",
                "4. 设置客户端授权密码",
                "5. 使用授权密码作为密码",
            ]
        elif provider_id == "outlook":
            instructions = [
                "1. 登录Outlook网页版",
                "2. 进入安全设置",
                "3. 开启两步验证（推荐）",
                "4. 生成应用密码",
                "5. 使用应用密码作为密码",
            ]
        elif provider_id == "yahoo":
            instructions = [
                "1. 登录Yahoo邮箱网页版",
                "2. 进入账户安全设置",
                "3. 开启两步验证",
                "4. 生成应用密码",
                "5. 使用应用密码作为密码",
            ]
        else:
            instructions = [
                "请联系您的邮件服务提供商获取正确的服务器设置",
                "通常需要SMTP和POP3/IMAP服务器地址、端口和加密设置",
            ]

        return instructions

    def create_custom_provider(
        self,
        name: str,
        smtp_host: str,
        smtp_port: int,
        pop3_host: str,
        pop3_port: int,
        use_ssl: bool = True,
    ) -> Dict:
        """创建自定义服务商配置"""
        return {
            "name": name,
            "domains": [],
            "smtp": {
                "host": smtp_host,
                "port": smtp_port,
                "use_ssl": use_ssl,
                "auth_method": "AUTO",
            },
            "pop3": {
                "host": pop3_host,
                "port": pop3_port,
                "use_ssl": use_ssl,
                "auth_method": "AUTO",
            },
            "notes": "自定义配置",
        }
