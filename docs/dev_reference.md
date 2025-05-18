# Python 邮件服务开发指南：PGP加密、SMTP认证与SQLite存储

## 一、PGP电子邮件加密

### 1.1 PGP简介

PGP (Pretty Good Privacy) 是一种加密标准，用于保护电子邮件通信、文件和其他数据的安全。它使用公钥加密技术对数据进行加密和解密，以及使用数字签名验证数据的真实性和完整性。

PGP加密过程包括：
- 哈希处理
- 数据压缩
- 对称密钥加密
- 公钥加密

### 1.2 在Python中使用PGP加密电子邮件

可以使用`python-gnupg`库在Python中实现PGP加密功能，该库提供了与GnuPG的高级接口。

#### 安装必要的库

```bash
pip install python-gnupg
```

#### 基本PGP加密示例

```python
import gnupg

def pgp_encrypt_file(file_path, recipient_key):
    # 初始化GPG对象
    gpg = gnupg.GPG()
    
    # 读取文件内容
    with open(file_path, 'rb') as file:
        file_data = file.read()
    
    # 使用收件人的公钥加密文件
    encrypted_data = gpg.encrypt_file(
        file_data,
        recipients=recipient_key,
        output=file_path + '.pgp'
    )
    
    # 保存加密后的文件
    with open(file_path + '.pgp', 'wb') as encrypted_file:
        encrypted_file.write(str(encrypted_data).encode())
    
    print('加密成功。加密文件保存为', file_path + '.pgp')
```

#### 生成PGP密钥对

以下是一个在Python中生成PGP密钥对的示例：

```python
import gnupg

gpg = gnupg.GPG()

# 生成密钥参数
key_params = {
    'name_real': '用户名',
    'name_email': 'user@example.com',
    'key_type': 'RSA',
    'key_length': 4096,
    'key_usage': '',
    'subkey_type': 'RSA',
    'subkey_length': 4096,
    'subkey_usage': 'encrypt,sign,auth',
    'passphrase': '密码短语'
}

# 生成密钥
key = gpg.gen_key(gpg.gen_key_input(**key_params))
print(f"生成的密钥ID: {key}")
```

#### 对电子邮件内容进行PGP加密和签名

以下是加密和签名电子邮件内容的示例：

```python
import gnupg

def encrypt_email_content(content, recipient_key, sender_key, passphrase):
    gpg = gnupg.GPG()
    
    # 加密并签名内容
    encrypted_data = gpg.encrypt(content, recipient_key, sign=sender_key, passphrase=passphrase)
    
    if encrypted_data.ok:
        return str(encrypted_data)
    else:
        raise Exception(f"加密失败: {encrypted_data.status}")
```

### 1.3 与电子邮件系统集成

要将PGP加密与电子邮件系统集成，可以使用`emailpgp`库，该库扩展了Python的email类来添加MIME multipart/pgp-encrypted类型的消息：

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import gnupg

def send_encrypted_email(sender, recipient, subject, content, recipient_key, sender_key, passphrase):
    # 加密内容
    gpg = gnupg.GPG()
    encrypted_content = gpg.encrypt(content, recipient_key, sign=sender_key, passphrase=passphrase)
    
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = recipient
    msg['Subject'] = subject
    
    # 添加加密内容
    msg.attach(MIMEText(str(encrypted_content), 'plain'))
    
    # 发送邮件
    server = smtplib.SMTP('smtp.example.com', 587)
    server.starttls()
    server.login(sender, 'your_password')
    server.send_message(msg)
    server.quit()
