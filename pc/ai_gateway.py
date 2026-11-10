# -*- coding: utf-8 -*-
"""
MYBIT AI 网关 —— 部署在电脑上，给信息科技实验板提供 AI 问答
=============================================================
板子侧只跟这台电脑打交道：
  1. 板子录音 -> POST /api/ask (multipart, wav)      语音提问
  2. 板子可选 POST /api/ask_text (json)              文本提问（调试用）
  3. 板子轮询 GET /api/reply?since=N                 一直接受服务器下发的消息
  4. 板子 GET /api/ping                              心跳/连通性

AI 后端：默认走 DeepSeek（OpenAI 兼容），可在 config.json 里切换成任意兼容端点。
语音识别：优先讯飞（配置了就用），否则用板子传上来的文本，或本地 whisper（若安装）。

启动：  python ai_gateway.py
"""
import io
import json
import os
import queue
import re
import threading
import time

import requests
from flask import Flask, jsonify, request

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "gateway_config.json")

DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "port": 8080,
    # ---- AI 后端（OpenAI 兼容）----
    "llm_base": "https://api.deepseek.com/v1",
    "llm_key": "",
    "llm_model": "deepseek-chat",
    "system_prompt": "你是小特，一块信息科技实验板上的AI学伴。用口语化中文回答，不用表情符号和特殊字符，回答控制在80字以内。",
    # ---- 讯飞语音识别（可选，留空则跳过）----
    "xfyun_appid": "",
    "xfyun_apikey": "",
    "xfyun_apisecret": "",
}

app = Flask(__name__)
CONFIG = {}
MESSAGES = []          # 待板子取走的消息队列
MSG_LOCK = threading.Lock()
MSG_SEQ = [0]
LOG = []


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            print("[warn] 配置文件读取失败:", e)
    env_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if env_key and not cfg.get("llm_key"):
        cfg["llm_key"] = env_key
    return cfg


def note(msg):
    line = "%s %s" % (time.strftime("%H:%M:%S"), msg)
    LOG.append(line)
    del LOG[:-200]
    print(line, flush=True)


def push_message(text, kind="reply", meta=None):
    """把一条消息推进队列，等板子来取"""
    with MSG_LOCK:
        MSG_SEQ[0] += 1
        MESSAGES.append({
            "seq": MSG_SEQ[0],
            "type": kind,
            "text": text,
            "meta": meta or {},
            "ts": int(time.time()),
        })


# ---------------- AI 后端 ----------------
def call_llm(user_text):
    cfg = CONFIG
    if not cfg.get("llm_key"):
        return None, "未配置 AI Key（gateway_config.json 里的 llm_key）"
    url = cfg["llm_base"].rstrip("/") + "/chat/completions"
    payload = {
        "model": cfg["llm_model"],
        "messages": [
            {"role": "system", "content": cfg["system_prompt"]},
            {"role": "user", "content": user_text},
        ],
        "stream": False,
        "max_tokens": 400,
    }
    headers = {
        "Authorization": "Bearer " + cfg["llm_key"],
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=45)
        if r.status_code != 200:
            return None, "AI 返回 %d: %s" % (r.status_code, r.text[:200])
        data = r.json()
        return data["choices"][0]["message"]["content"].strip(), None
    except Exception as e:
        return None, "AI 调用异常: %s" % e


# ---------------- 讯飞语音识别 ----------------
def xfyun_iat(wav_bytes):
    """用讯飞开放平台做语音转文字；未配置返回 (None, 说明)"""
    cfg = CONFIG
    if not (cfg.get("xfyun_appid") and cfg.get("xfyun_apikey") and cfg.get("xfyun_apisecret")):
        return None, "未配置讯飞语音识别"
    try:
        import base64
        import hashlib
        import hmac
        from urllib.parse import quote

        host = "iat-api.xfyun.cn"
        path = "/v2/iat"
        date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        signature_origin = "host: %s\ndate: %s\nGET %s HTTP/1.1" % (host, date, path)
        sig = hmac.new(cfg["xfyun_apisecret"].encode(), signature_origin.encode(),
                       hashlib.sha256).digest()
        authorization_origin = (
            'api_key="%s", algorithm="hmac-sha256", headers="host date request-line", '
            'signature="%s"' % (cfg["xfyun_apikey"], base64.b64encode(sig).decode()))
        authorization = base64.b64encode(authorization_origin.encode()).decode()
        url = "https://%s%s?authorization=%s&date=%s&host=%s" % (
            host, path, quote(authorization), quote(date), host)

        import websocket  # 需要 pip install websocket-client
        audio = base64.b64encode(wav_bytes).decode()
        result = {"text": ""}
        done = threading.Event()

        def on_open(ws):
            def send():
                frames = [audio[i:i + 12000] for i in range(0, len(audio), 12000)] or [""]
                for idx, chunk in enumerate(frames):
                    biz = {"language": "zh_cn", "domain": "iat", "accent": "mandarin",
                           "vad_eos": 3000, "punc": 1}
                    status = 0 if idx == 0 else 1
                    if idx == len(frames) - 1:
                        status = 2
                    d = {"common": {"app_id": cfg["xfyun_appid"]}, "business": biz,
                         "data": {"status": status, "format": "audio/L16;rate=16000",
                                  "encoding": "raw", "audio": chunk}}
                    ws.send(json.dumps(d))
                    time.sleep(0.04)
            threading.Thread(target=send, daemon=True).start()

        def on_message(ws, message):
            j = json.loads(message)
            if j.get("code") != 0:
                result["text"] = "__ERR__" + str(j.get("message"))
                ws.close()
                return
            data = j.get("data") or {}
            if data.get("result"):
                for ws_item in data["result"].get("ws", []):
                    for cw in ws_item.get("cw", []):
                        result["text"] += cw.get("w", "")
            if data.get("status") == 2:
                ws.close()

        def on_close(ws, *a):
            done.set()

        ws = websocket.WebSocketApp(url, on_open=on_open, on_message=on_message, on_close=on_close)
        threading.Thread(target=ws.run_forever, daemon=True).start()
        done.wait(30)
        txt = result["text"]
        if txt.startswith("__ERR__"):
            return None, txt[7:]
        return (txt or None), None
    except Exception as e:
        return None, "讯飞识别异常: %s" % e


