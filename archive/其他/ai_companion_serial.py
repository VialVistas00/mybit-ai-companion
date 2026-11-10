# -*- coding: utf_8 -*-
# ============================================================
#   AI 学伴 · 板子端（串口版）
# ------------------------------------------------------------
#   板子 <--USB串口--> 电脑(serial_bridge.py) --> DeepSeek
#   A 键：录音 3 秒 -> 发给电脑 -> 转文字问 AI -> 回传回答
#   B 键：清屏 / 打断播报
#
#   线协议（UTF-8 行文本）:
#     发送  Q|<b64 文本>
#     发送  A|S|<块数>  /  A|D|<序号>|<b64>  /  A|E
#     接收  R|<b64 回答>  /  E|<b64 错误>
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
    import microphone
    _MIC = "microphone"
except ImportError:
    try:
        import audio
        _MIC = "audio"
    except ImportError:
        _MIC = None

REC_SECONDS = 3
WAV_PATH = "ask.wav"
REPLY_TIMEOUT = 90000
CHUNK = 180                  # 180 字节/片 -> base64 后约 240 字符，堆安全且块数少

BUFFER = []
_roll = 0


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


def sleep_ms(ms):
    time.sleep_ms(ms)


# ---------------- 语音合成播报 ----------------
_UART1 = None


def speak(text):
    """外置语音合成模块（UART1），单帧上限 255 字节 -> 分句发送"""
    global _UART1
    try:
        if _UART1 is None:
            _UART1 = UART(1, 9600, rx=PINS[0], tx=PINS[1], timeout=10)
            sleep_ms(300)
            _UART1.write(b"\x7e\x00\x0a\x01\x00\x03\x03\xef\x01\x06\x07\xef")
            sleep_ms(300)
        piece = ""
        for ch in text:
            piece += ch
            if len(piece.encode("utf-8")) >= 120:
                _speak_frame(piece)
                piece = ""
        if piece:
            _speak_frame(piece)
        # 估算播报时长并等待
        wait = int(len(text) * 350)
        t0 = time.ticks_ms()
        while time.ticks_ms() - t0 < wait:
            if button.get_b() == 1:
                try:
                    _speak_frame(" ")
                except Exception:
                    pass
                break
            sleep_ms(100)
    except Exception:
        pass


def _speak_frame(text):
    data = text.encode("utf-8")
    if len(data) > 250:
        data = data[:250]
    cmd = b"\x03\xe8" + bytes([len(data)]) + data
    frame_len = 6 + len(cmd)
    content = frame_len.to_bytes(2, "big") + b"\x01\x00\x03" + cmd
    chk = sum(content) % 256
    _UART1.write(b"\x7e" + content + bytes([chk]) + b"\xef")


# ---------------- 串口收发 ----------------
def send(line):
    sys.stdout.write(line + "\n")


def send_text_question(text):
    send("Q|" + b64.b2a_base64(text.encode("utf-8")).strip().decode())


def send_wav(path):
    """流式分块发送：A|S|N  ->  A|D|i|b64  ->  A|E
    不缓存全部分片（49KB 的 wav 若一次性转 base64 会吃掉 60KB+ 堆内存导致 MemoryError）
    分片 180 字节 -> base64 后 240 字符，实测每块约 27ms"""
    size = os.stat(path)[6]
    n = (size + CHUNK - 1) // CHUNK
    send("A|S|%d" % n)
    f = open(path, "rb")
    i = 0
    while i < n:
        b = f.read(CHUNK)
        if not b:
            break
        send("A|D|%d|%s" % (i, b64.b2a_base64(b).strip().decode()))
        del b
        i += 1
        if i % 20 == 0:
            gc.collect()
    f.close()
    send("A|E")
    gc.collect()


