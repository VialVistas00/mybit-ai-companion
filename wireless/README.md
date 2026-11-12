# 无线版：板子语音遥控电脑

**一句话**：对着板子说话，电脑（或服务器）按你说的做。

```
┌──────────┐  语音    ┌──────────────────┐  HTTPS  ┌──────────┐
│ MYBIT 板子│ ───────▶ │ 10.61.190.8:8091 │ ──────▶ │ DeepSeek │
│  HZCU    │          │                  │         └──────────┘
└──────────┘          │ ① whisper 识别    │
                      │ ② 意图解析        │
                      │ ③ 生成任务        │
                      └────────┬─────────┘
                               │ 任务队列
                               ▼
                      ┌──────────────────┐
                      │ 你的电脑          │
                      │ pc_agent.py      │
                      │ 主动拉取，不开端口 │
                      └──────────────────┘
```

板子完全独立：插充电宝就能用，不需要连电脑。

---

## 组成部分

| 目录 | 文件 | 跑在哪 | 作用 |
|---|---|---|---|
| `board/` | `hzcu.py` | 板子 | 校园网自动认证（Dr.COM） |
| `board/` | `relay.py` | 板子 | 访问中转服务（HTTP 客户端） |
| `board/` | `ai_voice.py` | 板子 | 主程序：录音→上传→显示 |
| `server/` | `relay_server.py` | 服务器 | 语音识别 + LLM + 任务分发 |
| `server/` | `taskqueue.py` | 服务器 | 任务队列 |
| `pc/` | `pc_agent.py` | 你的电脑 | 执行命令（开程序、发QQ、跑命令） |
| `autostart/` | | | 开机自启配置（见 [autostart/README.md](autostart/README.md)） |

---

## 部署

### 1. 服务器

```bash
# 依赖（无 venv 时用 --user）
pip install --user flask requests faster-whisper -i https://mirrors.zju.edu.cn/pypi/web/simple

# 模型（huggingface 国内不通，用镜像）
export HF_ENDPOINT=https://hf-mirror.com
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('Systran/faster-whisper-small',
                  local_dir='/home/USER/models/faster-whisper-small')
"

# 配置
cat > ~/mybit-relay/relay_config.json <<'EOF'
{
  "port": 8091,
  "llm_base": "https://api.deepseek.com/v1",
  "llm_key": "sk-你的key",
  "llm_model": "deepseek-chat",
  "asr_model_dir": "/home/USER/models/faster-whisper-small",
  "audio_dir": "/tmp/mybit_audio"
}
EOF

# 启动
cd ~/mybit-relay && nohup python3 relay_server.py > relay.log 2>&1 &
```

### 2. 板子

```python
# 传到板子（用 pc/mybit.py 或 mpremote）
hzcu.py      -> hzcu.py
relay.py     -> relay.py
ai_voice.py  -> main.py
```

板子开机自动：连 HZCU → Dr.COM 认证 → 检查中转服务 → 待命。

### 3. 电脑

```powershell
python pc_agent.py
```

窗口留着别关。每 1.5 秒拉一次任务。

### 4. 开机自启（可选，推荐）

配好后整套系统无人值守，断电重来也能自动恢复。

**服务器**：

```bash
cp autostart/mybit-relay.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now mybit-relay.service
loginctl enable-linger $USER          # 未登录也运行
```

**电脑**：右键 `autostart/安装开机自启.ps1` → 使用 PowerShell 运行

详见 [autostart/README.md](autostart/README.md)

---

## 使用

按板子的 **A 键**，说话。

| 你说 | 电脑做什么 |
|---|---|
| 打开百度 | 浏览器打开 baidu.com |
| 打开记事本 | 启动 notepad |
| 打开计算器 | 启动 calc |
| 给张三发消息说明天见 | QQ 发消息 |
| 看看D盘还剩多少空间 | 返回磁盘信息 |
| 把音量调到30 | 调音量 |
| 截个图 | 截图并打开 |
| 锁屏 | 锁定 Windows |
| **其他任何话** | **文字发进 DSH 对话窗口** |

按 **B 键**：清屏 / 重连。

## 语音识别容错

实测中「打开电脑上的浏览器」常被识别成「牛奶器」「牛腩刺」等。三层次容错：

**1. 本地同音字纠错**（喂给 LLM 前先过）

```python
ASR_FIXES = [
    ("牛奶器", "浏览器"), ("浏懒器", "浏览器"), ("流览器", "浏览器"),
    ("记是本", "记事本"), ("鸡算器", "计算器"), ("阴凉", "音量"),
    ("截过图", "截图"), ("发小心", "发消息"), ("文件家", "文件夹"),
]
```

**2. LLM 按语义理解**（prompt 里明确列出常见错字）

**3. 模糊匹配兜底**（LLM 挂了也能用）

另外加了**繁体转简体**：whisper 有时输出「開電腦上的瀏覽器」，转成「开电脑上的浏览器」。

## 录音信号强度（重要）

板子麦克风信号很弱，实测：