def wav_to_raw_pcm(wav_bytes):
    """从 WAV 里剥出裸 PCM（讯飞要 raw）"""
    if wav_bytes[:4] != b"RIFF":
        return wav_bytes
    idx = wav_bytes.find(b"data")
    if idx < 0:
        return wav_bytes
    return wav_bytes[idx + 8:]


# ---------------- 路由 ----------------
@app.route("/api/ping")
def api_ping():
    with MSG_LOCK:
        pending = len(MESSAGES)
    return jsonify({"ok": True, "service": "mybit-ai-gateway",
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "pending": pending, "seq": MSG_SEQ[0]})


@app.route("/api/ask_text", methods=["POST"])
def api_ask_text():
    j = request.get_json(force=True, silent=True) or {}
    question = (j.get("q") or "").strip()
    if not question:
        return jsonify({"ok": False, "error": "empty question"}), 400
    note("文本提问: " + question)
    answer, err = call_llm(question)
    if err:
        note("AI 失败: " + err)
        return jsonify({"ok": False, "error": err}), 502
    note("AI 回答: " + answer[:60])
    push_message(answer, "reply", {"q": question})
    return jsonify({"ok": True, "q": question, "a": answer})


@app.route("/api/ask", methods=["POST"])
def api_ask():
    """板子 POST 上来的语音（wav 二进制，body 或 form 字段 audio）"""
    if "audio" in request.files:
        wav = request.files["audio"].read()
    else:
        wav = request.get_data()
    if not wav:
        return jsonify({"ok": False, "error": "no audio"}), 400
    note("收到语音 %d 字节" % len(wav))

    # 1) 语音转文字
    text, err = xfyun_iat(wav_to_raw_pcm(wav))
    if err:
        note("语音识别失败: " + err)
        # 没配识别时，允许板子带 text 参数直接用
        text = request.args.get("text", "").strip()
        if not text:
            push_message("语音识别未配置", "error", {"detail": err})
            return jsonify({"ok": False, "error": err}), 503

    note("识别结果: " + text)
    # 2) 问 AI
    answer, aerr = call_llm(text)
    if aerr:
        note("AI 失败: " + aerr)
        push_message("AI 暂时不可用", "error", {"q": text, "detail": aerr})
        return jsonify({"ok": False, "error": aerr}), 502

    note("AI 回答: " + answer[:60])
    push_message(answer, "reply", {"q": text})
    return jsonify({"ok": True, "q": text, "a": answer})


@app.route("/api/reply")
def api_reply():
    """板子轮询取消息。since=上次取到的 seq"""
    try:
        since = int(request.args.get("since", "0"))
    except ValueError:
        since = 0
    with MSG_LOCK:
        items = [m for m in MESSAGES if m["seq"] > since]
        seq = MSG_SEQ[0]
        # 清掉已被取走 200 条之外的历史，防内存涨
        if len(MESSAGES) > 200:
            del MESSAGES[:-200]
    return jsonify({"ok": True, "seq": seq, "count": len(items), "messages": items})


@app.route("/api/say", methods=["POST"])
def api_say():
    """手动往板子推一条消息（调试/通知用）"""
    j = request.get_json(force=True, silent=True) or {}
    text = (j.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "empty text"}), 400
    push_message(text, j.get("type", "notice"))
    return jsonify({"ok": True, "queued": text})


@app.route("/")
def index():
    with MSG_LOCK:
        pending = len(MESSAGES)
        seq = MSG_SEQ[0]
    rows = "".join("<li>%s</li>" % l.replace("<", "&lt;") for l in LOG[-30:][::-1]) or "<li>暂无</li>"
    return """<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="3"><title>MYBIT AI 网关</title>
<style>body{font-family:Consolas,monospace;background:#111;color:#0f0;padding:16px}
h2{color:#8cf}li{list-style:none;border-bottom:1px solid #222;padding:2px 0}</style></head>
<body><h2>MYBIT AI 网关 · 运行中</h2>
<p>待取消息 %d 条 ｜ 当前 seq=%d ｜ AI 模型 %s</p>
<p>板子接口：<code>GET /api/reply?since=N</code> ｜ <code>POST /api/ask</code></p>
<ul>%s</ul></body></html>""" % (pending, seq, CONFIG.get("llm_model", "-"), rows)


if __name__ == "__main__":
    CONFIG = load_config()
    if not CONFIG.get("llm_key"):
        print("[!] 未配置 llm_key，AI 问答会失败。请在 gateway_config.json 或环境变量 DEEPSEEK_API_KEY 里填。")
    print("=" * 58)
    print(" MYBIT AI 网关启动中")
    print("   监听 : http://%s:%d" % (CONFIG["host"], CONFIG["port"]))
    print("   模型 : %s @ %s" % (CONFIG["llm_model"], CONFIG["llm_base"]))
    print("=" * 58, flush=True)
    app.run(host=CONFIG["host"], port=CONFIG["port"], debug=False, threaded=True)
