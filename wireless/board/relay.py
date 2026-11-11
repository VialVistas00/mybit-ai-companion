# -*- coding: utf_8 -*-
# ============================================================
#   relay.py —— 板子端：访问中转服务（纯 HTTP，无 TLS）
# ------------------------------------------------------------
#   比直连 DeepSeek 好在：
#     - 纯 HTTP，不耗 TLS 内存（板子 TLS 会 ENOMEM）
#     - 语音识别和 LLM 都在服务器上跑（4090 + 大模型）
#     - 板子只负责录音/发送/显示/播报
#
#   用法：
#       import relay
#       relay.ask_wav('ask.wav')        # 上传录音，返回 (提问, 回答, 错误)
#       relay.ask_text('你好')          # 文本提问
#       relay.ping()                    # 心跳
# ============================================================
import socket
import time
import gc

# ---------------- 配置 ----------------
SRV_HOST = "10.61.190.8"
SRV_PORT = 8091
TIMEOUT = 60


# ---------------- 底层 HTTP ----------------
def _connect(timeout=TIMEOUT):
    s = socket.socket()
    s.settimeout(timeout)
    s.connect((SRV_HOST, SRV_PORT))
    return s


def _read_resp(s, maxlen=6000, timeout=90):
    """
    读 HTTP 响应（HTTP/1.0 + Connection: close，读到对端关闭为止）。

    ★ 实测坑（2026-11-11）：原来的实现用 s.recv() 循环，但 MicroPython 的
      recv 在数据未到达时会立刻抛异常/返回空，导致提前退出、拿到空响应。
      实测上传只用 363ms 就返回「没听清」，而服务器实际要 2 秒。

      修复：用 settimeout 明确超时，把"暂时没数据"和"连接关闭"区分开。
      正常关闭 -> b''，超时 -> 抛 OSError 但已有数据照样返回。
    """
    try:
        s.settimeout(timeout)
    except Exception:
        pass

    buf = b""
    idle = 0
    while len(buf) < maxlen:
        try:
            c = s.read(512) if hasattr(s, "read") else s.recv(512)
        except Exception:
            # 超时或异常：只要已经收到数据就返回，否则继续小等一下
            idle += 1
            if buf and idle >= 2:
                break
            if idle >= 6:
                break
            time.sleep(0.2)
            continue
        if not c:
            # 对端正常关闭
            break
        idle = 0
        buf += c

    idx = buf.find(b"\r\n\r\n")
    if idx < 0:
        return None, buf
    head = buf[:idx]
    payload = buf[idx + 4:]

    # 按 Content-Length 精确截取（Flask 总会给）
    cl = None
    h = head.lower()
    k = h.find(b"content-length:")
    if k >= 0:
        e = h.find(b"\r\n", k)
        try:
            cl = int(h[k + 15:e].strip())
        except Exception:
            cl = None
    if cl is not None and len(payload) >= cl:
        payload = payload[:cl]

    # chunked
    if b"chunked" in h:
        out = b""
        p = payload
        while True:
            e = p.find(b"\r\n")
            if e < 0:
                break
            try:
                size = int(p[:e].split(b";")[0], 16)
            except Exception:
                break
            if size == 0:
                break
            out += p[e + 2:e + 2 + size]
            p = p[e + 2 + size + 2:]
        payload = out

    del buf
    del head
    return None, payload


def _json_str(raw, key):
    """从 bytes 里抠字符串字段（不解码整个 JSON）"""
    k = b'"' + key.encode() + b'":"'
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
                    out += chr(code).encode("utf-8") if code > 0 else b"?"
                except Exception:
                    out += b"?"
                p += 6
                continue
            if nxt == b"n" or nxt == b"t":
                out += b" "
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
        return out.decode("latin-1")


def _json_int(raw, key):
    k = b'"' + key.encode() + b'":'
    i = raw.find(k)
    if i < 0:
        return None
    i += len(k)
    j = i
    while j < len(raw) and (48 <= raw[j] <= 57 or raw[j] == 45):
        j += 1
    try:
        return int(raw[i:j])
    except Exception:
        return None


