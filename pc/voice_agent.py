# -*- coding: utf-8 -*-
"""
MYBIT 语音指令执行器 —— 电脑端
=========================================================
板子按 A 录音 -> 本程序收 -> whisper 识别 -> 意图解析 -> 在电脑上执行 -> OLED 回显

设计：
  1. 先尝试「内置指令」精确匹配（打开程序/网页、音量、截图、锁屏等），零延迟不烧 token
  2. 匹配不到再用 LLM 生成可执行代码，在受限命名空间里 exec
  3. 每一步结果都回传板子显示

用法:
  python voice_agent.py            常驻
  python voice_agent.py --dry      只看不执行（安全预览）
"""
import base64
import json
import os
import subprocess
import sys
import time

import serial

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = json.load(open(os.path.join(HERE, "gateway_config.json"), encoding="utf-8"))

PORT = "COM3"
BAUD = 115200
DRY = "--dry" in sys.argv

AUDIO = {"total": 0, "parts": {}, "got": 0}


def note(msg):
    print("%s %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


# ---------------- 串口 ----------------
def reply(ser, text):
    b = base64.b64encode(text.encode("utf-8")).decode()
    ser.write(("REP|" + b + "\n").encode())
    ser.flush()
    note("-> 板子: " + text[:60])


# ---------------- 识别 ----------------
def recognize(wav_bytes):
    import struct
    pcm = wav_bytes
    rate = 8000
    if wav_bytes[:4] == b"RIFF":
        idx = wav_bytes.find(b"data")
        if idx >= 0:
            pcm = wav_bytes[idx + 8:]
        try:
            rate = struct.unpack("<I", wav_bytes[24:28])[0]
        except Exception:
            rate = 8000
    import local_asr
    return local_asr.transcribe_pcm(pcm, rate)


# ---------------- 内置指令 ----------------
def run_ps(cmd, timeout=15):
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=timeout)
        return (r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip())
    except subprocess.TimeoutExpired:
        return (-1, "", "超时")
    except Exception as e:
        return (-1, "", str(e)[:60])


APPS = {
    "记事本": "notepad.exe",
    "计算器": "calc.exe",
    "画图": "mspaint.exe",
    "资源管理器": "explorer.exe",
    "任务管理器": "taskmgr.exe",
    "命令提示符": "cmd.exe",
    "微信": None,
    "浏览器": None,
}

SITES = {
    "百度": "https://www.baidu.com",
    "必应": "https://www.bing.com",
    "知乎": "https://www.zhihu.com",
    "哔哩哔哩": "https://www.bilibili.com",
    "b站": "https://www.bilibili.com",
    "github": "https://github.com",
}


