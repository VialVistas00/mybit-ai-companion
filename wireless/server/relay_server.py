#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MYBIT 中转服务 —— 部署在 10.61.190.8
=========================================================
功能：
  1. 接收板子上传的录音（WAV/裸PCM）
  2. 本地 faster-whisper 识别（或转调）
  3. 调 DeepSeek 生成回答
  4. 把回答存起来，等板子来取

板子侧只需两条 HTTP 请求：
  上传语音：POST /api/ask    body=wav 二进制
  取回答：  GET  /api/reply?since=N

端口 8091（避开已有的 80/3001/8080/8090）
"""
import io
import json
import os
import struct
import threading
import time
import uuid
import wave

from flask import Flask, jsonify, request, Response

try:
    import taskqueue as TQ
except ImportError:
    TQ = None

# ---------------- 配置 ----------------
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "relay_config.json")
CONVLOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "conversations.jsonl")

DEFAULT_CONFIG = {
    "port": 8091,
    "llm_base": "https://api.deepseek.com/v1",
    "llm_key": "",
    "llm_model": "deepseek-chat",
    "system_prompt": "你是小特，一块信息科技实验板上的AI学伴。用口语化中文回答，"
                     "不用表情符号和特殊字符，回答控制在80字以内。",
    "asr_model": "large-v3-turbo",
    "asr_model_dir": "",
    "audio_dir": "/tmp/mybit_audio",
}

app = Flask(__name__)
CFG = {}
REPLIES = []
REPLY_SEQ = [0]
LOCK = threading.Lock()
LOG = []
_ASR = None


def note(msg):
    line = "%s %s" % (time.strftime("%H:%M:%S"), msg)
    LOG.append(line)
    del LOG[:-300]
    print(line, flush=True)


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            note("配置读取失败: %s" % e)
    cfg["llm_key"] = cfg.get("llm_key") or os.environ.get("DEEPSEEK_API_KEY", "")
    return cfg


# ---------------- 语音识别 ----------------
def get_asr():
    global _ASR
    if _ASR is not None:
        return _ASR
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("未安装 faster-whisper，请 pip install faster-whisper")
    model = CFG.get("asr_model") or "large-v3-turbo"
    mdir = CFG.get("asr_model_dir") or ""
    device = "cuda" if _cuda_ok() else "cpu"
    ctype = "float16" if device == "cuda" else "int8"
    note("加载 whisper: %s device=%s" % (model, device))
    if mdir and os.path.isdir(mdir):
        _ASR = WhisperModel(mdir, device=device, compute_type=ctype)
    else:
        _ASR = WhisperModel(model, device=device, compute_type=ctype)
    note("whisper 就绪")
    return _ASR


def _cuda_ok():
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def wav_to_pcm(raw):
    """从 WAV 里剥出 PCM，并返回 (pcm, rate)"""
    if raw[:4] != b"RIFF":
        return raw, 16000
    rate = 16000
    try:
        rate = struct.unpack("<I", raw[24:28])[0]
    except Exception:
        pass
    idx = raw.find(b"data")
    pcm = raw[idx + 8:] if idx >= 0 else raw
    return pcm, rate


def remove_dc_and_gain(pcm, sampwidth=2):
    """去直流 + 裁启动尖峰 + 稳健归一化（MYBIT 录音有 -8500 偏置）"""
    n = len(pcm) // 2
    if n < 400:
        return pcm
    s = struct.unpack("<%dh" % n, pcm[:n * 2])
    mean = sum(s) // n
    c = [v - mean for v in s]
    for i in range(min(120, n)):
        c[i] = 0
    mags = sorted(abs(v) for v in c)
    p95 = mags[int(len(mags) * 0.95)] if mags else 0
    peak = p95 if p95 > 200 else (mags[-1] if mags else 0)
    if peak < 100:
        return pcm
    scale = 0.6 * 32767.0 / peak
    out = bytearray()
    for v in c:
        x = int(v * scale)
        if x > 32767:
            x = 32767
        elif x < -32768:
            x = -32768
        out += struct.pack("<h", x)
    return bytes(out)


def resample_to_16k(pcm, rate):
    if rate == 16000:
        return pcm
    n = len(pcm) // 2
    if n < 2:
        return pcm
    s = struct.unpack("<%dh" % n, pcm[:n * 2])
    ratio = 16000.0 / rate
    out_n = int(n * ratio)
    out = bytearray()
    for i in range(out_n):
        pos = i / ratio
        i0 = int(pos)
        if i0 >= n - 1:
            v = s[-1]
        else:
            frac = pos - i0
            v = int(s[i0] * (1 - frac) + s[i0 + 1] * frac)
        out += struct.pack("<h", v)
    return bytes(out)


def recognize(raw):
    pcm, rate = wav_to_pcm(raw)
    if rate != 16000:
        pcm = resample_to_16k(pcm, rate)

    # ★ 关键：先做静音检测。板子麦克风信号幅度小，
    #   用均方根判断有没有真实语音，静音就直接返回，省掉 whisper 的 2 秒。
    rms = pcm_rms(pcm)
    if rms < 60:
        note("静音 (rms=%.1f)，跳过识别" % rms)
        return "", None

    pcm = remove_dc_and_gain(pcm)

    d = CFG.get("audio_dir") or "/tmp/mybit_audio"
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, "ask_%s.wav" % uuid.uuid4().hex[:8])
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm)

    try:
        model = get_asr()
        segs, info = model.transcribe(
            tmp, language="zh", task="transcribe", beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300,
                            "speech_pad_ms": 100,
                            "threshold": 0.5},
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4)
        # ★ 注意：不要用 initial_prompt —— 实测 whisper 会把提示词本身
        #   当成识别结果输出（录到静音时会把 prompt 原样吐出来）。
        parts = []
        for s in segs:
            t = (s.text or "").strip()
            if not t:
                continue
            if getattr(s, "no_speech_prob", 0) > 0.6:
                continue
            parts.append(t)
        text = "".join(parts).strip()

        # 过滤已知的 hallucination 产物
        bad = ("请使用简体中文转写", "请使用简体中文", "字幕由", "感谢观看",
               "谢谢观看", "订阅", "Amara", "字幕")
        for b in bad:
            if text.startswith(b):
                text = text.replace(b, "").strip()
        if text in bad:
            text = ""

        return text, None
    except Exception as e:
        return None, "识别失败: %s" % str(e)[:80]
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass


def pcm_rms(pcm):
    """
    计算 PCM 的真实信号强度（去掉直流偏置后的标准差）。
    MYBIT 录音有约 -8500 的直流偏置，直接算 RMS 会被偏置淹没。
    """
    n = len(pcm) // 2
    if n < 100:
        return 0.0
    step = max(1, n // 3000)
    vals = []
    for i in range(0, n, step):
        vals.append(struct.unpack("<h", pcm[i * 2:i * 2 + 2])[0])
    if len(vals) < 10:
        return 0.0
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    return var ** 0.5


# ---------------- 电脑操作指令 ----------------
# LLM 用它判断用户是否想让电脑做事，并给出结构化指令
AGENT_PROMPT = """你是一个电脑操作指令解析器。判断用户的话是否想操作电脑。

