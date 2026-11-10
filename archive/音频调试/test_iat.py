# -*- coding: utf-8 -*-
"""把刚才录的 wav 送讯飞识别，验证识别链路是否可用"""
import base64
import hashlib
import hmac
import json
import os
import sys
import threading
import time
import wave
from urllib.parse import quote

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")

LOCAL = r"D:\数据文件\上课\信电导论\开发板\_scratch\live.wav"
APPID = "YOUR_XFYUN_APPID"
APIKEY = "YOUR_XFYUN_APPID"
SECRET = "YOUR_XFYUN_APISECRET"


def resample_x2(pcm):
    import struct
    n = len(pcm) // 2
    s = struct.unpack("<%dh" % n, pcm[:n * 2])
    out = bytearray()
    for i in range(n - 1):
        a, b = s[i], s[i + 1]
        out += struct.pack("<hh", a, (a + b) // 2)
    out += struct.pack("<hh", s[-1], s[-1])
    return bytes(out)


w = wave.open(LOCAL, "rb")
sr = w.getframerate()
data = w.readframes(w.getnframes())
w.close()
print("原始:", sr, "Hz,", len(data), "字节")
if sr == 8000:
    data = resample_x2(data)
    print("上采样后:", len(data), "字节 (16kHz)")

try:
    import websocket
except ImportError:
    print("缺 websocket-client")
    sys.exit(1)

host, path = "iat-api.xfyun.cn", "/v2/iat"
date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
origin = "host: %s\ndate: %s\nGET %s HTTP/1.1" % (host, date, path)
sig = hmac.new(SECRET.encode(), origin.encode(), hashlib.sha256).digest()
auth_origin = ('api_key="%s", algorithm="hmac-sha256", '
               'headers="host date request-line", signature="%s"'
               % (APIKEY, base64.b64encode(sig).decode()))
auth = base64.b64encode(auth_origin.encode()).decode()
url = "wss://%s%s?authorization=%s&date=%s&host=%s" % (
    host, path, quote(auth), quote(date), host)

audio = base64.b64encode(data).decode()
state = {"text": "", "err": None, "code": None}
done = threading.Event()


def on_open(ws):
    def send():
        step = 12000
        frames = [audio[i:i + step] for i in range(0, len(audio), step)] or [""]
        for i, chunk in enumerate(frames):
            status = 0 if i == 0 else (2 if i == len(frames) - 1 else 1)
            d = {"common": {"app_id": APPID},
                 "business": {"language": "zh_cn", "domain": "iat",
                              "accent": "mandarin", "vad_eos": 3000, "punc": 1},
                 "data": {"status": status, "format": "audio/L16;rate=16000",
                          "encoding": "raw", "audio": chunk}}
            try:
                ws.send(json.dumps(d))
            except Exception as e:
                state["err"] = str(e)
                break
            time.sleep(0.04)
    threading.Thread(target=send, daemon=True).start()


def on_message(ws, message):
    j = json.loads(message)
    if j.get("code"):
        state["err"] = "%s %s" % (j.get("code"), j.get("message"))
        state["code"] = j.get("code")
        ws.close()
        return
    d = j.get("data") or {}
    if d.get("result"):
        for seg in d["result"].get("ws", []):
            for cw in seg.get("cw", []):
                state["text"] += cw.get("w", "")
    if d.get("status") == 2:
        ws.close()


def on_close(ws, *a):
    done.set()


def on_error(ws, e):
    state["err"] = str(e)
    done.set()


print("连接讯飞...")
ws = websocket.WebSocketApp(url, on_open=on_open, on_message=on_message,
                            on_close=on_close, on_error=on_error)
threading.Thread(target=ws.run_forever, daemon=True).start()
done.wait(40)

if state["err"]:
    print("识别失败:", state["err"])
else:
    print("识别结果:", repr(state["text"]))
