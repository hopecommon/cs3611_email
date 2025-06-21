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
        self.threshold = 2.0
        self.dynamic_threshold = True  # 启用动态阈值
        self.min_threshold = 1.5  # 最低阈值
        self.max_threshold = 4.0  # 最高阈值

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
        match_count = 0

        # 检查发件人
        sender = email_data.get("from_addr", "")
        for pattern in self.patterns["sender"]:
            if pattern.search(sender):
                score += 1.0
                match_count += 1
                matched.append(f"sender:{pattern.pattern}")

        # 检查主题
        subject = email_data.get("subject", "")
        subject_matches = 0
        for pattern in self.patterns["subject"]:
            if pattern.search(subject):
                score += 2.0
                subject_matches += 1
                match_count += 1
                matched.append(f"subject:{pattern.pattern}")

        # 检查正文
        content = email_data.get("content", "")
        content_matches = 0
        for pattern in self.patterns["body"]:
            if pattern.search(content):
                score += 1.5
                content_matches += 1
                match_count += 1
                matched.append(f"body:{pattern.pattern}")

        # 动态阈值调整
        effective_threshold = self.threshold
        if self.dynamic_threshold:
            # 如果有多个匹配，降低阈值
            if match_count >= 2:
                effective_threshold = max(self.min_threshold, self.threshold - 0.5)
            # 如果只有主题匹配，适当提高阈值
            elif subject_matches > 0 and content_matches == 0 and len(matched) == 1:
                effective_threshold = min(self.max_threshold, self.threshold + 0.3)

        # 内容质量评估：如果内容过短且有匹配，可能是垃圾邮件
        if content and len(content.strip()) < 50 and match_count > 0:
            score += 0.5
            matched.append("short_content_bonus")

        # 多重匹配奖励
        if match_count >= 2:
            score += 0.5 * (match_count - 1)
            matched.append(f"multiple_matches_bonus:{match_count}")

        return {
            "is_spam": score >= effective_threshold,
            "score": min(score, 10.0),
            "matched_keywords": matched,
            "effective_threshold": effective_threshold,
            "match_count": match_count,
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

    def configure_thresholds(
        self,
        base_threshold: float = None,
        min_threshold: float = None,
        max_threshold: float = None,
        enable_dynamic: bool = None,
    ) -> bool:
        """配置阈值参数"""
        try:
            if base_threshold is not None and 0.0 <= base_threshold <= 10.0:
                self.threshold = base_threshold
            if min_threshold is not None and 0.0 <= min_threshold <= 10.0:
                self.min_threshold = min_threshold
            if max_threshold is not None and 0.0 <= max_threshold <= 10.0:
                self.max_threshold = max_threshold
            if enable_dynamic is not None:
                self.dynamic_threshold = enable_dynamic

            logger.info(
                f"阈值配置已更新: base={self.threshold}, min={self.min_threshold}, "
                f"max={self.max_threshold}, dynamic={self.dynamic_threshold}"
            )
            return True
        except Exception as e:
            logger.error(f"配置阈值失败: {e}")
            return False

    def get_filter_stats(self) -> Dict:
        """获取过滤器统计信息"""
        return {
            "threshold": self.threshold,
            "min_threshold": self.min_threshold,
            "max_threshold": self.max_threshold,
            "dynamic_threshold": self.dynamic_threshold,
            "keyword_counts": {
                "subject": len(self.keywords.get("subject", [])),
                "body": len(self.keywords.get("body", [])),
                "sender": len(self.keywords.get("sender", [])),
            },
        }

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
