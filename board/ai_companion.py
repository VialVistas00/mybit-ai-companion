# -*- coding: utf_8 -*-
# ============================================================
#   AI 学伴 · 板子端   (信息科技实验板 / ESP32 / MicroPython)
# ------------------------------------------------------------
#   板子连 YOUR_CAMPUS_SSID -> 每 1.5 秒轮询电脑上的 AI 网关
#   按 A 键：录音 3 秒 -> 上传 -> 电脑转文字 -> 问 AI -> 回传
#   收到回答：OLED 滚动显示 + 语音播报（若有语音合成模块）
#
#   电脑端必须先跑 ai_gateway.py（监听 8080）
# ============================================================
from npython import *
import network
import time
import gc
import socket

try:
    import urllib.parse as _up
except ImportError:
    _up = None

# ---------------- 配置 ----------------
SSID = "YOUR_CAMPUS_SSID"
PWD = ""
GW_IP = "PC_IP"      # 电脑 IP
GW_PORT = 8080

POLL_MS = 1500               # 轮询间隔
REC_SECONDS = 3              # 录音时长
WAV_PATH = "ask.wav"

_HAS_MIC = True
try:
    import microphone
except ImportError:
    _HAS_MIC = False

# ---------------- 屏幕 ----------------
BUFFER = []        # 待显示的回答行
CUR_SEQ = 0


def show(line1, line2="", line3="", line4="", line5=""):
    oled.print(1, 1, line1, 1)
    oled.print(1, 2, line2, 1)
    oled.print(1, 3, line3, 1)
    oled.print(1, 4, line4, 1)
    oled.print(1, 5, line5, 1)


# ---------------- 网络 ----------------
def connect():
    w = network.WLAN(network.STA_IF)
    w.active(0)
    time.sleep(0.6)
    w.active(1)
    time.sleep(1.0)
    if w.isconnected():
        return w.ifconfig()[0]
    try:
        if PWD:
            w.connect(SSID, PWD)
        else:
            w.connect(SSID)
    except Exception:
        pass
    t = time.time()
    while not w.isconnected() and time.time() - t < 20:
        time.sleep(0.4)
    if w.isconnected():
        return w.ifconfig()[0]
    return None


# ---------------- HTTP ----------------
def http_post(host, port, path, body, content_type="application/octet-stream", timeout=40):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(socket.getaddrinfo(host, port)[0][4])
        head = ("POST " + path + " HTTP/1.0\r\nHost: " + host + ":" + str(port)
                + "\r\nContent-Type: " + content_type
                + "\r\nContent-Length: " + str(len(body))
                + "\r\nConnection: close\r\n\r\n")
        s.send(head.encode())
        # 分块发 body，省内存
        step = 512
        i = 0
        while i < len(body):
            s.send(body[i:i + step])
            i += step
        buf = b""
        while len(buf) < 3000:
            try:
                c = s.recv(400)
            except Exception:
                break
            if not c:
                break
            buf += c
        return buf
    finally:
        s.close()


def http_get(host, port, path, timeout=15, maxlen=4000):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(socket.getaddrinfo(host, port)[0][4])
        s.send(("GET " + path + " HTTP/1.0\r\nHost: " + host + ":" + str(port)
                + "\r\nConnection: close\r\n\r\n").encode())
        buf = b""
        while len(buf) < maxlen:
            try:
                c = s.recv(400)
            except Exception:
                break
            if not c:
                break
            buf += c
        return buf
    finally:
        s.close()


def body_of(resp):
    """取 HTTP 响应正文"""
    idx = resp.find(b"\r\n\r\n")
    if idx < 0:
        return resp
    return resp[idx + 4:]


def json_str(raw, key):
    """从 JSON 文本里抠出 key 对应的字符串值（简易解析，省内存）"""
    k = ('"' + key + '":"').encode()
    i = raw.find(k)
    if i < 0:
        return None
    i += len(k)
    out = bytearray()
    p = i
    while p < len(raw):
        ch = raw[p:p + 1]
        if ch == b"\\":
            nxt = raw[p + 1:p + 2]
            if nxt == b"u":
                try:
                    code = int(raw[p + 2:p + 6], 16)
                    if code < 128:
                        out.append(code)
                    else:
                        out += b"?"
                except Exception:
                    pass
                p += 6
                continue
            if nxt == b"n":
                out += b"\n"
            elif nxt == b"t":
                out += b"\t"
            else:
                out += nxt
            p += 2
            continue
        if ch == b'"':
            break
        out += ch
        p += 1
    try:
        return out.decode("utf-8")
    except Exception:
        s = ""
        for b in out:
            if 32 <= b < 127:
                s += chr(b)
        return s


def json_int(raw, key):
    k = ('"' + key + '":').encode()
    i = raw.find(k)
    if i < 0:
        return None
    i += len(k)
    j = i
    while j < len(raw) and (48 <= raw[j] <= 57):
        j += 1
    try:
        return int(raw[i:j])
    except Exception:
        return None


