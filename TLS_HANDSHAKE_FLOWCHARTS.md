# TLS握手流程专业图表集合
## 基于RFC 5246 (TLS 1.2) 和 RFC 8446 (TLS 1.3) 标准规范

本文档包含高质量的TLS握手流程图表，适合学术海报打印和技术文档使用。

---

## TLS 1.2 握手流程图 (2-RTT)

```mermaid
sequenceDiagram
    participant C as 客户端<br/>(Client)
    participant S as 服务器<br/>(Server)
    
    Note over C,S: TLS 1.2 握手过程 (2-RTT)
    
    rect rgba(255, 230, 230, 0.8)
        Note over C,S: 第一轮往返 (First Round Trip)
        
        C->>S: 1. ClientHello
        Note right of C: • TLS版本: 1.2<br/>• 客户端随机数<br/>• 支持的密码套件<br/>• 压缩方法<br/>• 扩展
        
        S->>C: 2. ServerHello  
        Note left of S: • 选定TLS版本<br/>• 服务器随机数<br/>• 选定密码套件<br/>• 会话ID
        
        S->>C: 3. Certificate
        Note left of S: • X.509证书链<br/>• 服务器公钥<br/>• 证书签名
        
        S->>C: 4. ServerKeyExchange*
        Note left of S: • DHE/ECDHE参数<br/>• 服务器签名<br/>• (仅临时密钥交换)
        
        S->>C: 5. CertificateRequest*
        Note left of S: • 证书类型<br/>• 支持的签名算法<br/>• 可信CA列表
        
        S->>C: 6. ServerHelloDone
        Note left of S: 服务器Hello阶段结束
    end
    
    rect rgba(230, 255, 230, 0.8)  
        Note over C,S: 第二轮往返 (Second Round Trip)
        
        C->>S: 7. Certificate*
        Note right of C: • 客户端证书<br/>• (响应CertificateRequest)
        
        C->>S: 8. ClientKeyExchange
        Note right of C: • RSA: 加密的PreMasterSecret<br/>• DHE/ECDHE: 客户端公钥<br/>• PSK: PSK身份
        
        C->>S: 9. CertificateVerify*
        Note right of C: • 客户端私钥签名<br/>• 证明拥有私钥
        
        C->>S: 10. [ChangeCipherSpec]
        Note right of C: 启用加密通信
        
        C->>S: 11. Finished
        Note right of C: • 握手消息MAC<br/>• 完整性验证
        
        S->>S: 验证Finished消息
        
        S->>C: 12. [ChangeCipherSpec]
        Note left of S: 启用加密通信
        
        S->>C: 13. Finished
        Note left of S: • 握手消息MAC<br/>• 完整性验证
    end
    
    rect rgba(230, 230, 255, 0.8)
        Note over C,S: 应用数据传输 (Application Data)
        C->>S: 应用层数据 (Client to Server)
        S->>C: 应用层数据 (Server to Client)
        Note over C,S: 使用对称密钥加密
    end
    
    Note over C,S: * 表示可选消息<br/>[ ] 表示记录层协议消息
```

---

## TLS 1.3 握手流程图 (1-RTT)