def try_builtin(text):
    """返回 (是否命中, 结果描述)"""
    t = text.replace(" ", "")

    # 打开程序
    for name, exe in APPS.items():
        if ("打开" + name) in t or ("启动" + name) in t or ("运行" + name) in t:
            if DRY:
                return True, "[预览] 打开 " + name
            if exe:
                try:
                    subprocess.Popen(exe)
                    return True, "已打开" + name
                except Exception as e:
                    return True, "打开失败:" + str(e)[:20]
            else:
                try:
                    os.startfile(name)
                    return True, "已打开" + name
                except Exception:
                    return True, "找不到" + name

    # 打开网站
    for name, url in SITES.items():
        if ("打开" + name) in t or ("访问" + name) in t or ("搜索" + name) in t:
            if DRY:
                return True, "[预览] 打开 " + url
            try:
                os.startfile(url)
                return True, "已打开" + name
            except Exception as e:
                return True, "打开失败"

    # 时间日期（要在"搜索"之前判断，避免"查一下现在几点"被当成搜索）
    if ("几点" in t or "现在时间" in t or "现在几点" in t) and "搜索" not in t:
        now = time.strftime("%H点%M分")
        return True, "现在" + now
    if ("几号" in t or "日期" in t or "今天星期" in t) and "搜索" not in t:
        wd = "一二三四五六日"[time.localtime().tm_wday]
        return True, "%d月%d日 星期%s" % (time.localtime().tm_mon,
                                        time.localtime().tm_mday, wd)

    # 搜索
    for kw in ("搜索", "查一下", "查查"):
        if t.startswith(kw) or ("百度" in t and kw in t):
            q = t.replace(kw, "").replace("百度", "").replace("一下", "")
            if q:
                if DRY:
                    return True, "[预览] 搜索 " + q
                url = "https://www.baidu.com/s?wd=" + q
                try:
                    os.startfile(url)
                    return True, "已搜索:" + q[:10]
                except Exception:
                    return True, "搜索失败"

    # 音量
    if "静音" in t:
        if DRY:
            return True, "[预览] 静音"
        run_ps("(New-Object -ComObject WScript.Shell).SendKeys([char]173)")
        return True, "已静音"
    if "音量最大" in t or "声音最大" in t or "最大声" in t:
        if DRY:
            return True, "[预览] 音量100%"
        run_ps("(New-Object -ComObject WScript.Shell).SendKeys([char]175)" * 20)
        return True, "音量已调高"
    if "音量减小" in t or "小声" in t or "调小" in t:
        if DRY:
            return True, "[预览] 音量降低"
        run_ps("(New-Object -ComObject WScript.Shell).SendKeys([char]174)" * 5)
        return True, "音量已降低"

    # 截图
    if "截图" in t or "截屏" in t:
        if DRY:
            return True, "[预览] 截图"
        out = os.path.join(HERE, "_shots", "shot_%s.png" % time.strftime("%H%M%S"))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        code = (
            "Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
            "$b=New-Object Drawing.Bitmap "
            "[Windows.Forms.SystemInformation]::VirtualScreen.Width,"
            "[Windows.Forms.SystemInformation]::VirtualScreen.Height;"
            "$g=[Drawing.Graphics]::FromImage($b);"
            "$g.CopyFromScreen(0,0,0,0,$b.Size);"
            "$b.Save('%s');" % out)
        rc, so, se = run_ps(code)
        return True, ("已截图" if os.path.exists(out) else "截图失败")

    # 锁屏
    if "锁屏" in t or "锁定" in t:
        if DRY:
            return True, "[预览] 锁屏"
        run_ps("rundll32.exe user32.dll,LockWorkStation")
        return True, "已锁屏"

    # 记事
    if t.startswith("记事") or t.startswith("记一下") or t.startswith("记下"):
        content = t.replace("记事", "").replace("记一下", "").replace("记下", "")
        if content:
            if DRY:
                return True, "[预览] 记事: " + content
            path = os.path.join(HERE, "_notes.txt")
            with open(path, "a", encoding="utf-8") as f:
                f.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), content))
            return True, "已记事"

    return False, None


# ---------------- LLM 生成操作 ----------------
CODEGEN_PROMPT = r"""你是一个 Windows 电脑操作助手。用户会用中文说出一个指令，你要输出可直接执行的 Python 代码。

严格规则：
1. 只输出代码，不要任何解释、不要 markdown 代码块标记
2. 可用模块：os, sys, subprocess, time, json, pathlib, shutil, glob
3. 打开程序用 subprocess.Popen([...]) 或 os.startfile(path)
4. 打开网址用 os.startfile("http://...")
5. 文件操作限定在 D:\数据文件 目录内
6. 执行完把结果字符串赋给变量 result
7. 不要用 input()，不要用无限循环，不要删除系统文件
8. 代码长度不超过 15 行

示例输入：把桌面壁纸换一下
示例输出：
import subprocess
subprocess.Popen(["rundll32.exe","user32.dll,UpdatePerUserSystemParameters"])
result = "壁纸已刷新"
"""


