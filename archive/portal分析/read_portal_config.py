# -*- coding: utf-8 -*-
"""读取 Portal 的配置接口，看认证域/账号规则"""
import json
import socket
import time
import urllib.parse


PORTAL = "PORTAL_IP"


def http(path, timeout=10, maxlen=6000):
    s = socket.socket()
    s.settimeout(timeout)
    s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
    s.send(("GET " + path + " HTTP/1.1\r\nHost: " + PORTAL
            + "\r\nConnection: close\r\nUser-Agent: Mozilla/5.0\r\n\r\n").encode())
    buf = b""
    while len(buf) < maxlen:
        try:
            c = s.recv(600)
        except Exception:
            break
        if not c:
            break
        buf += c
    s.close()
    return buf.decode("utf-8", "replace")


def body(t):
    return t.split("\r\n\r\n", 1)[-1] if "\r\n\r\n" in t else t


print("=== 1. 主页面里的 CREATER 配置 ===")
page = body(http("/srun_portal_pc?ac_id=1&theme=pro"))
found = False
for line in page.split("\n"):
    ln = line.strip()
    if any(k in ln for k in ("CREATER", "var ", "CONFIG", "domain", "acid", "ssid")):
        if len(ln) < 400:
            print("  " + ln[:380])
            found = True
if not found:
    print("  (无)")

print()
print("=== 2. 找 js 里的配置文件 ===")
for path in ("/static/themes/pro/js/creater.js?v=a32e00343444a19a",):
    t = body(http(path, maxlen=4000))
    print("  " + path)
    for ln in t.split("\n"):
        if ln.strip():
            print("    " + ln.strip()[:300])