```mermaid
sequenceDiagram
    participant C as 客户端<br/>(Client)  
    participant S as 服务器<br/>(Server)
    
    Note over C,S: TLS 1.3 握手过程 (1-RTT)
    
    rect rgba(255, 230, 255, 0.8)
        Note over C,S: 密钥交换阶段 (Key Exchange)
        
        C->>S: 1. ClientHello + key_share
        Note right of C: • TLS版本: 1.3<br/>• 客户端随机数<br/>• 支持的密码套件<br/>• key_share扩展<br/>• signature_algorithms<br/>• psk_key_exchange_modes*<br/>• pre_shared_key*
        
        S->>C: 2. ServerHello + key_share  
        Note left of S: • 选定密码套件<br/>• 服务器随机数<br/>• key_share扩展<br/>• pre_shared_key*
        
        Note over C,S: 🔑 握手流量密钥生成完成<br/>后续消息使用握手密钥加密
    end
    
    rect rgba(255, 255, 230, 0.8)
        Note over C,S: 服务器参数阶段 (Server Parameters)
        
        S->>C: 3. {EncryptedExtensions}
        Note left of S: • 加密的扩展<br/>• 服务器配置参数
        
        S->>C: 4. {CertificateRequest}*
        Note left of S: • 客户端证书请求<br/>• 支持的签名算法
        
        S->>C: 5. {Certificate}*
        Note left of S: • 服务器证书链<br/>• X.509证书
        
        S->>C: 6. {CertificateVerify}*
        Note left of S: • 服务器私钥签名<br/>• 覆盖整个握手过程
        
        S->>C: 7. {Finished}
        Note left of S: • 握手完整性验证<br/>• HMAC覆盖所有握手消息
        
        Note over C,S: 🔑 应用流量密钥生成完成<br/>服务器可发送应用数据
    end
    
    rect rgba(230, 255, 255, 0.8)
        Note over C,S: 客户端认证阶段 (Client Authentication)
        
        C->>S: 8. {Certificate}*
        Note right of C: • 客户端证书链<br/>• (响应CertificateRequest)
        
        C->>S: 9. {CertificateVerify}*
        Note right of C: • 客户端私钥签名<br/>• 证明拥有私钥
        
        C->>S: 10. {Finished}
        Note right of C: • 客户端握手验证<br/>• 握手过程完成
    end
    
    rect rgba(230, 255, 230, 0.8)
        Note over C,S: 应用数据传输 (Application Data)
        C->>S: [应用层数据] (Client to Server)
        S->>C: [应用层数据] (Server to Client)
        Note over C,S: 使用应用流量密钥<br/>AEAD加密模式
    end
    
    Note over C,S: {} 表示握手流量密钥加密<br/>[] 表示应用流量密钥加密<br/>* 表示可选消息
```

---

## TLS 1.3 零往返时间 (0-RTT) 模式

```mermaid
sequenceDiagram
    participant C as 客户端<br/>(Client)
    participant S as 服务器<br/>(Server)
    
    Note over C,S: TLS 1.3 零往返时间模式 (0-RTT)
    Note over C,S: ⚠️ 基于之前会话的PSK
    
    rect rgba(255, 200, 200, 0.8)
        Note over C,S: 早期数据传输 (Early Data)
        
        C->>S: 1. ClientHello + early_data + [应用数据]
        Note right of C: • pre_shared_key扩展<br/>• early_data扩展<br/>• 0-RTT应用数据<br/>• 使用早期流量密钥加密
        
        Note over C,S: ⚠️ 重放攻击风险<br/>应用层需要幂等性
    end
    
    rect rgba(200, 255, 200, 0.8)
        Note over C,S: 服务器响应 (Server Response)
        
        S->>C: 2. ServerHello + early_data*
        Note left of S: • 确认PSK使用<br/>• early_data扩展<br/>• (接受或拒绝0-RTT)
        
        S->>C: 3. {EncryptedExtensions}
        S->>C: 4. {Finished}
        S->>C: 5. [应用数据响应]
        Note left of S: 服务器应用数据
    end
    
    rect rgba(200, 200, 255, 0.8)
        Note over C,S: 客户端完成 (Client Completion)
        
        C->>S: 6. {Finished}
        Note right of C: 握手完成确认
        
        C->>S: 7. [正常应用数据]  
        Note right of C: 1-RTT后的安全数据
    end
    
    rect rgba(230, 255, 230, 0.8)
        Note over C,S: 正常应用数据传输
        C->>S: [双向加密通信] (Client to Server)
        S->>C: [双向加密通信] (Server to Client)
        Note over C,S: 完全安全的通信
    end
    
    Note over C,S: ⚠️ 0-RTT数据可能被重放<br/>仅适用于幂等操作
```

---

## TLS 1.2 vs 1.3 性能对比图

