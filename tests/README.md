# 测试说明

本目录包含项目的测试代码。

## 运行测试

可以使用以下几种方式运行测试：

### 1. 使用unittest发现并运行所有测试

```
python -m unittest discover tests
```

### 2. 直接运行测试文件（推荐）

```
python tests/test_smtp_client.py
python tests/test_mime_handler.py
```

### 3. 使用unittest模块运行特定测试模块

```
python -m unittest tests.test_smtp_client
python -m unittest tests.test_mime_handler
```

注意：不要使用`python -m unittest tests/test_mime_handler.py`这种形式，因为它会尝试将路径作为模块名导入，这是不正确的。

## 测试文件说明

- `test_smtp_client.py`: 测试SMTP客户端功能
- `test_mime_handler.py`: 测试MIME编码和解码功能

## 添加新测试

添加新测试时，请遵循以下规则：

1. 测试文件名应以`test_`开头
2. 测试类应继承`unittest.TestCase`
3. 测试方法应以`test_`开头
4. 使用`setUp`和`tearDown`方法进行测试前后的准备和清理工作
5. 使用断言方法验证测试结果

## 模拟外部依赖

在测试中，应该使用`unittest.mock`模块模拟外部依赖，如SMTP服务器、文件系统等。这样可以确保测试的独立性和可重复性。

示例：

```python
@patch('smtplib.SMTP')
def test_connect(self, mock_smtp):
    # 设置模拟对象
    mock_smtp_instance = MagicMock()
    mock_smtp.return_value = mock_smtp_instance

    # 创建SMTP客户端
    client = SMTPClient(host="localhost", port=465)

    # 连接
    client.connect()

    # 验证
    mock_smtp.assert_called_once_with("localhost", 465, timeout=30)
```

## 跨平台测试注意事项

在不同操作系统上运行测试时，可能会遇到一些平台特定的差异，需要特别注意：

### 1. MIME类型识别

不同操作系统对文件MIME类型的识别可能有所不同。例如：
- Windows可能将`.zip`文件识别为`application/x-zip-compressed`
- Linux/Mac可能将`.zip`文件识别为`application/zip`

解决方法：在测试中使用条件判断或适配不同平台的预期值。

### 2. 邮件头编码

中文等非ASCII字符在邮件头中会被编码（通常是Base64或Quoted-Printable），这会导致直接字符串比较失败。

解决方法：使用`MIMEHandler.decode_header_value`方法先解码邮件头，再与预期值进行比较：

```python
# 错误方式
self.assertEqual(msg['From'], f"{email.from_addr.name} <{email.from_addr.address}>")

# 正确方式
self.assertEqual(
    MIMEHandler.decode_header_value(msg['From']),
    f"{email.from_addr.name} <{email.from_addr.address}>"
)
```

### 3. 文件路径分隔符

Windows使用反斜杠`\`，而Unix/Linux使用正斜杠`/`作为路径分隔符。

解决方法：使用`os.path.join`和`pathlib.Path`来处理路径，避免硬编码路径分隔符。
