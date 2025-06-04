"""
PGP端到端加密模块

提供邮件的PGP加密、解密、签名和验证功能
"""

from .pgp_manager import PGPManager, PGPError
from .key_manager import KeyManager 
from .email_crypto import EmailCrypto

__all__ = ["PGPManager", "KeyManager", "EmailCrypto", "PGPError"]

# 版本信息
__version__ = "1.0.0"