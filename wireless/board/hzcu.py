# -*- coding: utf_8 -*-
# ============================================================
#   hzcu.py —— 校园网自动认证模块（HZCU / Dr.COM 城市热点）
# ------------------------------------------------------------
#   用法：
#       import hzcu
#       hzcu.ensure(oled_show=True)        # 确保联网，失败返回 False
#       hzcu.status()                      # 返回 (已认证?, IP, 账号)
#       hzcu.logout()                      # 注销
#
#   原理（实测于 2026-11-11）：
#     - 必须连 SSID "HZCU"（不是 HZCU-IPV6，那个是 SRun 体系会被劫持）
#     - 认证服务器 10.69.255.130，Dr.COM 协议，纯明文 GET，无加密
#     - 登录：/drcom/login?DDDDD=账号&upass=密码&0MKKey=123456...
#     - 查状态：/drcom/chkstatus  注销：/drcom/logout
#     - 响应是 GBK 编码且带中文，必须按 bytes 处理，不能 decode('utf-8')
# ============================================================
import network
import socket
import time
import gc

# ---------------- 配置 ----------------
SSID = "HZCU"                 # 必须用这个，不能是 HZCU-IPV6
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"
DRCOM = "10.69.255.130"

CONNECT_TIMEOUT = 25          # 连 Wi-Fi 超时（秒）
REQ_TIMEOUT = 6               # HTTP 请求超时（秒）
# 注：Dr.COM 服务器 10.69.255.130 在部分网络下不响应，
#     默认 12 秒超时会导致界面卡住，改成 6 秒快速失败。


# ---------------- 底层 HTTP ----------------
def _http(host, path, timeout=REQ_TIMEOUT, maxlen=2500):
    """返回原始 bytes（不解码，避免 GBK 中文导致 UnicodeError）"""
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, 80))
        s.send(("GET " + path + " HTTP/1.0\r\nHost: " + host
                + "\r\nConnection: close\r\nUser-Agent: Mozilla/5.0\r\n\r\n").encode())
        buf = b""
        while len(buf) < maxlen:
            try:
                c = s.recv(500)
            except Exception:
                break
            if not c:
                break
            buf += c
        return buf
    except Exception as e:
        return b"ERR:" + str(e).encode()
    finally:
        try:
            s.close()
        except Exception:
            pass


def _field(buf, key):
    """从 JSON bytes 里抠出字段值（字符串或数字），返回 str 或 None"""
    k = b'"' + key.encode() + b'":'
    i = buf.find(k)
    if i < 0:
        return None
    i += len(k)
    if i >= len(buf):
        return None
    if buf[i:i + 1] == b'"':
        j = buf.find(b'"', i + 1)
        if j < 0:
            return None
        try:
            return buf[i + 1:j].decode("utf-8")
        except Exception:
            return buf[i + 1:j].decode("latin-1")
    j = i
    while j < len(buf) and buf[j:j + 1] not in (b",", b"}"):
        j += 1
    try:
        return buf[i:j].decode("latin-1").strip()
    except Exception:
        return None


# ---------------- Wi-Fi ----------------
def wifi_connect(ssid=SSID, timeout=CONNECT_TIMEOUT):
    """连接指定 Wi-Fi，返回 IP 或 None"""
    w = network.WLAN(network.STA_IF)
    if not w.active():
        w.active(True)
        time.sleep(1.0)

    if w.isconnected():
        ap = w.config("essid")
        if ap and ap != ssid:
            # 连的是别的网络，先断开
            w.disconnect()
            time.sleep(1.2)
        else:
            return w.ifconfig()[0]

    for attempt in range(2):
        try:
            w.connect(ssid)
        except Exception:
            pass
        t = time.time()
        while not w.isconnected() and time.time() - t < timeout:
            time.sleep(0.4)
        if w.isconnected():
            return w.ifconfig()[0]
        if attempt == 0:
            w.disconnect()
            time.sleep(1.5)

    return None


# ---------------- Dr.COM ----------------
def check_status():
    """返回 dict: {'online': bool, 'ip': str, 'uid': str} 或 None（连不上服务器）"""
    buf = _http(DRCOM, "/drcom/chkstatus?callback=dr1002&jsVersion=4.1&v=7123&lang=zh")
    if buf.startswith(b"ERR:"):
        return None
    # 被劫持的表现：返回 HTML
    if b"<html" in buf[:400].lower() or b"Authentication is required" in buf:
        return None

    result = _field(buf, "result")
    if result is None:
        return None
    return {
        "online": result == "1",
        "ip": _field(buf, "v46ip"),
        "uid": _field(buf, "uid"),
    }