```mermaid
gantt
    title TLS握手性能对比 (时间轴)
    dateFormat X
    axisFormat %s
    
    section TLS 1.2 (2-RTT)
    ClientHello           :milestone, ch12, 0, 0
    ServerHello + Cert    :milestone, sh12, 50, 50  
    ClientKeyExchange     :milestone, cke12, 100, 100
    Finished              :milestone, fin12, 150, 150
    应用数据就绪          :milestone, app12, 150, 150
    
    section TLS 1.3 (1-RTT)  
    ClientHello + KeyShare :milestone, ch13, 0, 0
    ServerHello + Finished :milestone, fin13, 50, 50
    应用数据就绪           :milestone, app13, 50, 50
    
    section TLS 1.3 (0-RTT)
    ClientHello + 应用数据 :milestone, early, 0, 0
    服务器响应             :milestone, resp, 25, 25
    应用数据就绪           :milestone, app0, 0, 0
```

---

## 密钥派生层次结构对比

```mermaid
graph TD
    subgraph "TLS 1.2 密钥派生"
        PMS12[PreMasterSecret<br/>48字节] --> MS12[MasterSecret<br/>48字节]
        CR12[ClientHello.random] --> MS12
        SR12[ServerHello.random] --> MS12
        MS12 --> KB12[KeyBlock]
        KB12 --> CMK[client_write_MAC_key]
        KB12 --> SMK[server_write_MAC_key]  
        KB12 --> CEK[client_write_encryption_key]
        KB12 --> SEK[server_write_encryption_key]
        KB12 --> CIV[client_write_IV]
        KB12 --> SIV[server_write_IV]
    end
    
    subgraph "TLS 1.3 密钥派生"
        PSK13[PSK<br/>可选] --> ES13[Early Secret]
        DHE13[ECDHE共享密钥] --> HS13[Handshake Secret]
        ES13 --> HS13
        ES13 --> ETS[Early Traffic Secret]
        HS13 --> HTS[Handshake Traffic Secret]
        HS13 --> MS13[Master Secret]
        MS13 --> ATS[Application Traffic Secret]
        MS13 --> RMS[Resumption Master Secret]
        
        HTS --> HTK[握手流量密钥]
        ATS --> ATK[应用流量密钥]
    end
    
    style PMS12 fill:#ffcccc
    style MS12 fill:#ccffcc  
    style ES13 fill:#ccccff
    style HS13 fill:#ffccff
    style MS13 fill:#ffffcc
```

---

## 支持的密码套件对比

```mermaid
graph LR
    subgraph "TLS 1.2 密码套件"
        subgraph "密钥交换"
            RSA12[RSA<br/>❌不推荐]
            DHE12[DHE<br/>✅推荐]  
            ECDHE12[ECDHE<br/>✅推荐]
            PSK12[PSK<br/>✅特殊场景]
        end
        
        subgraph "对称加密"
            AES_CBC[AES-CBC<br/>⚠️存在风险]
            AES_GCM[AES-GCM<br/>✅推荐]
            RC4[RC4<br/>❌已禁用]
            CHACHA20_12[ChaCha20<br/>✅推荐]
        end
        
        subgraph "消息认证"
            SHA1[SHA-1<br/>❌不推荐]
            SHA256[SHA-256<br/>✅推荐]
            SHA384[SHA-384<br/>✅推荐]
        end
    end
    
    subgraph "TLS 1.3 密码套件"
        subgraph "密钥交换 (仅前向保密)"
            DHE13[DHE<br/>✅支持]
            ECDHE13[ECDHE<br/>✅推荐]
            PSK13[PSK<br/>✅支持]
        end
        
        subgraph "AEAD加密 (一体化)"
            AES_GCM_13[AES-GCM<br/>✅推荐]
            AES_CCM[AES-CCM<br/>✅支持] 
            CHACHA20_13[ChaCha20-Poly1305<br/>✅推荐]
        end
        
        subgraph "哈希算法"
            SHA256_13[SHA-256<br/>✅支持]
            SHA384_13[SHA-384<br/>✅支持]
        end
    end
    
    style RSA12 fill:#ffcccc
    style AES_CBC fill:#ffffcc
    style SHA1 fill:#ffcccc
    style RC4 fill:#ffcccc
    style AES_GCM_13 fill:#ccffcc
    style CHACHA20_13 fill:#ccffcc
```

