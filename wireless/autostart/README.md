# 开机自启配置

让整套系统无人值守：服务器重启后中转服务自动运行，电脑重启后执行端自动上线。

---

## 服务器端（systemd）

### 安装

```bash
# 1. 复制服务文件
mkdir -p ~/.config/systemd/user
cp mybit-relay.service ~/.config/systemd/user/

# 2. 重新加载
systemctl --user daemon-reload

# 3. 启用开机自启
systemctl --user enable mybit-relay.service

# 4. 立即启动
systemctl --user start mybit-relay.service

# 5. 允许用户未登录也运行（关键）
loginctl enable-linger $USER
```

### 服务文件内容

```ini
[Unit]
Description=MYBIT Relay Server (whisper + LLM + task queue)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=%h/mybit-relay
Environment="PATH=%h/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="HF_ENDPOINT=https://hf-mirror.com"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/usr/bin/python3 %h/mybit-relay/relay_server.py
Restart=always
RestartSec=5
StandardOutput=append:%h/mybit-relay/relay.log
StandardError=append:%h/mybit-relay/relay.log

[Install]
WantedBy=default.target
```

### 常用命令

```bash
systemctl --user status mybit-relay     # 看状态
systemctl --user restart mybit-relay    # 重启
systemctl --user stop mybit-relay       # 停止
systemctl --user disable mybit-relay    # 取消自启
journalctl --user -u mybit-relay -f     # 看实时日志
```

### 验证

```bash
systemctl --user is-active mybit-relay    # active
systemctl --user is-enabled mybit-relay   # enabled
loginctl show-user $USER | grep Linger    # Linger=yes
curl http://127.0.0.1:8091/api/ping
```

---

## 电脑端（Windows 启动文件夹）

### 安装

右键 `安装开机自启.ps1` → **使用 PowerShell 运行**

脚本会：
1. 检查 `start_agent.bat` 和 python
2. 在启动文件夹创建快捷方式
3. 立即启动一次
4. 验证是否运行

### 手动安装

1. `Win + R` 输入 `shell:startup` 回车
2. 把 `start_agent.bat` 的快捷方式拖进去
3. 快捷方式属性里把「运行方式」设为**最小化**

### 批处理内容

```bat
@echo off
chcp 936 >nul
title MYBIT PC Agent
cd /d "<PROJECT_DIR>"          ← 改成你的实际路径
set PYTHONIOENCODING=utf-8

:loop
echo [%date% %time%] start pc_agent
python pc_agent.py
echo [%date% %time%] exited, restart in 5s
timeout /t 5 /nobreak >nul
goto loop
```

**使用前必须改** `cd /d "<PROJECT_DIR>"` 这一行，换成 `pc_agent.py` 所在的真实目录。

**特点**：`pc_agent.py` 崩溃后 5 秒自动重启，无限循环。

### 验证

```powershell
# 看进程
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'pc_agent' }

# 看日志
Get-Content pc_agent.log -Tail 20
```

---

## 两个坑

### 坑 1：bat 文件必须用 CRLF 换行

用编辑器写 bat 时如果存成 LF（Unix 换行），cmd 会把整行拆碎：

```
'o' 不是内部或外部命令
'EVEL' 不是内部或外部命令
'timeRC)?' 不是内部或外部命令
```

原因是 `cd /d "..."` 里的 `/d` 被拆成孤立字符。

**解决**：用 CRLF 保存。PowerShell 写入时：

```powershell
$lines = @('@echo off', 'cd /d "..."', ...)
$content = ($lines -join "`r`n") + "`r`n"
[IO.File]::WriteAllText($path, $content, [Text.Encoding]::GetEncoding(936))
```

### 坑 2：bat 内容尽量用纯 ASCII

中文在 GBK/UTF-8 转换时容易乱码，导致 `echo` 输出成问号。

**解决**：命令部分全英文，注释可以不加。

### 坑 3：`loginctl enable-linger` 可能需要 sudo

如果提示权限不足：

```bash
sudo loginctl enable-linger $USER
```

不加 `linger` 的话，用 SSH 退出登录后服务会被杀掉。

---

## 验证整套自愈

| 测试 | 预期 |
|---|---|
| 服务器重启 | 中转服务自动起来 |
| 电脑重启 | pc_agent 自动起来 |
| 杀掉 relay_server | systemd 5 秒后重启 |
| 杀掉 python pc_agent | 批处理 5 秒后重启 |
| 板子断电重上电 | 自动连 WiFi + Dr.COM 认证 |

**现在整套系统是自愈的，不需要人工干预。**
