# -*- coding: utf-8 -*-
"""测试 MAC 认证：板子用自己的 MAC 走 mac 域认证"""
import hashlib
import json
import socket
import sys
import time
import urllib.parse

PORTAL = "PORTAL_IP"
BOARD_IP = "BOARD_IP"
BOARD_MAC = "00:00:00:00:00:00"

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S


def http(path, timeout=12, maxlen=2000):
    s = socket.socket()
    s.settimeout(timeout)
    s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
    s.send(("GET " + path + " HTTP/1.1\r\nHost: " + PORTAL
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
    s.close()
    return buf.decode("utf-8", "replace")


def jof(t):
    a, b = t.find("{"), t.rfind("}")
    if a < 0:
        return None
    try:
        return json.loads(t[a:b + 1])
    except Exception:
        return None


print("=== 1. 板子 MAC 是否已在系统里（按 MAC 查在线）===")
ts = str(int(time.time() * 1000))
r = http("/cgi-bin/rad_user_info?callback=cb&user_mac=" + BOARD_MAC + "&ip=" + BOARD_IP + "&_=" + ts)
j = jof(r)
print("  ", (j or {}).get("error"), "/", (j or {}).get("error_msg", ""))

print()
print("=== 2. 尝试 MAC 认证接口 ===")
# SRun 的 MAC 快捷认证：type=5 或 action=login 带 mac 参数
for extra in ("&mac=" + BOARD_MAC, "&mac=" + BOARD_MAC.replace(":", "") + "&nas_ip=CAMPUS_GW"):
    url = ("/cgi-bin/srun_portal?callback=cb&action=login&username=YOUR_ACCOUNT"
           + "&ac_id=1&ip=" + BOARD_IP + extra + "&n=200&type=5&os=Windows&name=Windows&_=" + ts)
    resp = http(url, maxlen=1200)
    jj = jof(resp)
    print("  type=5 %-40s -> %s" % (extra[:38], (jj or {}).get("error") if jj else resp[:80]))

print()
print("=== 3. 检查板子是否已能出网（可能已自动认到）===")
try:
    s = socket.socket()
    s.settimeout(5)
    s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
    s.send(b"GET http://connect.rom.miui.com/generate_204 HTTP/1.0\r\nHost: connect.rom.miui.com\r\n\r\n")
    d = s.recv(300)
    s.close()
    print("  ", d.decode("utf-8", "replace")[:200])
except Exception as e:
    print("  ", e)
