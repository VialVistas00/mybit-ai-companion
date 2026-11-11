# -*- coding: utf_8 -*-
# ============================================================
#   ai_voice.py —— AI 学伴 · 无线语音版
# ------------------------------------------------------------
#   板子完全独立：自己联网、自己录音、自己上传、自己显示
#
#   链路：
#     板子 --WiFi(HZCU)--> 10.61.190.8:8091 --HTTPS--> DeepSeek
#                           中转服务（whisper GPU 识别）
#
#   操作：
#     A 键  录音 3 秒 -> 上传 -> 显示 AI 回答
#     B 键  清屏 / 打断
#
#   启动流程：
#     连 WiFi(18ms) -> 测外网(76ms) -> 通过就绪
#     不通才走认证（避免 check_status 的 12 秒卡顿）
# ==========================================================
from npython import *
import gc
import time
import hzcu
import relay

try:
    import audio as _AUDIO
    _REC = "audio"
except ImportError:
    _AUDIO = None
    _REC = None

REC_SECONDS = 2          # ★ 实测：3 秒必 MemoryError，2 秒稳定成功（2026-11-11）
                         #   3 秒 WAV = 49196 字节，需要约 49KB 连续块
                         #   2 秒 WAV = 32812 字节，只要 32KB，稳过
                         #   板子堆总量 111KB，但 import 后可用约 75KB，
                         #   再被 socket/显示缓冲分割，3 秒就拿不到连续块了。
WAV_PATH = "ask.wav"

BUFFER = []
_roll = 0
_UART1 = None


# ---------------- Wi-Fi 质量 ----------------
def wifi_rssi():
    try:
        import network
        w = network.WLAN(network.STA_IF)
        if not w.isconnected():
            return None
        return w.status("rssi")
    except Exception:
        return None


def signal_hint(rssi):
    """返回信号等级提示"""
    if rssi is None:
        return "断开"
    if rssi >= -65:
        return "强"
    if rssi >= -75:
        return "中"
    if rssi >= -82:
        return "弱"
    return "极弱"


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


# ---------------- 语音播报（可选）----------------
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


# ---------------- 录音 ----------------
_REC_OPS = [0]          # 录音次数计数


def deep_clean():
    """
    深度堆整理。实测（2026-11-11）：
      - audio.recorder_init 只占 64 字节，record 占 208 字节
      - 录音失败不是总量问题，是堆被 import 和问答打散后拿不到 4KB 连续块
      - 冷启动后录音 100% 成功；跑过多轮测试后失败
    所以要主动整理：清空显示缓冲、释放字符串、反复 gc
    """
    global BUFFER, _roll
    try:
        BUFFER.clear()
    except Exception:
        pass
    _roll = 0
    for _ in range(6):
        gc.collect()


def record(path, seconds):
    """
    录音。带自动降级：指定秒数失败就按 2 秒再试。

    ★ 实测（2026-11-11）：
        3 秒 -> MemoryError（需要 49KB 连续块，拿不到）
        2 秒 -> 稳定成功（只要 32KB）
      所以默认 2 秒，且失败时自动降级。
    """
    global BUFFER, _roll

    if _REC != "audio":
        raise RuntimeError("无录音模块")

    # 候选时长：先按要求，再降级
    candidates = [seconds]
    for d in (2, 1):
        if d < seconds and d not in candidates:
            candidates.append(d)

    last_err = None
    for secs in candidates:
        for attempt in range(2):
            # 逐级加强清理
            try:
                BUFFER.clear()
            except Exception:
                pass
            _roll = 0
            levels = 6 if attempt == 0 else 12
            for _ in range(levels):
                gc.collect()

            if attempt >= 1:
                try:
                    oled.fill(0)
                    oled.show()
                except Exception:
                    pass
                for _ in range(4):
                    gc.collect()

            try:
                try:
                    os.remove(path)
                except Exception:
                    pass
                _AUDIO.recorder_init()
                time.sleep_ms(250)
                gc.collect()
                _AUDIO.record(path, secs)
                try:
                    _AUDIO.recorder_deinit()
                except Exception:
                    pass
                # 验证确实录到了数据（空文件就是失败）
                sz = os.stat(path)[6]
                if sz < 1000:
                    last_err = "录音为空"
                    continue
                _REC_OPS[0] += 1
                return secs
            except MemoryError:
                last_err = "内存不足"
                try:
                    _AUDIO.recorder_deinit()
                except Exception:
                    pass
                time.sleep_ms(600)
            except Exception as e:
                last_err = str(e)[:20]
                try:
                    _AUDIO.recorder_deinit()
                except Exception:
                    pass
                time.sleep_ms(400)

    raise RuntimeError(last_err or "录音失败")


