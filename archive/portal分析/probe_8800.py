# -*- coding: utf-8 -*-
"""在 8800 HTTPS 上找登录接口"""
import json
import socket
import ssl
import time
import urllib.parse

HOST = "PORTAL_IP"
PORT = 8800


def https(path, timeout=12, maxlen=8000):
    s = socket.socket()
    s.settimeout(timeout)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    s.connect(socket.getaddrinfo(HOST, PORT)[0][4])
    s = ctx.wrap_socket(s, server_hostname=HOST)
    s.send(("GET " + path + " HTTP/1.1\r\nHost: " + HOST + ":" + str(PORT)
            + "\r\nConnection: close\r\nUser-Agent: Mozilla/5.0\r\n\r\n").encode())
    buf = b""
    while len(buf) < maxlen:
        try:
            c = s.recv(1000)
        except Exception:
            break
        if not c:
            break
        buf += c
    s.close()
    return buf.decode("utf-8", "replace", )


def body(t):
    return t.split("\r\n\r\n", 1)[-1] if "\r\n\r\n" in t else t


print("=== 1. 8800 根路径（找入口）===")
p = body(https("/", maxlen=4000))
print(p[:600])
print()
print("--- 页面里的链接/脚本 ---")
for line in p.split("\n"):
    ln = line.strip()
    if "src=" in ln or "href=" in ln or "location" in ln:
        print("  " + ln[:200])

print()
print("=== 2. 常见 API 路径探测 ===")
PATHS = [
    "/cgi-bin/get_challenge?callback=cb&username=YOUR_ACCOUNT&ip=PC_IP&_=" + str(int(time.time() * 1000)),
    "/cgi-bin/rad_user_info?callback=cb",
    "/api/get_challenge",
    "/srun_portal_pc?ac_id=1",
    "/index.html",
    "/static/themes/pro/js/Portal.js",
]
for pth in PATHS:
    try:
        r = https(pth, maxlen=1200)
        status = r.split("\r\n")[0]
        b = body(r)
        ctype = ""
        for line in r.split("\r\n"):
            if line.lower().startswith("content-type"):
                ctype = line
        print("  %-40s %s | %s" % (pth.split("?")[0], status[:24], ctype[:40]))
        if "json" in ctype.lower():
            print("       ", b[:200])
    except Exception as e:
        print("  %-40s ERR %s" % (pth.split("?")[0], str(e)[:40]))
