# 依赖说明文档

本文档详细说明了CS3611邮件客户端项目的所有依赖库及其用途。

## 依赖文件说明

项目提供了三个不同的依赖文件：

### 1. `requirements-minimal.txt`
**用途**: 最小化生产环境  
**包含**: 仅运行邮件客户端核心功能所需的最少依赖  
**适用场景**: 
- 生产环境部署
- 资源受限的环境
- 只需要基本邮件收发功能

### 2. `requirements.txt`
**用途**: 标准完整安装  
**包含**: 运行完整邮件系统所需的所有依赖  
**适用场景**:
- 完整功能使用
- 包含Web界面和GUI
- 包含垃圾邮件过滤等高级功能

### 3. `requirements-dev.txt`
**用途**: 开发环境  
**包含**: 开发、测试、调试所需的所有工具  
**适用场景**:
- 项目开发
- 代码测试
- 文档生成

## 核心依赖详解

### 加密和安全
- **cryptography** (>=41.0.0): 提供加密功能和SSL/TLS支持
- **pyOpenSSL** (>=23.0.0): SSL/TLS连接实现

### 邮件服务器
- **aiosmtpd** (>=1.4.4): 异步SMTP服务器框架，用于实现SMTP服务器

### 数据库
- **SQLAlchemy** (>=2.0.0): ORM框架，用于高级数据库操作
- **alembic** (>=1.12.0): 数据库迁移工具

### 邮件处理
- **dnspython** (>=2.4.0): DNS查询功能，用于邮件服务器查找
- **email-validator** (>=2.0.0): 邮件地址格式验证

## 可选依赖详解

### 扩展功能
- **python-gnupg** (>=0.5.0): PGP加密支持
- **scikit-learn** (>=1.3.0): 机器学习库，用于垃圾邮件过滤
- **nltk** (>=3.8.1): 自然语言处理，用于邮件内容分析

### Web界面
- **Flask** (>=2.3.0): Web框架
- **Flask-WTF** (>=1.2.0): 表单处理
- **Flask-Login** (>=0.6.2): 用户认证
- **Jinja2** (>=3.1.0): 模板引擎

### GUI界面
- **PyQt5** (>=5.15.0): GUI框架，用于图形界面

### 开发工具
- **pytest** (>=7.4.0): 测试框架
- **pytest-cov** (>=4.1.0): 测试覆盖率
- **pytest-asyncio** (>=0.21.0): 异步测试支持
- **black** (>=23.0.0): 代码格式化
- **isort** (>=5.12.0): 导入排序
- **flake8** (>=6.0.0): 代码检查
- **mypy** (>=1.5.0): 类型检查

## 安装建议

### 新用户
```bash
# 使用自动安装脚本（推荐）
python install_dependencies.py
```

### 生产环境
```bash
# 最小安装
pip install -r requirements-minimal.txt
```

### 开发环境
```bash
# 完整开发环境
pip install -r requirements-dev.txt
```

### 特定功能
```bash
# 只需要Web界面
pip install Flask Flask-WTF Flask-Login Jinja2

# 只需要GUI界面
pip install PyQt5

# 只需要垃圾邮件过滤
pip install scikit-learn nltk
```

## 版本兼容性

### Python版本
- **最低要求**: Python 3.8
- **推荐版本**: Python 3.9+
- **测试版本**: Python 3.8, 3.9, 3.10, 3.11

### 操作系统
- **Windows**: 完全支持
- **Linux**: 完全支持
- **macOS**: 完全支持

## 故障排除

### 常见问题

1. **SSL相关错误**
   ```bash
   pip install --upgrade cryptography pyOpenSSL
   ```

2. **PyQt5安装失败**
   ```bash
   # Windows
   pip install PyQt5 --only-binary=all
   
   # Linux
   sudo apt-get install python3-pyqt5
   ```

3. **编译错误**
   ```bash
   # 升级构建工具
   pip install --upgrade setuptools wheel
   ```

### 检查安装
```bash
# 运行依赖检查脚本
python check_dependencies.py
```

## 更新依赖

### 定期更新
```bash
# 更新所有依赖到最新版本
pip install --upgrade -r requirements.txt
```

### 安全更新
```bash
# 检查安全漏洞
pip install safety
safety check

# 检查过时的包
pip list --outdated
```