def llm_codegen(text):
    import requests
    url = CONFIG["llm_base"].rstrip("/") + "/chat/completions"
    payload = {
        "model": CONFIG["llm_model"],
        "messages": [
            {"role": "system", "content": CODEGEN_PROMPT},
            {"role": "user", "content": text},
        ],
        "stream": False,
        "max_tokens": 500,
    }
    try:
        r = requests.post(url,
                          headers={"Authorization": "Bearer " + CONFIG["llm_key"],
                                   "Content-Type": "application/json"},
                          json=payload, timeout=60)
        if r.status_code != 200:
            return None, "AI %d" % r.status_code
        code = r.json()["choices"][0]["message"]["content"].strip()
        code = code.replace("```python", "").replace("```", "").strip()
        return code, None
    except Exception as e:
        return None, str(e)[:40]


def execute_code(code):
    """在受限命名空间执行"""
    import glob
    import shutil
    ns = {
        "os": os, "sys": sys, "subprocess": subprocess, "time": time,
        "json": json, "shutil": shutil, "glob": glob,
        "result": None,
        "__builtins__": {
            "__import__": __import__, "print": print, "len": len, "str": str,
            "int": int, "float": float, "list": list, "dict": dict,
            "range": range, "open": open, "enumerate": enumerate,
            "Exception": Exception, "True": True, "False": False, "None": None,
        },
    }
    from pathlib import Path
    ns["pathlib"] = __import__("pathlib")
    ns["Path"] = Path
    try:
        exec(code, ns)
        return str(ns.get("result") or "已执行")
    except Exception as e:
        return "执行出错:" + str(e)[:40]


# ---------------- 主流程 ----------------
def handle(ser, wav):
    t0 = time.time()
    text, err = recognize(wav)
    if err:
        reply(ser, "识别失败")
        note("识别失败: " + err)
        return
    if not text:
        reply(ser, "没听清")
        note("识别为空")
        return
    note("[%.1fs] 识别: %s" % (time.time() - t0, text))
    reply(ser, "听到:" + text[:14])

    # 1. 内置指令
    hit, res = try_builtin(text)
    if hit:
        note("[内置] " + res)
        reply(ser, res)
        return

    # 2. LLM 生成代码
    note("未匹配内置指令，让 AI 生成操作...")
    code, cerr = llm_codegen(text)
    if cerr:
        note("生成失败: " + cerr)
        reply(ser, "无法处理")
        return
    note("生成代码:\n" + code)
    if DRY:
        reply(ser, "[预览]已生成")
        return
    res = execute_code(code)
    note("执行结果: " + res)
    reply(ser, res[:60])


def main():
    note("=" * 56)
    note(" MYBIT 语音指令执行器" + ("  [预览模式]" if DRY else ""))
    note("   %s @ %d" % (PORT, BAUD))
    note("=" * 56)

    note("预加载 whisper...")
    import local_asr
    ok, err = local_asr.warmup()
    note("  %s" % ("就绪" if ok else "失败 " + str(err)))

    ser = serial.Serial(PORT, BAUD, timeout=0.2)
    time.sleep(0.3)
    ser.reset_input_buffer()
    note("等待板子指令...")

    while True:
        line = ser.readline()
        if not line:
            continue
        s = line.decode("utf-8", "ignore").strip()
        if not s:
            continue

        if s.startswith("MSG|S|"):
            AUDIO["total"] = int(s[6:]) if s[6:].isdigit() else 0
            AUDIO["parts"] = {}
            AUDIO["got"] = 0
            note("接收 %d 块" % AUDIO["total"])
            continue

        if s.startswith("MSG|D|"):
            body = s[6:]
            idx, _, payload = body.partition("|")
            try:
                AUDIO["parts"][int(idx)] = base64.b64decode(payload + "=" * (-len(payload) % 4))
                AUDIO["got"] += 1
            except Exception:
                pass
            continue

        if s == "MSG|E":
            buf = b""
            ok = True
            for i in range(AUDIO["total"]):
                p = AUDIO["parts"].get(i)
                if p is None:
                    ok = False
                    break
                buf += p
            if not ok or not buf:
                reply(ser, "数据不完整")
                continue
            note("收到语音 %d 字节" % len(buf))
            try:
                handle(ser, buf)
            except Exception as e:
                note("处理异常: %s" % str(e)[:80])
                reply(ser, "处理出错")
            continue

        if len(s) < 100:
            note("板子: " + s)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        note("退出")
