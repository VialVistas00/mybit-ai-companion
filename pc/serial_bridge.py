# -*- coding: utf-8 -*-
"""
MYBIT 串口 AI 桥  —— 电脑端
=========================================================
板子 <--USB串口(COM3)--> 本程序 --> DeepSeek / 讯飞

线协议（UTF-8 行文本，\n 结尾）
  板子 -> 电脑:
    Q|<base64(utf8文本)>        文本提问
    A|S|<总块数>               开始发语音
    A|D|<序号>|<base64分片>    语音数据块
    A|E                        语音结束
    P|                         心跳
  电脑 -> 板子:
    R|<base64(utf8回答)>
    E|<base64(utf8错误)>
    O|                         心跳应答

启动：python serial_bridge.py
"""
import base64
import json
import os
import sys
import threading
import time

import requests
import serial

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "gateway_config.json")

PORT = "COM3"
BAUD = 115200

AUDIO = {"total": 0, "parts": {}, "got": 0}


def note(msg):
    print("%s %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def load_config():
    cfg = {
        "llm_base": "https://api.deepseek.com/v1",
        "llm_key": "",
        "llm_model": "deepseek-chat",
        "system_prompt": "你是小特，一块信息科技实验板上的AI学伴。用口语化中文回答，不用表情符号和特殊字符，回答控制在70字以内。",
        "xfyun_appid": "",
        "xfyun_apikey": "",
        "xfyun_apisecret": "",
        "asr_engine": "local",
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            note("配置读取失败: %s" % e)
    if not cfg.get("llm_key"):
        cfg["llm_key"] = os.environ.get("DEEPSEEK_API_KEY", "")
    return cfg


CONFIG = load_config()


# ---------------- AI ----------------
def call_llm(text):
    if not CONFIG.get("llm_key"):
        return None, "未配置 AI Key"
    url = CONFIG["llm_base"].rstrip("/") + "/chat/completions"
    payload = {
        "model": CONFIG["llm_model"],
        "messages": [
            {"role": "system", "content": CONFIG["system_prompt"]},
            {"role": "user", "content": text},
        ],
        "stream": False,
        "max_tokens": 400,
    }
    headers = {"Authorization": "Bearer " + CONFIG["llm_key"],
               "Content-Type": "application/json"}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        if r.status_code != 200:
            return None, "AI 返回 %d" % r.status_code
        return r.json()["choices"][0]["message"]["content"].strip(), None
    except Exception as e:
        return None, "AI 异常: %s" % str(e)[:60]


# ---------------- 讯飞语音识别 ----------------
def xfyun_iat(wav_bytes):
    """语音识别入口：优先本地 whisper，无则用讯飞"""
    use_local = CONFIG.get("asr_engine", "local") == "local"
    if use_local:
        import struct as _st
        pcm = wav_bytes
        rate = 8000
        if wav_bytes[:4] == b"RIFF":
            idx = wav_bytes.find(b"data")
            if idx >= 0:
                pcm = wav_bytes[idx + 8:]
            try:
                rate = _st.unpack("<I", wav_bytes[24:28])[0]
            except Exception:
                rate = 8000
        try:
            import local_asr
            text, err = local_asr.transcribe_pcm(pcm, rate)
            if err:
                return None, err
            return (text or None), None
        except Exception as e:
            note("本地识别异常: %s，改用讯飞（若已配置）" % str(e)[:60])
            if not CONFIG.get("xfyun_apikey"):
                return None, "本地识别失败: %s" % str(e)[:60]
    return _xfyun_iat_raw(wav_bytes)


def _xfyun_iat_raw(wav_bytes):
    cfg = CONFIG
    if not (cfg.get("xfyun_appid") and cfg.get("xfyun_apikey") and cfg.get("xfyun_apisecret")):
        return None, "未配置讯飞语音识别"
    try:
        import hashlib
        import hmac
        import websocket
        from urllib.parse import quote

        host = "iat-api.xfyun.cn"
        path = "/v2/iat"
        date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        origin = "host: %s\ndate: %s\nGET %s HTTP/1.1" % (host, date, path)
        sig = hmac.new(cfg["xfyun_apisecret"].encode(), origin.encode(),
                       hashlib.sha256).digest()
        auth_origin = ('api_key="%s", algorithm="hmac-sha256", '
                       'headers="host date request-line", signature="%s"'
                       % (cfg["xfyun_apikey"], base64.b64encode(sig).decode()))
        auth = base64.b64encode(auth_origin.encode()).decode()
        url = "https://%s%s?authorization=%s&date=%s&host=%s" % (
            host, path, quote(auth), quote(date), host)

        pcm = wav_bytes
        rate = 16000
        if wav_bytes[:4] == b"RIFF":
            idx = wav_bytes.find(b"data")
            if idx >= 0:
                pcm = wav_bytes[idx + 8:]
            # 读采样率（WAV 头偏移 24 起 4 字节小端）
            try:
                import struct as _st
                rate = _st.unpack("<I", wav_bytes[24:28])[0]
            except Exception:
                rate = 16000
        # 板子固件录的是 8kHz，讯飞要 16kHz
        if rate == 8000:
            pcm = resample_x2(pcm)
            note("   采样率 8k -> 16k 已转换，%d 字节" % len(pcm))
        elif rate not in (16000,):
            note("   注意：采样率 %d，讯飞要求 16000" % rate)

        audio = base64.b64encode(pcm).decode()
        state = {"text": "", "err": None}
        done = threading.Event()

        def on_open(ws):
            def send():
                step = 12000
                frames = [audio[i:i + step] for i in range(0, len(audio), step)] or [""]
                for idx2, chunk in enumerate(frames):
                    if idx2 == 0:
                        status = 0
                    elif idx2 == len(frames) - 1:
                        status = 2
                    else:
                        status = 1
                    d = {"common": {"app_id": cfg["xfyun_appid"]},
                         "business": {"language": "zh_cn", "domain": "iat",
                                      "accent": "mandarin", "vad_eos": 3000, "punc": 1},
                         "data": {"status": status, "format": "audio/L16;rate=16000",
                                  "encoding": "raw", "audio": chunk}}
                    try:
                        ws.send(json.dumps(d))
                    except Exception:
                        break
                    time.sleep(0.04)
            threading.Thread(target=send, daemon=True).start()

        def on_message(ws, message):
            try:
                j = json.loads(message)
            except Exception:
                return
            if j.get("code") != 0:
                state["err"] = j.get("message", "xfyun error")
                ws.close()
                return
            data = j.get("data") or {}
            if data.get("result"):
                for seg in data["result"].get("ws", []):
                    for cw in seg.get("cw", []):
                        state["text"] += cw.get("w", "")
            if data.get("status") == 2:
                ws.close()

        def on_close(ws, *a):
            done.set()

        def on_error(ws, err):
            state["err"] = str(err)
            done.set()

        ws = websocket.WebSocketApp(url, on_open=on_open, on_message=on_message,
                                    on_close=on_close, on_error=on_error)
        threading.Thread(target=ws.run_forever, daemon=True).start()
        done.wait(35)
        if state["err"]:
            return None, "讯飞: %s" % state["err"]
        return (state["text"] or None), None
    except Exception as e:
        return None, "讯飞异常: %s" % str(e)[:60]


def b64d(s):
    return base64.b64decode(s + "=" * (-len(s) % 4))


def resample_x2(pcm_bytes):
    """8kHz -> 16kHz 线性插值上采样"""
    import struct
    n = len(pcm_bytes) // 2
    if n < 2:
        return pcm_bytes
    s = struct.unpack("<%dh" % n, pcm_bytes[:n * 2])
    out = bytearray()
    for i in range(n - 1):
        a = s[i]
        b = s[i + 1]
        out += struct.pack("<hh", a, int((a + b) / 2))
    out += struct.pack("<hh", s[-1], s[-1])
    return bytes(out)


def b64e(b):
    return base64.b64encode(b).decode()


def reply(ser, kind, text):
    ser.write((kind + "|" + b64e(text.encode("utf-8")) + "\n").encode())
    ser.flush()


def main():
    note("=" * 58)
    note(" MYBIT 串口 AI 桥")
    note("   串口 %s @ %d   模型 %s" % (PORT, BAUD, CONFIG.get("llm_model")))
    note("=" * 58)

    selftest = "--selftest" in sys.argv
    voice_test = "--voice" in sys.argv

    if "--warmup" in sys.argv or voice_test:
        note("[预热] 加载本地 whisper 模型...")
        try:
            import local_asr
            ok, err = local_asr.warmup()
            note("[预热] %s" % ("完成" if ok else "失败: %s" % err))
        except Exception as e:
            note("[预热] 异常: %s" % str(e)[:80])

    ser = serial.Serial(PORT, BAUD, timeout=0.2, rtscts=False, dsrdtr=False)
    time.sleep(0.3)
    ser.reset_input_buffer()
    ser.write(b"\x03\x03")
    time.sleep(0.5)
    ser.reset_input_buffer()
    # 关键：进 REPL 后先强制回收内存，否则残留对象会让录音 MemoryError
    ser.write(b"import gc;gc.collect();print('FREEMEM', gc.mem_free())\r\n")
    time.sleep(1.0)
    while ser.in_waiting:
        ln = ser.readline().decode("utf-8", "ignore").strip()
        if "FREEMEM" in ln:
            note("板子空闲内存: " + ln)
    ser.reset_input_buffer()

    if selftest:
        note("[自测] 让板子执行 selftest.py")
        ser.write(b"\x03\x03")
        time.sleep(0.4)
        ser.reset_input_buffer()
        # 普通 REPL 下直接 exec 文件（不用 Ctrl-E，那会进 paste mode）
        ser.write(b"exec(open('selftest.py').read())\r\n")
        time.sleep(0.8)
        note("[自测] 已下发，等待板子提问")

    if voice_test:
        note("[语音测试] 让板子录音并发送")
        ser.write(b"\x03\x03")
        time.sleep(0.4)
        ser.reset_input_buffer()
        ser.write(b"exec(open('voicetest.py').read())\r\n")
        time.sleep(0.8)
        note("[语音测试] 已下发")

    note("等待板子请求...")

    while True:
        try:
            raw = ser.readline()
        except Exception as e:
            note("读串口异常: %s" % e)
            time.sleep(0.5)
            continue
        if not raw:
            continue
        line = raw.decode("utf-8", "ignore").strip()
        if not line:
            continue

        # ---- 心跳 ----
        if line == "P|":
            ser.write(b"O|\n")
            continue

        # ---- 文本提问 ----
        if line.startswith("Q|"):
            try:
                question = b64d(line[2:]).decode("utf-8")
            except Exception:
                continue
            note("文本提问: " + question)
            ans, err = call_llm(question)
            if err:
                note("失败: " + err)
                reply(ser, "E", err)
            else:
                note("回答: " + ans[:70])
                reply(ser, "R", ans)
            continue

        # ---- 语音：开始 ----
        if line.startswith("A|S|"):
            try:
                AUDIO["total"] = int(line[4:])
            except Exception:
                AUDIO["total"] = 0
            AUDIO["parts"] = {}
            AUDIO["got"] = 0
            note("开始接收语音，共 %d 块" % AUDIO["total"])
            continue

        # ---- 语音：数据块 ----
        if line.startswith("A|D|"):
            body = line[4:]
            seq, _, payload = body.partition("|")
            try:
                idx = int(seq)
                AUDIO["parts"][idx] = b64d(payload)
                AUDIO["got"] += 1
            except Exception:
                pass
            if AUDIO["total"] and AUDIO["got"] % 10 == 0:
                note("  已收 %d/%d" % (AUDIO["got"], AUDIO["total"]))
            continue

        # ---- 语音：结束 ----
        if line == "A|E":
            total = AUDIO["total"]
            note("语音接收完毕 %d/%d 块" % (AUDIO["got"], total))
            buf = b""
            ok = True
            for i in range(total):
                p = AUDIO["parts"].get(i)
                if p is None:
                    ok = False
                    break
                buf += p
            if not ok or not buf:
                reply(ser, "E", "语音数据不完整")
                continue
            note("语音 %d 字节，开始识别" % len(buf))
            text, err = xfyun_iat(buf)
            if err:
                note("识别失败: " + err)
                reply(ser, "E", err)
                continue
            if not text:
                note("识别结果为空（没听到人声？）")
                reply(ser, "E", "没听清，请再说一次")
                continue
            note("识别结果: " + text)
            ans, aerr = call_llm(text)
            if aerr:
                note("AI 失败: " + aerr)
                reply(ser, "E", aerr)
            else:
                note("回答: " + ans[:70])
                reply(ser, "R", ans)
            continue

        if len(line) < 120:
            note("板子输出: " + line)
        if selftest and line.startswith("FINAL|"):
            note("[自测] 板子最终收到: " + line[6:])
            note("[自测] 完成")
            return
        if voice_test and line.startswith("VOICE_DONE"):
            note("[语音测试] 完成")
            return


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        note("已退出")