def login(user=USER, pwd=PWD):
    """登录。返回 (成功?, 说明)"""
    path = ("/drcom/login?callback=dr1003&DDDDD=" + user + "&upass=" + pwd
            + "&0MKKey=123456&R1=0&R2=&R3=0&R6=0&para=00&v6ip=&terminal_type=1"
            + "&lang=zh-cn&jsVersion=4.1&v=4842&lang=zh")
    buf = _http(DRCOM, path, timeout=15)
    if buf.startswith(b"ERR:"):
        return False, "网络不通"
    if b"<html" in buf[:400].lower():
        return False, "被Portal劫持"

    result = _field(buf, "result")
    if result == "1":
        return True, "登录成功"
    msg = _field(buf, "msga") or _field(buf, "msg") or ""
    return False, ("登录失败 " + msg)[:28]


def logout():
    """注销。返回 (成功?, 说明)"""
    buf = _http(DRCOM, "/drcom/logout?callback=dr1006&jsVersion=4.1&v=1949&lang=zh")
    if buf.startswith(b"ERR:"):
        return False, "网络不通"
    result = _field(buf, "result")
    return result == "1", ("注销成功" if result == "1" else "注销失败")


def online_test(host="www.baidu.com", path="/"):
    """外网连通性测试"""
    try:
        s = socket.socket()
        s.settimeout(8)
        s.connect(socket.getaddrinfo(host, 80)[0][4])
        s.send(("GET " + path + " HTTP/1.0\r\nHost: " + host + "\r\n\r\n").encode())
        d = s.recv(100)
        s.close()
        return d.startswith(b"HTTP/")
    except Exception:
        return False


# ---------------- 对外主接口 ----------------
def ensure(show=None, retries=3, verbose=False):
    """
    确保板子联网。返回 True/False。
    show: 可选的显示回调 show(line1, line2, line3, line4, line5)

    ★ 性能关键（实测 2026-11-11）：
        online_test()    ~76 ms    直连百度
        check_status()   ~12000 ms 访问 Dr.COM 服务器会卡到超时
    所以必须【先测外网】，外网通就立刻返回，绝不去碰 check_status。
    只有外网不通时才去查认证状态。
    """
    def say(a="", b="", c="", d="", e=""):
        if show:
            try:
                show(a, b, c, d, e)
            except Exception:
                pass
        if verbose:
            print("[hzcu]", a, b, c)

    gc.collect()

    # 1. 连 Wi-Fi（已连就是 18ms）
    say("连接 " + SSID, "", "", "", "")
    ip = wifi_connect()
    if not ip:
        say("WiFi 连接失败", "请检查热点", "", "", "")
        return False

    # 2. 先测外网 —— 通了就秒返回，不碰 check_status
    if online_test():
        say("联网正常", "IP:" + ip, "", "", "")
        return True

    # 3. 外网不通，才开始认证流程
    say("WiFi 已连", "IP:" + ip, "检测认证...", "", "")

    for attempt in range(retries):
        st = check_status()

        if st is not None and st.get("online"):
            say("已认证但外网不通", "重新登录...", "", "", "")
        else:
            say("正在登录...", "账号:" + USER, "", "", "")

        ok, msg = login()
        if verbose:
            print("[hzcu] login:", ok, msg)

        # 登录后给服务器 2 秒生效
        time.sleep(2)

        if online_test():
            say("认证成功", "账号:" + USER, "IP:" + ip, "", "")
            return True

        say("第 " + str(attempt + 1) + " 次失败", "重试中...", "", "", "")
        time.sleep(1)

    say("联网失败", "请检查账号/网络", "", "", "")
    return False


def status():
    """返回 (在线?, IP, 账号)"""
    st = check_status()
    if not st:
        return False, None, None
    return st["online"], st["ip"], st["uid"]


# ---------------- 自测 ----------------
if __name__ == "__main__":
    print("=== HZCU 自动认证自测 ===")
    ok = ensure(verbose=True)
    print("ensure:", ok)
    print("status:", status())