规则：
- 想操作电脑 -> 只输出一行 JSON，不要任何解释和markdown
- 不想操作电脑 -> 只输出：NONE

支持的指令类型：
1. 打开网址/网站/浏览器
   {"type":"open_url","url":"https://...","name":"网站名"}
   例：打开百度 -> {"type":"open_url","url":"https://www.baidu.com","name":"百度"}
   例：打开浏览器 -> {"type":"open_url","url":"https://www.bing.com","name":"浏览器"}
   例：搜索杭州天气 -> {"type":"open_url","url":"https://www.bing.com/search?q=杭州天气","name":"搜索"}

2. 打开电脑程序
   {"type":"app","name":"notepad","label":"记事本"}
   可用程序：notepad(记事本) calc(计算器) mspaint(画图) explorer(资源管理器)
             cmd(命令行) taskmgr(任务管理器) control(控制面板)
   例：打开记事本 -> {"type":"app","name":"notepad","label":"记事本"}

3. 给QQ某人发消息
   {"type":"qq","contact":"联系人名","message":"消息内容"}
   例：给张三发消息说明天见 -> {"type":"qq","contact":"张三","message":"明天见"}

4. 执行 PowerShell 命令（仅限无害操作：查询信息、打开文件、调整音量亮度等）
   {"type":"shell","command":"命令"}
   例：看看D盘还剩多少空间 -> {"type":"shell","command":"Get-PSDrive D | Select-Object Used,Free"}

