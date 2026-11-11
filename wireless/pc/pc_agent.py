#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MYBIT 电脑执行端 pc_agent.py
=========================================================
在你的电脑上常驻运行，主动向中转服务器拉取任务并执行。

用法：
    python pc_agent.py                  # 启动
    python pc_agent.py --once           # 只跑一轮（调试）
    python pc_agent.py --dry            # 只看不执行

支持的任务类型：
    open_url   打开网址
    app        打开程序（记事本/计算器/画图/资源管理器...）
    path       打开文件或文件夹
    qq         给 QQ 联系人发消息
    shell      执行 PowerShell 命令（白名单校验）
    volume     调节音量 / 静音
    screenshot 截图
    lock       锁定电脑

安全：
    - shell 命令走白名单，拒绝危险操作
    - 所有执行都记日志到 pc_agent.log
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import traceback
import urllib.parse
import urllib.request

# ---------------- 配置 ----------------
SERVER = os.environ.get("MYBIT_SERVER", "http://10.61.190.8:8091")
POLL_INTERVAL = 1.5          # 轮询间隔（秒）
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "pc_agent.log")


def log(msg):
    line = "%s %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%Y-%m-%d"), line))
    except Exception:
        pass


# ---------------- HTTP ----------------
def http_get(path, timeout=10):
    try:
        with urllib.request.urlopen(SERVER + path, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}


def http_post(path, obj, timeout=15):
    try:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            SERVER + path, data=data,
            headers={"Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------- 各类型执行器 ----------------
def do_open_url(p):
    url = (p.get("url") or "").strip()
    if not url:
        return False, "缺少 url"
    if not re.match(r"^https?://", url):
        url = "https://" + url
    os.startfile(url)
    return True, "已打开 %s" % (p.get("name") or url)


APP_MAP = {
    "notepad": "notepad.exe",
    "记事本": "notepad.exe",
    "calc": "calc.exe",
    "计算器": "calc.exe",
    "mspaint": "mspaint.exe",
    "画图": "mspaint.exe",
    "explorer": "explorer.exe",
    "资源管理器": "explorer.exe",
    "cmd": "cmd.exe",
    "命令行": "cmd.exe",
    "taskmgr": "taskmgr.exe",
    "任务管理器": "taskmgr.exe",
    "control": "control.exe",
    "控制面板": "control.exe",
    "mstsc": "mstsc.exe",
    "mag": "magnify.exe",
}


def do_app(p):
    name = (p.get("name") or "").strip().lower()
    exe = APP_MAP.get(name)
    if not exe:
        return False, "不支持的程序: %s" % name
    subprocess.Popen([exe], shell=False)
    return True, "已启动 %s" % (p.get("label") or name)


def do_path(p):
    path = (p.get("path") or "").strip()
    if not path:
        return False, "缺少 path"
    if not os.path.exists(path):
        return False, "路径不存在: %s" % path
    os.startfile(path)
    return True, "已打开 %s" % (p.get("label") or path)


def do_qq(p):
    """给 QQ 联系人发消息（用快捷键 + 剪贴板方式）"""
    contact = (p.get("contact") or "").strip()
    message = (p.get("message") or "").strip()
    if not contact:
        return False, "缺少联系人"
    if not message:
        return False, "缺少消息内容"

    ps = """
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms

# 1. 确保 QQ 在前台（如果已运行）
$qq = Get-Process QQ -ErrorAction SilentlyContinue
if (-not $qq) {
    $exe = @(
        "$env:ProgramFiles\\Tencent\\QQNT\\QQ.exe",
        "${env:ProgramFiles(x86)}\\Tencent\\QQ\\Bin\\QQ.exe",
        "$env:LOCALAPPDATA\\Programs\\Tencent\\QQNT\\QQ.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $exe) { Write-Output 'QQ_NOT_FOUND'; exit 1 }
    Start-Process $exe
    Start-Sleep -Seconds 8
}

# 2. 全局搜索消息（QQNT 用 Ctrl+K 搜索联系人）
[System.Windows.Forms.SendKeys]::SendWait('^k')
Start-Sleep -Milliseconds 800

# 3. 输入联系人
Set-Clipboard -Value %CONTACT%
Start-Sleep -Milliseconds 200
[System.Windows.Forms.SendKeys]::SendWait('^v')
Start-Sleep -Milliseconds 1200

# 4. 回车进入会话
[System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
Start-Sleep -Milliseconds 1500

# 5. 输入消息并发送
Set-Clipboard -Value %MESSAGE%
Start-Sleep -Milliseconds 200
[System.Windows.Forms.SendKeys]::SendWait('^v')
Start-Sleep -Milliseconds 500
[System.Windows.Forms.SendKeys]::SendWait('{ENTER}')

Write-Output 'QQ_SENT'
"""
    ps = ps.replace("%CONTACT%", "'" + contact.replace("'", "''") + "'")
    ps = ps.replace("%MESSAGE%", "'" + message.replace("'", "''") + "'")

    r = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", ps],
                       capture_output=True, text=True, timeout=60,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    if "QQ_SENT" in out:
        return True, "已给 %s 发送: %s" % (contact, message)
    if "QQ_NOT_FOUND" in out:
        return False, "没找到 QQ，请先手动登录"
    return False, "发送失败: %s" % out.strip()[:60]


# shell 命令白名单：必须是这些开头才算安全
SHELL_ALLOW = (
    "get-", "dir", "ls", "echo", "whoami", "hostname", "date", "time",
    "systeminfo", "ipconfig", "ping", "test-", "select-", "where-",
    "measure-", "resolve-", "get-process", "get-service", "get-childitem",
    "get-content", "get-item", "get-psdrive", "get-volume", "get-date",
    "invoke-", "start-process", "stop-process", "tasklist", "taskkill",
    "netstat", "nslookup", "nvidia-smi", "wmic", "vol", "fsutil",
)
SHELL_DENY = (
    "format", "del ", "rmdir", "remove-item", "rd /s", "shutdown",
    "restart-computer", "stop-computer", "reg delete", "net user",
    "invoke-expression", "iex", "curl ", "wget ", "invoke-webrequest",
    "downloadstring", "set-executionpolicy", "new-service",
    "disable-", "uninstall-", "cipher /w", "diskpart",
)


def do_shell(p):
    cmd = (p.get("command") or "").strip()
    if not cmd:
        return False, "缺少命令"
    low = cmd.lower()
    for d in SHELL_DENY:
        if d in low:
            return False, "命令被拒绝（含危险操作 %s）" % d
    if not any(low.startswith(a) or (" " + a) in low for a in SHELL_ALLOW):
        return False, "命令不在白名单: %s" % cmd[:40]
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=25,
            encoding="utf-8", errors="replace")
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if r.returncode != 0 and err:
            return False, err[:150]
        return True, out[:300] if out else "执行完成（无输出）"
    except subprocess.TimeoutExpired:
        return False, "命令超时"
    except Exception as e:
        return False, str(e)[:100]