# ---------------- 对外接口 ----------------
def ping():
    """心跳，返回 True/False"""
    try:
        s = _connect(10)
        s.send(("GET /api/ping HTTP/1.0\r\nHost: " + SRV_HOST
                + "\r\nConnection: close\r\n\r\n").encode())
        head, payload = _read_resp(s, 800)
        s.close()
        return payload is not None and b'"ok":true' in payload.replace(b" ", b"")
    except Exception:
        return False


def ask_text(q):
    """文本提问 -> (回答, 错误)"""
    body = ('{"q":"' + q.replace('"', '\\"') + '"}').encode("utf-8")
    s = None
    try:
        s = _connect()
        req = ("POST /api/ask_text HTTP/1.0\r\nHost: " + SRV_HOST
               + "\r\nContent-Type: application/json"
               + "\r\nContent-Length: " + str(len(body))
               + "\r\nConnection: close\r\n\r\n")
        s.send(req.encode())
        s.send(body)
        head, payload = _read_resp(s, 4000)
    except Exception as e:
        cleanup()
        return None, "连接失败:" + str(e)[:24]
    finally:
        try:
            if s:
                s.close()
        except Exception:
            pass
        del body

    if payload is None:
        cleanup()
        return None, "无响应"
    flat = payload.replace(b" ", b"")
    ok = b'"ok":true' in flat
    del flat
    if not ok:
        err = _json_str(payload, "error") or "未知错误"
        del payload
        cleanup()
        return None, err[:30]
    a = _json_str(payload, "a")
    del payload
    cleanup()
    return a, None


def cleanup():
    """强制清理内存碎片 —— 每次问答后必须调用，否则录音会 MemoryError"""
    gc.collect()
    gc.collect()
    gc.collect()


def ask_wav(path, progress=None):
    """
    上传 WAV 录音 -> (提问, 回答, 错误)
    progress: 可选回调 progress(已发字节, 总字节)

    ★ 两个实测坑（2026-11-11）：
      1. f.read(512) 返回长度不定，49196 字节文件只发出 44 字节就 EOF，
         导致 Content-Length 与实际不符，服务器死等 -> 表现为「70% 出错」。
      2. 整块读入 32KB 到内存会 MemoryError（板子堆不够），
         所以必须【边读边发】，不能先全读进 RAM。

      方案：用 os.stat 拿准确大小做 Content-Length，然后分块读-发-放。
    """
    s = None
    f = None
    try:
        try:
            size = _fsize(path)
        except Exception:
            return None, None, "文件不存在"
        if size < 1000:
            return None, None, "录音为空"

        # ★ 弱网重试：整次上传失败后最多重试 3 轮
        last_err = None
        for attempt in range(3):
            if attempt > 0:
                time.sleep(1)
                gc.collect()

            try:
                s = _connect(60)
            except Exception as e:
                last_err = "连接失败:" + str(e)[:20]
                continue

            ok_head = False
            try:
                req = ("POST /api/ask HTTP/1.0\r\nHost: " + SRV_HOST
                       + "\r\nContent-Type: audio/wav"
                       + "\r\nContent-Length: " + str(size)
                       + "\r\nConnection: close\r\n\r\n")
                s.send(req.encode())
                ok_head = True
            except Exception as e:
                last_err = "发头失败:" + str(e)[:16]

            if not ok_head:
                try:
                    s.close()
                except Exception:
                    pass
                s = None
                continue

            # ---- 边读边发，块小、重试多，适应弱网 ----
            try:
                f = open(path, "rb")
            except Exception:
                try:
                    s.close()
                except Exception:
                    pass
                s = None
                return None, None, "打不开文件"

            sent = 0
            CH = 128
            retry = 0
            aborted = False
            while sent < size:
                try:
                    piece = f.read(CH)
                except Exception:
                    aborted = True
                    break
                if not piece:
                    break
                try:
                    n = s.send(piece)
                except OSError as e:
                    retry += 1
                    if retry > 60:
                        last_err = "发送失败:" + str(e)[:16]
                        aborted = True
                        break
                    time.sleep_ms(120)
                    continue
                retry = 0
                if not n:
                    aborted = True
                    break
                sent += n
                del piece
                if progress:
                    try:
                        progress(sent, size)
                    except Exception:
                        pass

            try:
                f.close()
            except Exception:
                pass
            f = None

            if aborted or sent < size:
                if not last_err:
                    last_err = "上传中断 %d/%d" % (sent, size)
                try:
                    s.close()
                except Exception:
                    pass
                s = None
                continue

            # ---- 读响应 ----
            try:
                head, payload = _read_resp(s, 6000, 60)
            except Exception as e:
                last_err = "读响应失败:" + str(e)[:18]
                payload = None
            finally:
                try:
                    if s:
                        s.close()
                except Exception:
                    pass
                s = None

            if payload is None:
                last_err = "无响应"
                continue

            flat = payload.replace(b" ", b"")
            okflag = b'"ok":true' in flat
            del flat

            if not okflag:
                err = _json_str(payload, "error") or "未知"
                del payload
                cleanup()
                if "empty" in err:
                    return None, None, "没听清"
                return None, None, err[:30]

            q = _json_str(payload, "q")
            a = _json_str(payload, "a")
            del payload
            cleanup()
            return q, a, None

        cleanup()
        return None, None, last_err or "上传失败"

    except MemoryError:
        cleanup()
        return None, None, "内存不足"
    except Exception as e:
        cleanup()
        return None, None, "异常:" + str(e)[:22]
    finally:
        try:
            if f:
                f.close()
        except Exception:
            pass
        try:
            if s:
                s.close()
        except Exception:
            pass