# ---------------- 显示/播报 ----------------
def wrap_text(text, width=18):
    """按 OLED 宽度折行（中文算 1 列，英文约 1 列）"""
    lines = []
    cur = ""
    for ch in text:
        cur += ch
        if len(cur) >= width:
            lines.append(cur)
            cur = ""
    if cur:
        lines.append(cur)
    return lines


def present(text):
    """把回答显示并播报"""
    global BUFFER
    BUFFER = wrap_text(text, 18)
    # 前 3 行立刻显示
    for k in range(min(3, len(BUFFER))):
        oled.print(1, k + 2, BUFFER[k], 1)
    speak(text[:100])


def speak(text):
    """若有外置语音合成模块则播报（UART1, PINS[0]/PINS[1]）"""
    try:
        uart1 = UART(1, 9600, rx=PINS[0], tx=PINS[1], timeout=10)
        time.sleep(0.2)
        # 设 UTF-8 模式
        uart1.write(b"\x7e\x00\x0a\x01\x00\x03\x03\xef\x01\x06\x07\xef")
        time.sleep(0.2)
        data = text.encode("utf-8")
        if len(data) > 240:
            data = data[:240]
        cmd = b"\x03\xe8" + bytes([len(data)]) + data
        frame_len = 6 + len(cmd)
        content = frame_len.to_bytes(2, "big") + b"\x01\x00\x03" + cmd
        chk = sum(content) % 256
        uart1.write(b"\x7e" + content + bytes([chk]) + b"\xef")
        time.sleep(0.3)
    except Exception:
        pass


# ---------------- 主程序 ----------------
show("AI 学伴启动", "连接 " + SSID)
ip = connect()
if not ip:
    show("WiFi 连接失败", "请检查热点")
    while True:
        time.sleep(1)

show("已联网", "IP:" + ip, "网关:" + GW_IP)

# 连通性确认
_try = 0
while _try < 3:
    try:
        r = body_of(http_get(GW_IP, GW_PORT, "/api/ping", 8, 400))
        if r.find(b'"ok":true') >= 0 or r.find(b'"ok": true') >= 0:
            break
    except Exception:
        pass
    _try += 1
    time.sleep(1)

if _try >= 3:
    show("连不上电脑网关", GW_IP + ":" + str(GW_PORT), "请先运行", "ai_gateway.py")
    while True:
        time.sleep(1)

show("已连接网关", "按A键说话", "A:提问  B:清屏")

_eat_flash = 0

while True:
    # 1) 按键：A 提问
    if button.get_a() == 1:
        time.sleep_ms(250)
        show("请说话...", "", "", "录音中", "")

        ok = False
        if _HAS_MIC:
            try:
                try:
                    os.remove(WAV_PATH)
                except Exception:
                    pass
                gc.collect()
                microphone.record(WAV_PATH, REC_SECONDS)
                ok = True
            except Exception as e:
                show("录音失败", str(e)[:20])
                time.sleep(1.5)

        if ok:
            show("录音完成", "上传中...", "", "", "")
            try:
                f = open(WAV_PATH, "rb")
                wav = f.read()
                f.close()
                resp = http_post(GW_IP, GW_PORT, "/api/ask", wav,
                                 "audio/wav", timeout=60)
                body = body_of(resp)
                if body.find(b'"ok":true') >= 0 or body.find(b'"ok": true') >= 0:
                    a = json_str(body, "a")
                    q = json_str(body, "q")
                    show("已提问", "你:" + (q or "")[:16], "等待播报")
                    if a:
                        present(a)
                else:
                    e = json_str(body, "error") or "未知错误"
                    show("上传失败", e[:30])
                    time.sleep(1.5)
            except Exception as e:
                show("上传异常", str(e)[:30])
                time.sleep(1.5)
            try:
                os.remove(WAV_PATH)
            except Exception:
                pass
        else:
            show("本固件无麦克风", "请用文字测试")
            time.sleep(1.5)

        show("已连接网关", "按A键说话", "B:清屏")
        time.sleep_ms(400)

    # 2) 按键：B 清屏
    if button.get_b() == 1:
        time.sleep_ms(250)
        oled.print(1, 1, "已清屏", 1)
        oled.print(1, 2, "按A键说话", 1)
        oled.print(1, 3, "", 1)
        oled.print(1, 4, "", 1)
        oled.print(1, 5, "", 1)
        time.sleep_ms(300)

    # 3) 轮询网关，接收推送/回答
    try:
        raw = body_of(http_get(GW_IP, GW_PORT, "/api/reply?since=" + str(CUR_SEQ), 10, 3000))
        new_seq = json_int(raw, "seq")
        cnt = json_int(raw, "count")
        if new_seq is not None:
            CUR_SEQ = new_seq
        if cnt and cnt > 0:
            txt = json_str(raw, "text")
            if txt:
                present(txt)
    except Exception:
        pass

    # 4) 滚动显示剩余行
    if len(BUFFER) > 3:
        _eat_flash += 1
        if _eat_flash % 3 == 0:
            shift = (_eat_flash // 3) % len(BUFFER)
            for k in range(3):
                idx = (shift + k) % len(BUFFER)
                oled.print(1, k + 2, BUFFER[idx], 1)

    gc.collect()
    time.sleep_ms(POLL_MS)
