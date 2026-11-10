# -*- coding: utf_8 -*-
# ============================================================
#   AI 学伴 · 板子端（发送模式）
# ------------------------------------------------------------
#   按 A：录音 3 秒 -> 通过串口发出   "MSG|<base64 wav>"
#   按 B：清屏
#   收到回复：串口来的 "REP|<文字>"，显示在 OLED
#
#   板子只负责：录音、发送、显示、播报
#   识别与 AI 由电脑端（DSH）处理
# ============================================================
from npython import *
import sys
import gc
import time

try:
    import ubinascii as b64
except ImportError:
    import binascii as b64

try:
    import uselect
    _POLL = uselect.poll()
    _POLL.register(sys.stdin, uselect.POLLIN)
except Exception:
    _POLL = None

try:
    import audio as _AUDIO
    _REC = "audio"
except ImportError:
    _AUDIO = None
    _REC = None

REC_SECONDS = 3
WAV_PATH = "ask.wav"
CHUNK = 180

BUFFER = []
_roll = 0
_UART1 = None


# ---------------- 显示 ----------------
def show(l1="", l2="", l3="", l4="", l5=""):
    oled.print(1, 1, l1, 1)
    oled.print(1, 2, l2, 1)
    oled.print(1, 3, l3, 1)
    oled.print(1, 4, l4, 1)
    oled.print(1, 5, l5, 1)


def wrap_text(text, width=18):
    lines = []
    cur = ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        cur += ch
        if len(cur) >= width:
            lines.append(cur)
            cur = ""
    if cur:
        lines.append(cur)
    return lines


def present(text):
    global BUFFER, _roll
    BUFFER = wrap_text(text, 18)
    _roll = 0
    for k in range(3):
        oled.print(1, k + 2, BUFFER[k] if k < len(BUFFER) else "", 1)


def speak(text):
    global _UART1
    try:
        if _UART1 is None:
            _UART1 = UART(1, 9600, rx=PINS[0], tx=PINS[1], timeout=10)
            time.sleep_ms(300)
            _UART1.write(b"\x7e\x00\x0a\x01\x00\x03\x03\xef\x01\x06\x07\xef")
            time.sleep_ms(300)
        piece = ""
        for ch in text:
            piece += ch
            if len(piece.encode("utf-8")) >= 120:
                _frame(piece)
                piece = ""
        if piece:
            _frame(piece)
    except Exception:
        pass


def _frame(text):
    data = text.encode("utf-8")[:250]
    cmd = b"\x03\xe8" + bytes([len(data)]) + data
    flen = 6 + len(cmd)
    content = flen.to_bytes(2, "big") + b"\x01\x00\x03" + cmd
    chk = sum(content) % 256
    _UART1.write(b"\x7e" + content + bytes([chk]) + b"\xef")


# ---------------- 串口 ----------------
def send(line):
    sys.stdout.write(line + "\n")


def send_wav(path):
    """流式发送，不缓存全部分片"""
    size = os.stat(path)[6]
    n = (size + CHUNK - 1) // CHUNK
    send("MSG|S|%d" % n)
    f = open(path, "rb")
    i = 0
    while i < n:
        b = f.read(CHUNK)
        if not b:
            break
        send("MSG|D|%d|%s" % (i, b64.b2a_base64(b).strip().decode()))
        del b
        i += 1
        if i % 20 == 0:
            gc.collect()
    f.close()
    send("MSG|E")
    gc.collect()


def poll_reply():
    """非阻塞检查有没有 REP| 消息"""
    if _POLL is None:
        return None
    if not _POLL.poll(0):
        return None
    line = sys.stdin.readline()
    if not line:
        return None
    line = line.strip()
    if line.startswith("REP|"):
        try:
            return b64.a2b_base64(line[4:].encode()).decode("utf-8")
        except Exception:
            return line[4:]
    return None


def record_wav(path, seconds):
    if _REC != "audio":
        raise RuntimeError("no recorder")
    try:
        os.remove(path)
    except Exception:
        pass
    gc.collect()
    gc.collect()
    _AUDIO.recorder_init()
    time.sleep_ms(150)
    gc.collect()
    _AUDIO.record(path, seconds)
    try:
        _AUDIO.recorder_deinit()
    except Exception:
        pass


# ---------------- 主程序 ----------------
oled.fill(0)
show("AI 学伴", "就绪")
time.sleep_ms(1000)
show("按A说话", "B清屏", "", "", "")

while True:
    # 检查电脑发来的回复
    rep = poll_reply()
    if rep:
        show("AI 回答", "", "", "", "")
        present(rep)
        speak(rep)
        time.sleep_ms(200)

    # A 键录音发送
    if button.get_a() == 1:
        time.sleep_ms(250)
        show("请说话...", "", "", "录音3秒", "")
        rgb.write_left(200, 0, 0)
        rgb.write_right(200, 0, 0)
        ok = False
        try:
            record_wav(WAV_PATH, REC_SECONDS)
            ok = True
        except Exception as e:
            show("录音失败", str(e)[:22])
            time.sleep_ms(2000)
        rgb.write_left(0, 0, 0)
        rgb.write_right(0, 0, 0)

        if ok:
            show("录音完成", "发送中...", "", "", "")
            try:
                send_wav(WAV_PATH)
                show("已发送", "等待AI回答...", "", "", "")
                rgb.write_left(0, 0, 200)
                rgb.write_right(0, 0, 200)
            except Exception as e:
                show("发送异常", str(e)[:26])
                time.sleep_ms(2000)
            try:
                os.remove(WAV_PATH)
            except Exception:
                pass

    # B 键清屏
    if button.get_b() == 1:
        time.sleep_ms(250)
        show("已清屏", "按A说话", "", "", "")
        time.sleep_ms(300)

    # 长回答滚动
    if len(BUFFER) > 3:
        _roll += 1
        if _roll % 6 == 0:
            shift = (_roll // 6) % len(BUFFER)
            for k in range(3):
                oled.print(1, k + 2, BUFFER[(shift + k) % len(BUFFER)], 1)

    gc.collect()
    time.sleep_ms(100)
