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
            'subject': [re.compile(k, re.IGNORECASE) for k in self.keywords.get('subject', [])],
            'body': [re.compile(k, re.IGNORECASE) for k in self.keywords.get('body', [])],
            'sender': [re.compile(k, re.IGNORECASE) for k in self.keywords.get('sender', [])]
        }
    
    def _load_keywords(self) -> Dict[str, List[str]]:
        """加载关键词配置"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载垃圾邮件关键词失败: {e}")
            return {'subject': [], 'body': [], 'sender': []}
    
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
        sender = email_data.get('from_addr', '')
        for pattern in self.patterns['sender']:
            if pattern.search(sender):
                score += 1.0
                matched.append(f"sender:{pattern.pattern}")
        
        # 检查主题
        subject = email_data.get('subject', '')
        for pattern in self.patterns['subject']:
            if pattern.search(subject):
                score += 2.0
                matched.append(f"subject:{pattern.pattern}")
        
        # 检查正文
        content = email_data.get('content', '')
        for pattern in self.patterns['body']:
            if pattern.search(content):
                score += 1.5
                matched.append(f"body:{pattern.pattern}")
        
        return {
            'is_spam': score >= 3.0,  # 阈值可配置
            'score': min(score, 10.0),
            'matched_keywords': matched
        }