def _wait_task_result(timeout_ms=8000):
    """
    等电脑执行结果。电脑端每 1.5 秒轮询一次，所以最多等 8 秒。
    拿到就显示+播报，返回 True。
    """
    t0 = time.ticks_ms()
    while time.ticks_ms() - t0 < timeout_ms:
        try:
            results = relay.fetch_task_result()
        except Exception:
            results = []
        if results:
            for _tid, ok, text in results:
                head = "执行成功" if ok else "执行失败"
                show(head, text[:20], text[20:40], text[40:60], "")
                present((head + "：" + text))
                speak(head + "，" + text)
                time.sleep_ms(300)
            return True
        time.sleep_ms(600)
        gc.collect()
    return False


# ---------------- 主程序 ----------------
oled.fill(0)
show("AI 学伴", "启动中...")
rgb.write_left(0, 0, 0)
rgb.write_right(0, 0, 0)

# 联网（内部先测外网，快）
if not hzcu.ensure(show=show):
    show("联网失败", "检查 HZCU", "", "", "")
    rgb.write_left(255, 0, 0)
    rgb.write_right(255, 0, 0)
    while True:
        if button.get_b() == 1:
            time.sleep_ms(300)
            hzcu.ensure(show=show)
        time.sleep_ms(100)

ip = hzcu.wifi_connect() or "?"
if not ip:
    ip = "?"

# 检查中转服务
show("已联网", "IP:" + ip, "连接中转服务...")
if not relay.ping():
    show("中转服务不通", relay.SRV_HOST, "", "按B重试")
    rgb.write_left(255, 128, 0)
    rgb.write_right(255, 128, 0)

net_ok = True


def show_ready():
    """刷新就绪界面（带信号强度）"""
    r = wifi_rssi()
    line3 = "按A键说话"
    if r is not None:
        line3 = "按A键说话 信号" + signal_hint(r)
    show("AI 学伴就绪", "IP:" + ip, line3, "", "")


show_ready()
rgb.write_left(0, 180, 0)
rgb.write_right(0, 180, 0)

while True:
    # ---- A 键：语音提问 ----
    if button.get_a() == 1:
        time.sleep_ms(260)

        if _REC is None:
            show("无录音模块", "", "", "", "")
            time.sleep_ms(2000)
            show_ready()
            continue

        # 录音前先深度整理堆（关键：否则 MemoryError）
        show("请说话...", "", "", "", "整理内存")
        deep_clean()

        show("请说话...", "", "", "录音%d秒" % REC_SECONDS, "")
        rgb.write_left(200, 0, 0)
        rgb.write_right(200, 0, 0)
        ok = False
        used_secs = 0
        try:
            used_secs = record(WAV_PATH, REC_SECONDS)
            ok = True
        except Exception as e:
            show("录音失败", str(e)[:22], "按A重试", "", "")
            time.sleep_ms(2000)
        rgb.write_left(0, 0, 0)
        rgb.write_right(0, 0, 0)

        if ok:
            # 上传
            show("录音完成", "上传中...", "", "", "")
            rgb.write_left(0, 0, 200)
            rgb.write_right(0, 0, 200)

            def prog(sent, total):
                pct = sent * 100 // total
                oled.print(1, 4, "上传 %d%%" % pct, 1)

            q, a, err = relay.ask_wav(WAV_PATH, progress=prog)
            rgb.write_left(0, 0, 0)
            rgb.write_right(0, 0, 0)

            try:
                os.remove(WAV_PATH)
            except Exception:
                pass

            if err:
                # 弱网提示
                r = wifi_rssi()
                if "发送失败" in err or "上传中断" in err or "无响应" in err:
                    show("弱网中断", "信号:%s(%d)" % (signal_hint(r), r if r else 0),
                         "靠近路由器", "再按A重试", "")
                elif "连接失败" in err:
                    show("网络断开", "正在重连...", "", "", "")
                    hzcu.ensure(show=show)
                else:
                    show("出错", err[:28], "", "", "")
                time.sleep_ms(2500)
                del err
            else:
                show("你问:", (q or "")[:20], "AI 回答:", "", "")
                present(a or "")
                rgb.write_left(0, 180, 0)
                rgb.write_right(0, 180, 0)
                speak(a or "")
                rgb.write_left(0, 0, 0)
                rgb.write_right(0, 0, 0)

                # ---- 等电脑执行结果（最多 8 秒）----
                got = _wait_task_result()

                del q
                del a
                gc.collect()

        relay.cleanup()
        show_ready()
        time.sleep_ms(300)

    # ---- B 键：清屏 / 重连 ----
    if button.get_b() == 1:
        time.sleep_ms(260)
        show_ready()
        if not relay.ping():
            show("重连中转...", "", "", "", "")
            hzcu.ensure(show=show)
            if relay.ping():
                show_ready()
            else:
                show("中转仍不通", relay.SRV_HOST, "", "", "")
        time.sleep_ms(500)

    # ---- 长回答滚动 ----
    if len(BUFFER) > 3:
        _roll += 1
        if _roll % 6 == 0:
            shift = (_roll // 6) % len(BUFFER)
            for k in range(3):
                oled.print(1, k + 2, BUFFER[(shift + k) % len(BUFFER)], 1)

    gc.collect()
    time.sleep_ms(100)