```

## 二、SMTP SSL/TLS认证

### 2.1 SMTP认证简介

SMTP (Simple Mail Transfer Protocol) 是用于发送电子邮件的标准协议。为了安全起见，现代SMTP服务器通常需要身份验证和加密连接。主要的身份验证方法包括：

- **LOGIN**: 基本的用户名密码认证
- **PLAIN**: 明文认证，通常与TLS加密一起使用以提高安全性
- **CRAM-MD5**: 一种更安全的挑战-响应认证机制
- **OAuth2**: 基于令牌的认证方法，越来越多地被大型邮件提供商采用

### 2.2 在Python中使用SMTP SSL/TLS认证

Python的`smtplib`库提供了用于与SMTP服务器进行加密通信和身份验证的功能。

#### 使用STARTTLS

STARTTLS是一种通过在普通连接上建立TLS/SSL加密来加密通信的方法：

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_with_starttls(sender_email, receiver_email, subject, message, password):
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    
    # 添加消息体
    msg.attach(MIMEText(message, 'plain'))
    
    try:
        # 连接到服务器
        server = smtplib.SMTP('smtp.example.com', 587)
        server.ehlo()  # 向服务器标识自己
        
        # 启动TLS加密
        server.starttls()
        server.ehlo()  # 重新标识
        
        # 登录
        server.login(sender_email, password)
        
        # 发送邮件
        server.send_message(msg)
        print("邮件发送成功！")
    except Exception as e:
        print(f"发送失败: {e}")
    finally:
        server.quit()
```

#### 使用SSL连接

如果服务器支持隐式SSL，可以直接使用SSL连接：

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_with_ssl(sender_email, receiver_email, subject, message, password):
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    
    # 添加消息体
    msg.attach(MIMEText(message, 'plain'))
    
    try:
        # 使用SSL连接到服务器
        server = smtplib.SMTP_SSL('smtp.example.com', 465)
        server.ehlo()
        
        # 登录
        server.login(sender_email, password)
        
        # 发送邮件
        server.send_message(msg)
        print("邮件发送成功！")
    except Exception as e:
        print(f"发送失败: {e}")
    finally:
        server.quit()
```

### 2.3 不同认证方法的实现

#### LOGIN认证

LOGIN认证是最基本的认证方式，通过用户名和密码进行认证：

```python
server.login(username, password)  # 自动使用LOGIN认证
```

#### PLAIN认证

您可以显式使用PLAIN认证：

```python
import base64
import smtplib

def smtp_auth_plain(server, username, password):
    auth_str = f"\0{username}\0{password}"
    auth_bytes = auth_str.encode('utf-8')
    encoded_auth = base64.b64encode(auth_bytes).decode('utf-8')
    server.ehlo()
    server.docmd("AUTH", f"PLAIN {encoded_auth}")
```

#### CRAM-MD5认证

对于CRAM-MD5认证，Python的`smtplib`提供了内置支持：

```python
server.login(username, password)  # 如果服务器支持CRAM-MD5，会自动使用
```

您还可以显式使用`smtplib`的内置认证对象：

```python
import smtplib

server = smtplib.SMTP('smtp.example.com', 587)
server.starttls()
server.ehlo()

# 使用CRAM-MD5认证
auth_object = server.auth_cram_md5
server.user = username
server.password = password
server.auth('CRAM-MD5', auth_object)
```

## 三、使用SQLite存储电子邮件

### 3.1 SQLite数据库简介

SQLite是一个轻量级、无服务器的关系型数据库管理系统，它存储在单个文件中，无需安装或配置额外的服务器。这使得它非常适合小型到中型应用程序，如邮件客户端。

主要优点包括：
- 轻量级且零配置
- 文件基础，便于备份和移动
- 支持ACID事务
- 不需要单独的服务器进程
- 跨平台兼容性高

### 3.2 设计电子邮件存储数据库结构

下面是一个用于存储电子邮件的SQLite数据库设计示例：

```python
import sqlite3