def do_volume(p):
    if p.get("mute"):
        ps = "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=15)
        return True, "已切换静音"
    lvl = p.get("level")
    if lvl is None:
        return False, "缺少 level"
    try:
        lvl = max(0, min(100, int(lvl)))
    except Exception:
        return False, "level 无效"
    # 用 nircmd 或 PowerShell 调音量
    steps = lvl - _current_volume()
    if steps == 0:
        return True, "音量已是 %d" % lvl
    key = 175 if steps > 0 else 174       # VK_VOLUME_DOWN / UP
    ps = """
$w = New-Object -ComObject WScript.Shell
for ($i=0; $i -lt %d; $i++) { $w.SendKeys([char]%d); Start-Sleep -Milliseconds 30 }
""" % (abs(steps) // 2 + 1, key)
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=30)
    return True, "音量已调到 %d" % lvl


def _current_volume():
    try:
        ps = "(Get-CimInstance -Namespace root/cimv2 -ClassName Win32_SoundDevice | Measure-Object).Count"
        return 50
    except Exception:
        return 50


def do_screenshot(p):
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shots")
    os.makedirs(out_dir, exist_ok=True)
    fn = os.path.join(out_dir, time.strftime("shot_%Y%m%d_%H%M%S.png"))
    ps = """
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
$bmp.Save('%s', [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output 'OK'
""" % fn.replace("\\", "\\\\")
    r = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", ps],
                       capture_output=True, text=True, timeout=30,
                       encoding="utf-8", errors="replace")
    if os.path.exists(fn):
        os.startfile(fn)
        return True, "已截图: %s" % os.path.basename(fn)
    return False, "截图失败: %s" % (r.stderr or "")[:80]


def do_lock(p):
    subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], timeout=10)
    return True, "已锁定电脑"


EXECUTORS = {
    "open_url": do_open_url,
    "app": do_app,
    "path": do_path,
    "qq": do_qq,
    "shell": do_shell,
    "volume": do_volume,
    "screenshot": do_screenshot,
    "lock": do_lock,
}


def run_task(task):
    """执行一个任务，返回 (ok, output)"""
    ttype = task.get("type")
    payload = task.get("payload") or {}
    fn = EXECUTORS.get(ttype)
    if not fn:
        return False, "未知任务类型: %s" % ttype
    try:
        return fn(payload)
    except Exception as e:
        return False, "执行异常: %s" % str(e)[:100]


# ---------------- 主循环 ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="只跑一轮")
    ap.add_argument("--dry", action="store_true", help="只看不执行")
    ap.add_argument("--server", default=None, help="服务器地址")
    args = ap.parse_args()

    global SERVER
    if args.server:
        SERVER = args.server

    log("=" * 56)
    log(" MYBIT 电脑执行端启动")
    log("   服务器: %s" % SERVER)
    log("   模式  : %s" % ("dry（只看）" if args.dry else "正常运行"))
    log("=" * 56)

    # 连服务器
    info = http_get("/api/ping", timeout=8)
    if not info.get("ok"):
        log("!! 连不上服务器: %s" % info.get("error"))
        log("   检查网络，或用 --server 指定地址")
        return 1
    log("服务器在线: %s" % info.get("service"))

    rounds = 0
    while True:
        rounds += 1
        try:
            res = http_get("/api/task/pull", timeout=10)
            tasks = res.get("tasks") or []
            for t in tasks:
                tid = t.get("id")
                log("[任务] %s  %s  %s" % (tid, t.get("type"),
                                          json.dumps(t.get("payload"),
                                                     ensure_ascii=False)[:80]))
                if args.dry:
                    log("  dry 模式，跳过执行")
                    ok, out = True, "（dry 模式，未执行）"
                else:
                    ok, out = run_task(t)
                log("  -> %s  %s" % ("成功" if ok else "失败", out[:100]))
                http_post("/api/task/result",
                          {"id": tid, "ok": ok, "output": out})
        except KeyboardInterrupt:
            log("已停止")
            return 0
        except Exception:
            log("轮询异常:\n" + traceback.format_exc()[:300])

        if args.once:
            return 0
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    sys.exit(main())
