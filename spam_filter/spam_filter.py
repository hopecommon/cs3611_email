# -*- coding: utf-8 -*-
# spam_filter/spam_filter.py
import re
from typing import List, Dict
from pathlib import Path
import json
from common.utils import setup_logging

logger = setup_logging("spam_filter")


class KeywordSpamFilter:
    """基于关键词的垃圾邮件过滤器"""

    def __init__(self, config_path: str = "config/spam_keywords.json"):
        self.config_path = Path(config_path)
        self.keywords = self._load_keywords()
        self.threshold = 3.0

        # 初始化匹配模式（支持正则表达式）
        self.patterns = {
            "subject": [
                re.compile(k, re.IGNORECASE) for k in self.keywords.get("subject", [])
            ],
            "body": [
                re.compile(k, re.IGNORECASE) for k in self.keywords.get("body", [])
            ],
            "sender": [
                re.compile(k, re.IGNORECASE) for k in self.keywords.get("sender", [])
            ],
        }

    def _load_keywords(self) -> Dict[str, List[str]]:
        """加载关键词配置"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载垃圾邮件关键词失败: {e}")
            return {"subject": [], "body": [], "sender": []}

    def analyze_email(self, email_data: Dict) -> Dict:
        """
        分析邮件并返回垃圾评分
        返回格式: {
            'is_spam': bool,
            'score': float,
            'matched_keywords': List[str]
        }
        """
        score = 0.0
        matched = []

        # 检查发件人
        sender = email_data.get("from_addr", "")
        for pattern in self.patterns["sender"]:
            if pattern.search(sender):
                score += 1.0
                matched.append(f"sender:{pattern.pattern}")

        # 检查主题
        subject = email_data.get("subject", "")
        for pattern in self.patterns["subject"]:
            if pattern.search(subject):
                score += 2.0
                matched.append(f"subject:{pattern.pattern}")

        # 检查正文
        content = email_data.get("content", "")
        for pattern in self.patterns["body"]:
            if pattern.search(content):
                score += 1.5
                matched.append(f"body:{pattern.pattern}")

        return {
            "is_spam": score >= self.threshold,  # 使用可配置阈值
            "score": min(score, 10.0),
            "matched_keywords": matched,
        }

    def update_threshold(self, new_threshold: float) -> bool:
        """更新垃圾邮件检测阈值"""
        try:
            if 0.0 <= new_threshold <= 10.0:
                self.threshold = new_threshold
                logger.info(f"垃圾邮件阈值已更新为: {new_threshold}")
                return True
            else:
                logger.warning(f"阈值超出范围 (0.0-10.0): {new_threshold}")
                return False
        except Exception as e:
            logger.error(f"更新阈值失败: {e}")
            return False

    def reload_keywords(self) -> bool:
        """重新加载关键词配置"""
        try:
            self.keywords = self._load_keywords()
            # 重新初始化匹配模式
            self.patterns = {
                "subject": [
                    re.compile(k, re.IGNORECASE)
                    for k in self.keywords.get("subject", [])
                ],
                "body": [
                    re.compile(k, re.IGNORECASE) for k in self.keywords.get("body", [])
                ],
                "sender": [
                    re.compile(k, re.IGNORECASE)
                    for k in self.keywords.get("sender", [])
                ],
            }
            logger.info("垃圾邮件关键词已重新加载")
            return True
        except Exception as e:
            logger.error(f"重新加载关键词失败: {e}")
            return False