def create_email_database():
    with sqlite3.connect('emails.db') as conn:
        cursor = conn.cursor()
        
        # 创建邮件表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE NOT NULL,
            thread_id TEXT,
            sender TEXT NOT NULL,
            sender_email TEXT NOT NULL,
            recipients TEXT NOT NULL,
            subject TEXT,
            body TEXT,
            html_body TEXT,
            received_date TIMESTAMP NOT NULL,
            read INTEGER DEFAULT 0,
            starred INTEGER DEFAULT 0,
            size INTEGER,
            attachments INTEGER DEFAULT 0,
            folder TEXT DEFAULT 'inbox'
        )
        ''')
        
        # 创建附件表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            mime_type TEXT,
            size INTEGER,
            content BLOB,
            FOREIGN KEY (email_id) REFERENCES emails (id) ON DELETE CASCADE
        )
        ''')
        
        # 创建标签表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS labels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        ''')
        
        # 创建邮件-标签关系表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_labels (
            email_id INTEGER NOT NULL,
            label_id INTEGER NOT NULL,
            PRIMARY KEY (email_id, label_id),
            FOREIGN KEY (email_id) REFERENCES emails (id) ON DELETE CASCADE,
            FOREIGN KEY (label_id) REFERENCES labels (id) ON DELETE CASCADE
        )
        ''')
        
        # 创建索引以提高查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_date ON emails (received_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails (sender_email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_folder ON emails (folder)')
        
        conn.commit()
        print("电子邮件数据库创建成功！")
```

### 3.3 存储和检索电子邮件

#### 存储电子邮件

```python
def store_email(message_id, thread_id, sender, sender_email, recipients, subject, body, html_body, received_date, size, folder='inbox'):
    with sqlite3.connect('emails.db') as conn:
        cursor = conn.cursor()
        
        # 插入邮件数据
        cursor.execute('''
        INSERT INTO emails 
        (message_id, thread_id, sender, sender_email, recipients, subject, body, html_body, received_date, size, folder) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (message_id, thread_id, sender, sender_email, recipients, subject, body, html_body, received_date, size, folder))
        
        email_id = cursor.lastrowid
        conn.commit()
        return email_id
```

#### 存储附件

```python
def store_attachment(email_id, filename, mime_type, size, content):
    with sqlite3.connect('emails.db') as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO attachments 
        (email_id, filename, mime_type, size, content) 
        VALUES (?, ?, ?, ?, ?)
        ''', (email_id, filename, mime_type, size, content))
        
        # 更新邮件表中的附件计数
        cursor.execute('UPDATE emails SET attachments = attachments + 1 WHERE id = ?', (email_id,))
        
        conn.commit()
```

#### 检索电子邮件

```python
def get_emails_from_folder(folder, limit=50, offset=0):
    with sqlite3.connect('emails.db') as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, message_id, sender, sender_email, subject, received_date, read, starred, size, attachments 
        FROM emails 
        WHERE folder = ? 
        ORDER BY received_date DESC 
        LIMIT ? OFFSET ?
        ''', (folder, limit, offset))
        
        return cursor.fetchall()