def wait_reply():
    """等待电脑回 R|/E|，返回 (kind, text)"""
    t0 = time.ticks_ms()
    while time.ticks_ms() - t0 < REPLY_TIMEOUT:
        if _POLL is not None:
            if not _POLL.poll(150):
                continue
        line = sys.stdin.readline()
        if not line:
            continue
        line = line.strip()
        if line.startswith("R|") or line.startswith("E|"):
            kind = line[0]
            raw = line[2:]
            try:
                txt = b64.a2b_base64(raw.encode()).decode("utf-8")
            except Exception:
                txt = raw
            return kind, txt
    return None, None


def record_wav(path, seconds):
    """兼容两种固件的录音：microphone.record 或 audio.record"""
    try:
        os.remove(path)
    except Exception:
        pass
    # 录音需要连续约 4KB 块，先尽量腾出内存
    gc.collect()
    # 释放屏幕缓冲区与之前的大对象
    for _ in range(3):
        gc.collect()
    if _MIC == "microphone":
        microphone.record(path, seconds)
    elif _MIC == "audio":
        audio.recorder_init()
        time.sleep_ms(150)
        gc.collect()
        audio.record(path, seconds)
        try:
            audio.recorder_deinit()
        except Exception:
            pass
    else:
        raise RuntimeError("本固件无录音模块")
    return True


# ---------------- 主程序 ----------------
oled.fill(0)
show("AI 学伴", "串口模式")
sleep_ms(1200)
show("AI 学伴就绪", "按A键说话", "B键清屏/打断", "", "电脑运行 bridge")

while True:
    # ---- A：语音提问 ----
    if button.get_a() == 1:
        sleep_ms(260)
        if _MIC is None:
            show("无录音模块", "本固件不支持", "录音", "", "")
            sleep_ms(2000)
            show("AI 学伴就绪", "按A键说话", "B键清屏/打断", "", "")
            continue

        show("请说话...", "", "", "录音中3秒", "")
        rgb.write_left(200, 0, 0)
        rgb.write_right(200, 0, 0)
        ok = False
        try:
            record_wav(WAV_PATH, REC_SECONDS)
            ok = True
        except Exception as e:
            show("录音失败", str(e)[:22])
            sleep_ms(2000)
        rgb.write_left(0, 0, 0)
        rgb.write_right(0, 0, 0)

        if ok:
            show("录音完成", "正在发送...", "", "", "")
            try:
                send_wav(WAV_PATH)
                show("已发送", "等待AI回答...", "", "", "")
                rgb.write_left(0, 0, 180)
                rgb.write_right(0, 0, 180)
                kind, txt = wait_reply()
                rgb.write_left(0, 0, 0)
                rgb.write_right(0, 0, 0)
                if kind == "R" and txt:
                    show("AI 回答", "", "", "", "")
                    present(txt)
                    rgb.write_left(0, 120, 0)
                    rgb.write_right(0, 120, 0)
                    speak(txt)
                    rgb.write_left(0, 0, 0)
                    rgb.write_right(0, 0, 0)
                elif kind == "E":
                    show("出错", (txt or "")[:30])
                    sleep_ms(2000)
                else:
                    show("等待超时", "检查电脑端", "serial_bridge", "", "")
                    sleep_ms(2000)
            except Exception as e:
                show("发送异常", str(e)[:26])
                sleep_ms(2000)
            try:
                os.remove(WAV_PATH)
            except Exception:
                pass

        show("AI 学伴就绪", "按A键说话", "B键清屏/打断", "", "")
        sleep_ms(300)

    # ---- B：清屏 ----
    if button.get_b() == 1:
        sleep_ms(260)
        show("已清屏", "按A键说话", "", "", "")
        sleep_ms(300)

    # ---- 长回答滚动 ----
    if len(BUFFER) > 3:
        _roll += 1
        if _roll % 5 == 0:
            shift = (_roll // 5) % len(BUFFER)
            for k in range(3):
                oled.print(1, k + 2, BUFFER[(shift + k) % len(BUFFER)], 1)

    gc.collect()
    sleep_ms(100)