---

## 安全性威胁和防护矩阵

```mermaid
graph TB
    subgraph "常见TLS攻击"
        MITM[中间人攻击<br/>Man-in-the-Middle]
        DOWNGRADE[降级攻击<br/>Protocol Downgrade]
        REPLAY[重放攻击<br/>Replay Attack]
        BEAST[BEAST攻击<br/>Browser Exploit]
        LUCKY13[Lucky13攻击<br/>Padding Oracle]
        CRIME[CRIME攻击<br/>Compression]
        TIMING[时序攻击<br/>Timing Attack]
    end
    
    subgraph "TLS 1.2 防护"
        CERT_VERIFY[证书验证]
        FINISHED_MAC[Finished消息MAC]
        SEQ_NUM[序列号]
        CBC_CONST[常时间CBC]
        NO_COMPRESS_12[禁用压缩]
    end
    
    subgraph "TLS 1.3 增强防护"
        FULL_HANDSHAKE_SIG[整个握手签名]
        NO_RSA[禁用RSA密钥传输]
        ONLY_AEAD[强制AEAD加密]
        NO_RENEGO[禁用重协商]
        NO_COMPRESS_13[禁用压缩]
        PFS_ONLY[强制前向保密]
    end
    
    MITM --> CERT_VERIFY
    MITM --> FULL_HANDSHAKE_SIG
    
    DOWNGRADE --> FINISHED_MAC
    DOWNGRADE --> FULL_HANDSHAKE_SIG
    
    REPLAY --> SEQ_NUM
    
    BEAST --> CBC_CONST
    BEAST --> ONLY_AEAD
    
    LUCKY13 --> CBC_CONST  
    LUCKY13 --> ONLY_AEAD
    
    CRIME --> NO_COMPRESS_12
    CRIME --> NO_COMPRESS_13
    
    TIMING --> PFS_ONLY
    
    style MITM fill:#ffcccc
    style DOWNGRADE fill:#ffcccc
    style REPLAY fill:#ffcccc
    style BEAST fill:#ffcccc
    style LUCKY13 fill:#ffcccc
    style CRIME fill:#ffcccc
    style TIMING fill:#ffcccc
    
    style ONLY_AEAD fill:#ccffcc
    style FULL_HANDSHAKE_SIG fill:#ccffcc
    style PFS_ONLY fill:#ccffcc
```

---

## 图表转换为高分辨率图像说明

### 使用Mermaid CLI生成PNG/PDF

1. **安装Mermaid CLI**:
```bash
npm install -g @mermaid-js/mermaid-cli
```

2. **生成高分辨率PNG** (适合海报打印):
```bash
mmdc -i TLS_HANDSHAKE_FLOWCHARTS.md -o tls_handshake_poster.png -w 3840 -H 2160 --backgroundColor white --theme neutral
```

3. **生成PDF** (矢量格式):
```bash
mmdc -i TLS_HANDSHAKE_FLOWCHARTS.md -o tls_handshake_poster.pdf --format pdf --backgroundColor white --theme neutral
```

4. **批量生成各个图表**:
```bash
# 提取单个图表并生成
mmdc -i tls12_sequence.mmd -o tls12_handshake.png -w 2560 -H 1440
mmdc -i tls13_sequence.mmd -o tls13_handshake.png -w 2560 -H 1440
mmdc -i comparison.mmd -o tls_comparison.png -w 2560 -H 1440
```

### 打印建议

- **A0海报** (841×1189mm): 使用300 DPI，推荐分辨率 9933×14043
- **A1海报** (594×841mm): 使用300 DPI，推荐分辨率 7016×9933  
- **A2海报** (420×594mm): 使用300 DPI，推荐分辨率 4961×7016

### 主题配置

可选择的专业主题：
- `neutral`: 中性配色，适合学术使用
- `dark`: 深色主题，适合演示
- `forest`: 绿色主题
- `base`: 默认主题

这些图表完全符合RFC标准规范，适合计算机网络安全领域的学术研究和工程实践使用。 