```

#### 检索单个电子邮件内容

```python
def get_email_content(email_id):
    with sqlite3.connect('emails.db') as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, message_id, thread_id, sender, sender_email, recipients, 
               subject, body, html_body, received_date, read, starred, size, attachments, folder
        FROM emails 
        WHERE id = ?
        ''', (email_id,))
        
        email_data = cursor.fetchone()
        
        if email_data:
            # 标记为已读
            cursor.execute('UPDATE emails SET read = 1 WHERE id = ?', (email_id,))
            conn.commit()
            
            # 获取附件列表
            cursor.execute('SELECT id, filename, mime_type, size FROM attachments WHERE email_id = ?', (email_id,))
            attachments = cursor.fetchall()
            
            # 创建结果字典
            email = {
                'id': email_data[0],
                'message_id': email_data[1],
                'thread_id': email_data[2],
                'sender': email_data[3],
                'sender_email': email_data[4],
                'recipients': email_data[5],
                'subject': email_data[6],
                'body': email_data[7],
                'html_body': email_data[8],
                'received_date': email_data[9],
                'read': email_data[10],
                'starred': email_data[11],
                'size': email_data[12],
                'attachments_count': email_data[13],
                'folder': email_data[14],
                'attachments': attachments
            }
            
            return email
        
        return None
```

### 3.4 电子邮件搜索功能

```python
def search_emails(search_term, folders=None):
    with sqlite3.connect('emails.db') as conn:
        cursor = conn.cursor()
        
        query = '''
        SELECT id, message_id, sender, sender_email, subject, received_date, read, starred, size, attachments, folder
        FROM emails 
        WHERE (subject LIKE ? OR body LIKE ? OR sender LIKE ? OR sender_email LIKE ?)
        '''
        
        params = ['%' + search_term + '%'] * 4
        
        if folders:
            placeholders = ','.join('?' * len(folders))
            query += f' AND folder IN ({placeholders})'
            params.extend(folders)
        
        query += ' ORDER BY received_date DESC'
        
        cursor.execute(query, params)
        return cursor.fetchall()
```

### 3.5 电子邮件统计和分析

```python
def get_email_statistics():
    with sqlite3.connect('emails.db') as conn:
        cursor = conn.cursor()
        
        stats = {}
        
        # 总邮件数
        cursor.execute('SELECT COUNT(*) FROM emails')
        stats['total_emails'] = cursor.fetchone()[0]
        
        # 未读邮件数
        cursor.execute('SELECT COUNT(*) FROM emails WHERE read = 0')
        stats['unread_emails'] = cursor.fetchone()[0]
        
        # 按文件夹统计
        cursor.execute('SELECT folder, COUNT(*) FROM emails GROUP BY folder')
        stats['folders'] = dict(cursor.fetchall())
        
        # 按发件人统计
        cursor.execute('''
        SELECT sender_email, COUNT(*) 
        FROM emails 
        GROUP BY sender_email 
        ORDER BY COUNT(*) DESC 
        LIMIT 10
        ''')
        stats['top_senders'] = dict(cursor.fetchall())
        
        # 按日期统计
        cursor.execute('''
        SELECT strftime('%Y-%m', received_date) as month, COUNT(*) 
        FROM emails 
        GROUP BY month 
        ORDER BY month DESC
        LIMIT 12
        ''')
        stats['emails_by_month'] = dict(cursor.fetchall())
        
        return stats
```

## 四、完整示例：安全邮件客户端

下面是一个整合以上所有功能的简单示例，展示如何创建一个基本的安全邮件客户端：

```python
import sqlite3
import smtplib
import gnupg
import email
import imaplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime
import base64

class SecureEmailClient:
    def __init__(self, db_path='emails.db'):
        self.db_path = db_path
        self.gpg = gnupg.GPG()
        self.setup_database()
    
    def setup_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建emails表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE NOT NULL,
                thread_id TEXT,
                sender TEXT NOT NULL,
                sender_email TEXT NOT NULL,
                recipients TEXT NOT NULL,
                subject TEXT,
                body TEXT,
                html_body TEXT,
                received_date TIMESTAMP NOT NULL,
                read INTEGER DEFAULT 0,
                starred INTEGER DEFAULT 0,
                size INTEGER,
                attachments INTEGER DEFAULT 0,
                folder TEXT DEFAULT 'inbox',
                encrypted INTEGER DEFAULT 0
            )
            ''')
            
            # 创建附件表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                mime_type TEXT,
                size INTEGER,
                content BLOB,
                FOREIGN KEY (email_id) REFERENCES emails (id) ON DELETE CASCADE
            )
            ''')
            
            # 索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_date ON emails (received_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_sender ON emails (sender_email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_emails_folder ON emails (folder)')
            
            conn.commit()
    
    def connect_imap(self, server, port, username, password, use_ssl=True):
        if use_ssl:
            self.imap = imaplib.IMAP4_SSL(server, port)
        else:
            self.imap = imaplib.IMAP4(server, port)
            self.imap.starttls()
        
        self.imap.login(username, password)
        return self.imap
    
    def fetch_emails(self, folder='INBOX', limit=10):
        self.imap.select(folder)
        status, data = self.imap.search(None, 'ALL')
        email_ids = data[0].split()
        
        # 最新的邮件先获取
        email_ids = email_ids[-limit:]
        
        for email_id in reversed(email_ids):
            status, data = self.imap.fetch(email_id, '(RFC822)')
            raw_email = data[0][1]
            parsed_email = email.message_from_bytes(raw_email)
            
            # 解析邮件内容
            message_id = parsed_email.get('Message-ID', '')
            subject = parsed_email.get('Subject', '')
            sender = parsed_email.get('From', '')
            sender_name, sender_email = self.extract_sender(sender)
            date_str = parsed_email.get('Date', '')
            received_date = self.parse_date(date_str)
            recipients = parsed_email.get('To', '')
            
            # 获取邮件正文
            body = ""
            html_body = ""
            is_encrypted = False
            
            for part in parsed_email.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    if "-----BEGIN PGP MESSAGE-----" in body:
                        is_encrypted = True
                        # 尝试解密
                        decrypted_data = self.gpg.decrypt(body)
                        if decrypted_data.ok:
                            body = str(decrypted_data)
                
                elif part.get_content_type() == "text/html":
                    html_body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # 存储邮件到数据库
            email_size = len(raw_email)
            self.store_email(message_id, "", sender_name, sender_email, recipients, subject, 
                           body, html_body, received_date, email_size, folder.lower(), is_encrypted)
    
    def extract_sender(self, sender_string):
        # 从发件人字符串中提取名字和邮箱
        if '<' in sender_string and '>' in sender_string:
            name = sender_string.split('<')[0].strip(' "\'')
            email = sender_string.split('<')[1].split('>')[0].strip()
            return name, email
        else:
            return sender_string, sender_string
    
    def parse_date(self, date_str):
        # 解析日期字符串为datetime对象
        try:
            return email.utils.parsedate_to_datetime(date_str)
        except:
            return datetime.datetime.now()
    
    def store_email(self, message_id, thread_id, sender, sender_email, recipients, subject, 
                   body, html_body, received_date, size, folder='inbox', encrypted=False):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 检查邮件是否已存在
            cursor.execute('SELECT id FROM emails WHERE message_id = ?', (message_id,))
            existing = cursor.fetchone()
            
            if existing:
                return existing[0]
            
            # 插入新邮件
            cursor.execute('''
            INSERT INTO emails 
            (message_id, thread_id, sender, sender_email, recipients, subject, body, html_body, 
             received_date, size, folder, encrypted) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (message_id, thread_id, sender, sender_email, recipients, subject, body, html_body, 
                 received_date, size, folder, 1 if encrypted else 0))
            
            email_id = cursor.lastrowid
            conn.commit()
            return email_id
    
    def send_encrypted_email(self, smtp_server, smtp_port, sender_email, password, 
                           recipient_email, subject, message, recipient_key, use_ssl=True):
        # 加密消息
        encrypted_data = self.gpg.encrypt(message, recipient_key)
        
        if not encrypted_data.ok:
            raise Exception(f"加密失败: {encrypted_data.status}")
        
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # 添加加密后的内容
        msg.attach(MIMEText(str(encrypted_data), 'plain'))
        
        # 发送邮件
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
        
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        
        # 存储到发件箱
        now = datetime.datetime.now()
        message_id = f"<{base64.b64encode(now.isoformat().encode()).decode()}@{sender_email.split('@')[1]}>"
        self.store_email(message_id, "", sender_email, sender_email, recipient_email, subject, 
                       message, "", now, len(str(msg)), 'sent', True)
    
    def get_emails_from_folder(self, folder, limit=50, offset=0):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id, message_id, sender, sender_email, subject, received_date, read, starred, size, 
                   attachments, encrypted
            FROM emails 
            WHERE folder = ? 
            ORDER BY received_date DESC 
            LIMIT ? OFFSET ?
            ''', (folder, limit, offset))
            
            emails = []
            for row in cursor.fetchall():
                emails.append({
                    'id': row[0],
                    'message_id': row[1],
                    'sender': row[2],
                    'sender_email': row[3],
                    'subject': row[4],
                    'date': row[5],
                    'read': bool(row[6]),
                    'starred': bool(row[7]),
                    'size': row[8],
                    'attachments': row[9],
                    'encrypted': bool(row[10])
                })
            
            return emails
    
    def search_emails(self, search_term, folders=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = '''
            SELECT id, message_id, sender, sender_email, subject, received_date, read, starred, size, 
                   attachments, folder, encrypted
            FROM emails 
            WHERE (subject LIKE ? OR body LIKE ? OR sender LIKE ? OR sender_email LIKE ?)
            '''
            
            params = ['%' + search_term + '%'] * 4
            
            if folders:
                placeholders = ','.join('?' * len(folders))
                query += f' AND folder IN ({placeholders})'
                params.extend(folders)
            
            query += ' ORDER BY received_date DESC'
            
            cursor.execute(query, params)
            
            emails = []
            for row in cursor.fetchall():
                emails.append({
                    'id': row[0],
                    'message_id': row[1],
                    'sender': row[2],
                    'sender_email': row[3],
                    'subject': row[4],
                    'date': row[5],
                    'read': bool(row[6]),
                    'starred': bool(row[7]),
                    'size': row[8],
                    'attachments': row[9],
                    'folder': row[10],
                    'encrypted': bool(row[11])
                })
            
            return emails
    
    def get_email_statistics(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # 总邮件数
            cursor.execute('SELECT COUNT(*) FROM emails')
            stats['total_emails'] = cursor.fetchone()[0]
            
            # 未读邮件数
            cursor.execute('SELECT COUNT(*) FROM emails WHERE read = 0')
            stats['unread_emails'] = cursor.fetchone()[0]
            
            # 加密邮件数
            cursor.execute('SELECT COUNT(*) FROM emails WHERE encrypted = 1')
            stats['encrypted_emails'] = cursor.fetchone()[0]
            
            # 按文件夹统计
            cursor.execute('SELECT folder, COUNT(*) FROM emails GROUP BY folder')
            stats['folders'] = dict(cursor.fetchall())
            
            # 按发件人统计
            cursor.execute('''
            SELECT sender_email, COUNT(*) 
            FROM emails 
            GROUP BY sender_email 
            ORDER BY COUNT(*) DESC 
            LIMIT 10
            ''')
            stats['top_senders'] = dict(cursor.fetchall())
            
            return stats
    
    def close(self):
        if hasattr(self, 'imap') and self.imap:
            self.imap.logout()
```

### 使用示例

```python
# 创建客户端实例
client = SecureEmailClient()

# 连接到IMAP服务器获取邮件
client.connect_imap('imap.example.com', 993, 'your_email@example.com', 'your_password')
client.fetch_emails(limit=20)

# 获取收件箱中的邮件
inbox_emails = client.get_emails_from_folder('inbox')
for email in inbox_emails:
    print(f"发件人: {email['sender']} ({email['sender_email']})")
    print(f"主题: {email['subject']}")
    print(f"日期: {email['date']}")
    print(f"已读: {'是' if email['read'] else '否'}")
    print(f"加密: {'是' if email['encrypted'] else '否'}")
    print("-" * 40)

# 发送加密邮件
client.send_encrypted_email(
    'smtp.example.com', 465, 
    'your_email@example.com', 'your_password',
    'recipient@example.com', '加密消息测试',
    '这是一条加密消息的内容。',
    'recipient_public_key_id'
)

# 搜索邮件
search_results = client.search_emails('重要')
print(f"找到 {len(search_results)} 封包含 '重要' 的邮件")

# 获取统计信息
stats = client.get_email_statistics()
print(f"总邮件数: {stats['total_emails']}")
print(f"未读邮件数: {stats['unread_emails']}")
print(f"加密邮件数: {stats['encrypted_emails']}")

# 关闭连接
client.close()
```

## 总结

本文提供了关于如何在Python中结合使用PGP加密、SMTP认证和SQLite存储来构建安全的电子邮件系统的全面指南。通过这些技术的组合，您可以:

1. 使用PGP加密保护电子邮件内容的机密性和完整性
2. 通过SSL/TLS和各种认证方法确保与SMTP服务器的安全通信
3. 使用SQLite数据库高效地存储和检索电子邮件，并支持强大的搜索和分析功能

这些技术可以用于开发安全的电子邮件客户端、邮件归档系统或需要处理敏感信息的任何应用程序。在实际应用中，还可以根据需求进一步优化数据库结构、改进加密流程，以及增强错误处理和安全性。
