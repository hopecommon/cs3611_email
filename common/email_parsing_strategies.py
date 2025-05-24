# -*- coding: utf-8 -*-
"""
邮件解析策略模块
提供多种邮件解析策略，从严格到宽松的渐进式解析
"""

from typing import Union, List, Callable
from email.message import EmailMessage
from email.parser import Parser, BytesParser
from email import policy

from common.utils import setup_logging

logger = setup_logging(__name__)


class EmailParsingStrategies:
    """邮件解析策略管理器"""
    
    @classmethod
    def parse_with_strategies(cls, content: Union[str, bytes]) -> EmailMessage:
        """
        使用多种策略解析邮件内容
        
        Args:
            content: 邮件内容
            
        Returns:
            解析后的EmailMessage对象
            
        Raises:
            ValueError: 所有策略都失败时抛出
        """
        strategies = cls._get_parsing_strategies()
        last_exception = None
        
        for strategy_name, strategy_func in strategies:
            try:
                logger.debug(f"尝试使用策略: {strategy_name}")
                msg = strategy_func(content)
                if msg:
                    logger.debug(f"策略 {strategy_name} 解析成功")
                    return msg
            except Exception as e:
                logger.debug(f"策略 {strategy_name} 失败: {e}")
                last_exception = e
                continue
        
        # 所有策略都失败
        error_msg = f"所有解析策略都失败，最后错误: {last_exception}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    @classmethod
    def _get_parsing_strategies(cls) -> List[tuple]:
        """
        获取解析策略列表
        
        Returns:
            策略列表，每个元素为(策略名称, 策略函数)
        """
        return [
            ("strict", lambda c: cls._parse_with_policy(c, policy.strict)),
            ("default", lambda c: cls._parse_with_policy(c, policy.default)),
            ("compat32", lambda c: cls._parse_with_policy(c, policy.compat32)),
            ("lenient", lambda c: cls._parse_with_policy(c, cls._create_lenient_policy())),
        ]
    
    @classmethod
    def _parse_with_policy(cls, content: Union[str, bytes], parse_policy) -> EmailMessage:
        """
        使用指定策略解析邮件
        
        Args:
            content: 邮件内容
            parse_policy: 解析策略
            
        Returns:
            解析后的EmailMessage对象
        """
        if isinstance(content, bytes):
            parser = BytesParser(policy=parse_policy)
            return parser.parsebytes(content)
        else:
            parser = Parser(policy=parse_policy)
            return parser.parsestr(content)
    
    @classmethod
    def _create_lenient_policy(cls):
        """
        创建宽松的解析策略
        
        Returns:
            宽松的解析策略
        """
        return policy.default.clone(
            raise_on_defect=False,  # 不因为格式缺陷抛出异常
            max_line_length=None,   # 不限制行长度
            mangle_from_=False,     # 不修改From行
        )


class EmailPreprocessor:
    """邮件预处理器"""
    
    @classmethod
    def preprocess_content(cls, raw_content: Union[str, bytes]) -> Union[str, bytes]:
        """
        预处理邮件内容以提高解析兼容性
        
        Args:
            raw_content: 原始邮件内容
            
        Returns:
            预处理后的邮件内容
        """
        try:
            if isinstance(raw_content, bytes):
                return cls._preprocess_bytes_content(raw_content)
            else:
                return cls._preprocess_string_content(raw_content)
        except Exception as e:
            logger.warning(f"预处理邮件内容失败: {e}")
            return raw_content
    
    @classmethod
    def _preprocess_bytes_content(cls, content: bytes) -> bytes:
        """预处理字节内容"""
        # 尝试解码为字符串进行处理
        try:
            str_content = cls._decode_with_fallback(content)
            processed_str = cls._preprocess_string_content(str_content)
            return processed_str.encode('utf-8')
        except Exception:
            return content
    
    @classmethod
    def _preprocess_string_content(cls, content: str) -> str:
        """预处理字符串内容"""
        # 标准化行结束符
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # 修复常见的格式问题
        content = cls._fix_common_format_issues(content)
        
        # 确保头部和正文之间有空行
        content = cls._ensure_header_body_separation(content)
        
        return content
    
    @classmethod
    def _fix_common_format_issues(cls, content: str) -> str:
        """修复常见的格式问题"""
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # 修复头部字段折行问题
            if i > 0 and line.startswith((' ', '\t')) and fixed_lines:
                # 这是一个折行，合并到上一行
                fixed_lines[-1] += ' ' + line.strip()
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    @classmethod
    def _ensure_header_body_separation(cls, content: str) -> str:
        """确保头部和正文之间有空行"""
        lines = content.split('\n')
        
        # 查找头部结束位置
        header_end = -1
        for i, line in enumerate(lines):
            if line.strip() == "":
                header_end = i
                break
        
        if header_end == -1:
            # 没有找到空行，尝试根据内容判断
            for i, line in enumerate(lines):
                if not line or (":" not in line and not line.startswith(" ")):
                    lines.insert(i, "")
                    break
        
        return '\n'.join(lines)
    
    @classmethod
    def _decode_with_fallback(cls, content_bytes: bytes) -> str:
        """
        使用多种编码尝试解码字节内容
        
        Args:
            content_bytes: 字节内容
            
        Returns:
            解码后的字符串
        """
        encodings = ['utf-8', 'gbk', 'gb2312', 'big5', 'iso-8859-1', 'windows-1252']
        
        for encoding in encodings:
            try:
                return content_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，使用utf-8并忽略错误
        return content_bytes.decode('utf-8', errors='replace')