5. 控制音量/亮度
   {"type":"volume","level":0到100}  或  {"type":"volume","mute":true}
   例：音量调到50 -> {"type":"volume","level":50}
   例：静音 -> {"type":"volume","mute":true}

6. 截图
   {"type":"screenshot"}

7. 锁定电脑
   {"type":"lock"}

8. 打开文件或文件夹
   {"type":"path","path":"D:\\\\数据文件","label":"数据文件"}

只输出 JSON 或 NONE，不要其他内容。"""


def parse_agent_intent(text):
    """让 LLM 判断是否要操作电脑，返回 task dict 或 None"""
    import requests
    if not CFG.get("llm_key"):
        return None
    try:
        r = requests.post(
            CFG["llm_base"].rstrip("/") + "/chat/completions",
            headers={"Authorization": "Bearer " + CFG["llm_key"],
                     "Content-Type": "application/json"},
            json={
                "model": CFG["llm_model"],
                "messages": [
                    {"role": "system", "content": AGENT_PROMPT},
                    {"role": "user", "content": text},
                ],
                "stream": False,
                "max_tokens": 200,
                "temperature": 0,
            },
            timeout=25)
        if r.status_code != 200:
            note("意图解析 HTTP %d" % r.status_code)
            return None
        out = r.json()["choices"][0]["message"]["content"].strip()
        note("意图解析: %s" % out[:100])

        if not out or out.upper().startswith("NONE"):
            return None

        # 去掉可能的 ```json 包裹
        if "```" in out:
            a = out.find("{")
            b = out.rfind("}")
            if a >= 0 and b > a:
                out = out[a:b + 1]
        else:
            a = out.find("{")
            b = out.rfind("}")
            if a >= 0 and b > a:
                out = out[a:b + 1]

        task = json.loads(out)
        ttype = task.get("type")
        if not ttype:
            return None
        payload = {k: v for k, v in task.items() if k != "type"}
        return {"type": ttype, "payload": payload}
    except Exception as e:
        note("意图解析失败: %s" % str(e)[:60])
        return None


# ---------------- LLM ----------------
def call_llm(q):
    import requests
    if not CFG.get("llm_key"):
        return None, "服务端未配置 llm_key"
    url = CFG["llm_base"].rstrip("/") + "/chat/completions"
    payload = {
        "model": CFG["llm_model"],
        "messages": [
            {"role": "system", "content": CFG["system_prompt"]},
            {"role": "user", "content": q},
        ],
        "stream": False,
        "max_tokens": 400,
    }
    try:
        r = requests.post(url,
                          headers={"Authorization": "Bearer " + CFG["llm_key"],
                                   "Content-Type": "application/json"},
                          json=payload, timeout=45)
        if r.status_code != 200:
            return None, "AI %d" % r.status_code
        return r.json()["choices"][0]["message"]["content"].strip(), None
    except Exception as e:
        return None, "AI异常: %s" % str(e)[:60]


def push_reply(text, kind="reply", meta=None):
    with LOCK:
        REPLY_SEQ[0] += 1
        REPLIES.append({
            "seq": REPLY_SEQ[0],
            "type": kind,
            "text": text,
            "meta": meta or {},
            "ts": int(time.time()),
        })


def log_conv(q, a, kind="voice", extra=None):
    """写对话日志（jsonl，一行一条）"""
    rec = {
        "ts": int(time.time()),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "kind": kind,
        "q": q or "",
        "a": a or "",
    }
    if extra:
        rec.update(extra)
    try:
        with open(CONVLOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        note("写日志失败: %s" % e)


# ---------------- 路由 ----------------
@app.route("/api/task/pull")
def api_task_pull():
    """电脑端拉取待执行任务"""
    if TQ is None:
        return jsonify({"ok": False, "error": "taskqueue 未加载"}), 503
    try:
        limit = int(request.args.get("limit", "5"))
    except ValueError:
        limit = 5
    tasks = TQ.pull(limit)
    if tasks:
        note("电脑取走 %d 个任务" % len(tasks))
    return jsonify({"ok": True, "tasks": tasks})


@app.route("/api/task/result", methods=["POST"])
def api_task_result():
    """电脑端回报执行结果"""
    if TQ is None:
        return jsonify({"ok": False, "error": "taskqueue 未加载"}), 503
    j = request.get_json(silent=True) or {}
    tid = j.get("id")
    if not tid:
        return jsonify({"ok": False, "error": "missing id"}), 400
    ok = j.get("ok", False)
    output = j.get("output", "")
    rec = TQ.complete(tid, ok, output)
    note("任务完成 %s ok=%s: %s" % (tid, ok, str(output)[:60]))
    # 把结果也推给板子
    push_reply(("执行成功：" if ok else "执行失败：") + str(output)[:80],
               "task", {"task_id": tid})
    return jsonify({"ok": True, "id": tid})


@app.route("/api/task/done")
def api_task_done():
    """板子取执行结果"""
    if TQ is None:
        return jsonify({"ok": False, "error": "taskqueue 未加载"}), 503
    try:
        since = int(request.args.get("since", "0"))
    except ValueError:
        since = 0
    return jsonify({"ok": True, "results": TQ.get_done(since)})


@app.route("/api/task/submit", methods=["POST"])
def api_task_submit():
    """手动提交任务（调试用）"""
    if TQ is None:
        return jsonify({"ok": False, "error": "taskqueue 未加载"}), 503
    j = request.get_json(silent=True) or {}
    ttype = j.get("type")
    if not ttype:
        return jsonify({"ok": False, "error": "missing type"}), 400
    tid = TQ.submit(ttype, j.get("payload") or {})
    note("手动提交任务 %s: %s" % (tid, ttype))
    return jsonify({"ok": True, "id": tid})


@app.route("/api/ping")
def api_ping():
    with LOCK:
        pending = len(REPLIES)
        seq = REPLY_SEQ[0]
    return jsonify({
        "ok": True,
        "service": "mybit-relay",
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "pending": pending,
        "seq": seq,
        "asr_ready": _ASR is not None,
    })


@app.route("/api/ask", methods=["POST"])
def api_ask():
    raw = request.get_data()
    if not raw:
        return jsonify({"ok": False, "error": "no audio"}), 400
    note("收到语音 %d 字节 from %s" % (len(raw), request.remote_addr))

    t0 = time.time()
    text, err = recognize(raw)
    if err:
        note("识别失败: " + err)
        return jsonify({"ok": False, "error": err}), 503
    if not text:
        note("识别为空")
        push_reply("没听清，请再说一次", "error")
        return jsonify({"ok": False, "error": "empty"}), 200
    note("识别(%.1fs): %s" % (time.time() - t0, text))

    # 先判断是不是要操作电脑
    if TQ is not None:
        task = parse_agent_intent(text)
        if task:
            tid = TQ.submit(task["type"], task["payload"], source="board")
            note("生成电脑任务 %s: %s" % (tid, task["type"]))
            ans = "好的，正在执行"
            log_conv(text, ans, "voice", {"ip": request.remote_addr,
                                          "bytes": len(raw), "task": tid})
            push_reply(ans, "reply", {"q": text, "task": tid})
            return jsonify({"ok": True, "q": text, "a": ans, "task": tid})

    t1 = time.time()
    ans, aerr = call_llm(text)
    if aerr:
        note("AI 失败: " + aerr)
        push_reply("AI 暂时不可用", "error", {"q": text})
        return jsonify({"ok": False, "error": aerr}), 502
    note("AI(%.1fs): %s" % (time.time() - t1, ans[:60]))

    log_conv(text, ans, "voice", {"ip": request.remote_addr, "bytes": len(raw)})
    push_reply(ans, "reply", {"q": text})
    return jsonify({"ok": True, "q": text, "a": ans})


@app.route("/api/ask_text", methods=["POST", "GET"])
def api_ask_text():
    if request.method == "GET":
        q = request.args.get("q", "").strip()
    else:
        j = request.get_json(silent=True) or {}
        q = (j.get("q") or "").strip()
    if not q:
        return jsonify({"ok": False, "error": "empty"}), 400
    note("文本提问: " + q)

    if TQ is not None:
        task = parse_agent_intent(q)
        if task:
            tid = TQ.submit(task["type"], task["payload"], source="text")
            note("生成电脑任务 %s: %s" % (tid, task["type"]))
            ans = "好的，正在执行"
            log_conv(q, ans, "text", {"ip": request.remote_addr, "task": tid})
            push_reply(ans, "reply", {"q": q, "task": tid})
            return jsonify({"ok": True, "q": q, "a": ans, "task": tid})

    ans, err = call_llm(q)
    if err:
        return jsonify({"ok": False, "error": err}), 502
    note("AI: " + ans[:60])
    log_conv(q, ans, "text", {"ip": request.remote_addr})
    push_reply(ans, "reply", {"q": q})
    return jsonify({"ok": True, "q": q, "a": ans})


@app.route("/api/reply")
def api_reply():
    try:
        since = int(request.args.get("since", "0"))
    except ValueError:
        since = 0
    with LOCK:
        items = [m for m in REPLIES if m["seq"] > since]
        seq = REPLY_SEQ[0]
        if len(REPLIES) > 200:
            del REPLIES[:-200]
    return jsonify({"ok": True, "seq": seq, "count": len(items), "messages": items})


@app.route("/api/conversations")
def api_conversations():
    """读取对话历史（jsonl），供 DSH 或前端查询"""
    try:
        since = int(request.args.get("since", "0"))
    except ValueError:
        since = 0
    try:
        limit = int(request.args.get("limit", "50"))
    except ValueError:
        limit = 50

    items = []
    try:
        with open(CONVLOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("ts", 0) > since:
                    items.append(rec)
    except FileNotFoundError:
        pass
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    if limit and len(items) > limit:
        items = items[-limit:]
    return jsonify({"ok": True, "count": len(items), "items": items})


@app.route("/api/say", methods=["POST"])
def api_say():
    j = request.get_json(silent=True) or {}
    t = (j.get("text") or "").strip()
    if not t:
        return jsonify({"ok": False, "error": "empty"}), 400
    push_reply(t, j.get("type", "notice"))
    return jsonify({"ok": True, "queued": t})


@app.route("/")
def index():
    with LOCK:
        pending = len(REPLIES)
        seq = REPLY_SEQ[0]
    rows = "".join("<li>%s</li>" % l.replace("<", "&lt;") for l in LOG[-40:][::-1]) or "<li>暂无</li>"
    return Response("""<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="3"><title>MYBIT 中转服务</title>