def fetch_reply(since=0):
    """取消息队列，返回 (最新seq, [文本列表])"""
    try:
        s = _connect(15)
        s.send(("GET /api/reply?since=" + str(since) + " HTTP/1.0\r\nHost: " + SRV_HOST
                + "\r\nConnection: close\r\n\r\n").encode())
        head, payload = _read_resp(s, 3000, 15)
        s.close()
    except Exception:
        return since, []

    if payload is None:
        return since, []

    seq = _json_int(payload, "seq")
    cnt = _json_int(payload, "count")
    texts = []
    if cnt and cnt > 0:
        t = _json_str(payload, "text")
        if t:
            texts.append(t)
    return (seq if seq is not None else since), texts


def fetch_task_result(since=0):
    """
    取电脑执行结果，返回 [(task_id, ok, output), ...]
    只取执行成功的，失败的在 ok=False
    """
    try:
        s = _connect(15)
        s.send(("GET /api/task/done?since=" + str(since)
                + " HTTP/1.0\r\nHost: " + SRV_HOST
                + "\r\nConnection: close\r\n\r\n").encode())
        head, payload = _read_resp(s, 3500, 15)
        s.close()
    except Exception:
        return []

    if payload is None:
        return []

    out = []
    # 逐个抠出 "output":"..." 和 "ok":true/false
    pos = 0
    while True:
        i = payload.find(b'"output":"', pos)
        if i < 0:
            break
        pos = i + 10
        # 找 ok 值（在前面的字段里）
        okv = True
        j = payload.rfind(b'"ok":', max(0, i - 300), i)
        if j >= 0:
            seg = payload[j + 5:j + 10]
            okv = b"true" in seg
        # 抠 output 字符串
        k = payload.find(b'"', i)
        if k < 0:
            break
        raw = payload[i:k]
        try:
            text = raw.decode("utf-8")
        except Exception:
            text = raw.decode("latin-1")
        # 简单反转义
        text = text.replace("\\n", " ").replace("\\r", "")
        text = text.replace('\\"', '"').replace("\\\\", "\\")
        out.append((None, okv, text[:200]))
        pos = k + 1
    return out[-5:]


def check_task_status():
    """查服务器状态：返回 (待执行数, 已完成数) 或 (None, None)"""
    try:
        s = _connect(10)
        s.send(("GET /api/ping HTTP/1.0\r\nHost: " + SRV_HOST
                + "\r\nConnection: close\r\n\r\n").encode())
        head, payload = _read_resp(s, 900, 10)
        s.close()
    except Exception:
        return None, None
    if payload is None:
        return None, None
    return _json_int(payload, "pending"), _json_int(payload, "seq")


def _fsize(path):
    import os
    return os.stat(path)[6]