| 场景 | 原始 rms | 识别结果 |
|---|---|---|
| 板子离人远（>1m） | 137 | 「字幕by索兰娅」（幻觉）|
| **凑近说话**（<20cm）| **3332** | **正确识别** |

**rms 超过 1000 识别才稳定。** 服务器端做了自适应增益（放大 1~30 倍 + 软限幅），但源头信号太弱时仍无能为力。

**用法建议**：凑近板子（10~20cm）正常音量说话，2 秒内说完一句。

## 向 DSH 发消息

说的话不是任何具体操作时，自动走 `dsh` 类型：文字被粘贴进 DeepSeek Harness 对话窗口并发送。

```python
# pc_agent.py 的 do_dsh 实现
# 1. 找 DSH 窗口（MainWindowTitle 匹配 Harness）
# 2. ShowWindow + SetForegroundWindow
# 3. 剪贴板粘贴（SendKeys 对中文支持差，必须用剪贴板）
# 4. Enter 发送
```

**注意**：会抢焦点。如果当时正在别处打字，文字可能粘到错误位置。

---

## 校园网认证（关键）

**必须连 SSID `HZCU`，不能是 `HZCU-IPV6`。**

| | `HZCU-IPV6` | `HZCU` |
|---|---|---|
| IP 段 | 10.60.x | 10.67.x |
| 认证系统 | SRun（深澜） | **Dr.COM（城市热点）** |
| 认证服务器 | 10.69.255.190 | **10.69.255.130** |
| 协议复杂度 | HMAC-MD5 + xxtea + SHA1 | **纯明文 GET** |
| 脚本能否认证 | ❌ 被拦 | ✅ **可以** |

`HZCU-IPV6` 下所有 HTTP 请求（包括发给认证服务器本身的）都会被劫持到 Portal 页面，板子过不去。

`HZCU` 则直接放行到 `10.69.255.130`，登录就是一行：

```
http://10.69.255.130/drcom/login?DDDDD=账号&upass=密码&0MKKey=123456&...
```

---

## 踩过的坑

### 1. 录音 3 秒必 MemoryError

```
3 秒 → 49196 字节，需要 49KB 连续块 → MemoryError
2 秒 → 32812 字节，只要 32KB      → 稳定成功
```

板子堆总量 111KB，import 后可用约 75KB，再被 socket/显示缓冲分割，3 秒就拿不到连续块了。

**解决**：默认 2 秒，失败自动降级到 1 秒。

### 2. `f.read(512)` 返回值不定

实测 49196 字节的文件只发出 44 字节就 EOF，但 `Content-Length` 声明的是完整大小 → 服务器死等剩余数据，板子死等响应 → **表现为「上传卡在 70%」**。

**解决**：用 `os.stat()` 拿准确大小，边读边发，绝不整块读入内存。

### 3. socket 块大小敏感

```
s.send(1024) → 直接 OSError
s.send(512)  → 327 KB/s
s.send(256)  → 425 KB/s
s.send(128)  → 弱网下最稳
```

**解决**：固定 128 字节，带 60 次单块重试 + 3 轮整次重传。

### 4. whisper 把提示词当答案

用了 `initial_prompt` 后，录到静音时 whisper 会把提示词原样吐出来（「请使用简体中文转写」）。

**解决**：去掉 `initial_prompt`，加 `no_speech_threshold` 过滤 + hallucination 词表。

### 5. 弱 Wi-Fi 上传中断

```
RSSI -78 dBm 已在临界值
拿远一点 → -85 以下 → 上传到 19% 断
```

**解决**：块降到 128、重试加重、OLED 显示信号等级。

### 6. socket 读响应提前退出

原来的 `_read_resp` 在数据未到达时就退出循环，拿到空响应（363ms 返回「没听清」，实际服务器要 2 秒）。

**解决**：区分「暂时没数据」和「连接关闭」，按 `Content-Length` 精确截取。

### 7. raw REPL 比普通 REPL 更耗内存

同样的 free 值，raw REPL 执行脚本时录音失败，普通 REPL 成功。

**解决**：调试时用普通 REPL 逐行发送，别用 raw。

---

## 接口

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/ping` | GET | 心跳 |
| `/api/ask` | POST | 上传 WAV → 识别 → 意图解析 → 回答 |
| `/api/ask_text` | POST | 文本提问 |
| `/api/reply` | GET | 取回答队列 |
| `/api/task/pull` | GET | 电脑拉任务 |
| `/api/task/result` | POST | 电脑回报结果 |
| `/api/task/done` | GET | 板子取执行结果 |
| `/api/conversations` | GET | 对话历史 |
| `/` | GET | 网页监控面板 |

---

## 安全

`pc_agent.py` 的 `shell` 类型有白名单：

**允许**：`Get-*`、`dir`、`ping`、`ipconfig`、`tasklist`、`nvidia-smi` 等查询类

**拒绝**：`format`、`del`、`shutdown`、`Remove-Item`、`Invoke-Expression`、`Invoke-WebRequest`、`net user`、`reg delete`、`diskpart` 等

所有执行都记录到 `pc_agent.log`。