<style>body{font-family:Consolas,monospace;background:#111;color:#0f0;padding:16px}
h2{color:#8cf}li{list-style:none;border-bottom:1px solid #222;padding:2px 0}</style></head>
<body><h2>MYBIT 中转服务 · 运行中</h2>
<p>待取消息 %d ｜ seq=%d ｜ ASR: %s ｜ 模型 %s</p>
<p>板子接口：<code>POST /api/ask</code> ｜ <code>GET /api/reply?since=N</code></p>
<ul>%s</ul></body></html>""" % (pending, seq,
                                "已加载" if _ASR else "未加载",
                                CFG.get("llm_model", "-"), rows),
                    mimetype="text/html")


if __name__ == "__main__":
    CFG = load_config()
    os.makedirs(CFG.get("audio_dir", "/tmp/mybit_audio"), exist_ok=True)
    note("=" * 56)
    note(" MYBIT 中转服务启动")
    note("   端口 %d" % CFG["port"])
    note("   模型 %s" % CFG["llm_model"])
    note("=" * 56)
    # 后台预加载
    try:
        threading.Thread(target=lambda: (lambda: None)() if False else get_asr(), daemon=True).start()
    except Exception:
        pass
    app.run(host="0.0.0.0", port=CFG["port"], debug=False, threaded=True)
