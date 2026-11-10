# -*- coding: utf-8 -*-
"""
MYBIT 串口服务 —— 电脑端
=========================================================
板子发来语音 -> 本程序读串口 -> whisper 识别 -> DeepSeek -> 回传板子

协议
  板子 -> 电脑:
    MSG|S|<块数>              开始
    MSG|D|<序号>|<b64分片>    数据
    MSG|E                     结束
  电脑 -> 板子:
    REP|<b64文字>             回复

用法:
  python board_server.py            常驻运行
  python board_server.py --once     处理一次就退出（测试用）
"""
import base64
import json
import os
import sys
import time

import serial

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = json.load(open(os.path.join(HERE, "gateway_config.json"), encoding="utf-8"))

PORT = "COM3"
BAUD = 115200

AUDIO = {"total": 0, "parts": {}, "got": 0}


def note(msg):
    print("%s %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def call_llm(text):
    import requests
    url = CONFIG["llm_base"].rstrip("/") + "/chat/completions"
    payload = {
        "model": CONFIG["llm_model"],
        "messages": [
            {"role": "system", "content": CONFIG.get("system_prompt", "")},
            {"role": "user", "content": text},
        ],
        "stream": False,
        "max_tokens": 400,
    }
    try:
        r = requests.post(url,
                          headers={"Authorization": "Bearer " + CONFIG["llm_key"],
                                   "Content-Type": "application/json"},
                          json=payload, timeout=60)
        if r.status_code != 200:
            return None, "AI %d" % r.status_code
        return r.json()["choices"][0]["message"]["content"].strip(), None
    except Exception as e:
        return None, "AI异常 %s" % str(e)[:40]


def recognize(wav_bytes):
    """本地 whisper 识别"""
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
    try:
        import local_asr
        return local_asr.transcribe_pcm(pcm, rate)
    except Exception as e:
        return None, "识别异常 %s" % str(e)[:40]


def reply(ser, text):
    b = base64.b64encode(text.encode("utf-8")).decode()
    ser.write(("REP|" + b + "\n").encode())
    ser.flush()


def process_audio(ser, data):
    note("语音 %d 字节，开始识别" % len(data))
    t0 = time.time()
    text, err = recognize(data)
    if err:
        note("识别失败: " + err)
        reply(ser, "识别失败")
        return
    if not text:
        note("识别结果为空（%.1fs）" % (time.time() - t0))
        reply(ser, "没听清，请再说一次")
        return
    note("识别(%.1fs): %s" % (time.time() - t0, text))

    t1 = time.time()
    ans, aerr = call_llm(text)
    if aerr:
        note("AI 失败: " + aerr)
        reply(ser, "AI暂时不可用")
        return
    note("AI(%.1fs): %s" % (time.time() - t1, ans[:60]))
    reply(ser, ans)
    note("已回传板子")


def main():
    once = "--once" in sys.argv
    note("=" * 56)
    note(" MYBIT 串口服务")
    note("   %s @ %d   模型 %s" % (PORT, BAUD, CONFIG["llm_model"]))
    note("=" * 56)

    note("预加载 whisper...")
    try:
        import local_asr
        ok, err = local_asr.warmup()
        note("  %s" % ("就绪" if ok else "失败 %s" % err))
    except Exception as e:
        note("  异常 %s" % str(e)[:60])

    ser = serial.Serial(PORT, BAUD, timeout=0.2)
    time.sleep(0.3)
    ser.reset_input_buffer()
    note("等待板子数据...")

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
            note("开始接收 %d 块" % AUDIO["total"])
            continue

        if s.startswith("MSG|D|"):
            body = s[6:]
            idx, _, payload = body.partition("|")
            try:
                AUDIO["parts"][int(idx)] = base64.b64decode(payload + "=" * (-len(payload) % 4))
                AUDIO["got"] += 1
            except Exception:
                pass
            if AUDIO["total"] and AUDIO["got"] == AUDIO["total"]:
                note("  收齐 %d/%d" % (AUDIO["got"], AUDIO["total"]))
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
                note("数据不完整")
                reply(ser, "数据不完整")
                continue
            process_audio(ser, buf)
            if once:
                note("--once 完成，退出")
                return
            continue

        if len(s) < 100:
            note("板子: " + s)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        note("退出")
