# -*- coding: utf-8 -*-
"""分析 Portal 页面与请求头要求"""
import re
import socket
import time

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
IP = "PC_IP"


def get(path, headers=""):
    s = socket.socket()
    s.settimeout(8)
    s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
    s.send(("GET " + path + " HTTP/1.1\r\nHost: " + PORTAL
            + "\r\nConnection: close\r\n" + headers + "\r\n").encode())
    b = b""
    while True:
        try:
            c = s.recv(1000)
        except Exception:
            break
        if not c:
            break
        b += c
    s.close()
    return b.decode("utf-8", "replace")


def body(t):
    return t.split("\r\n\r\n", 1)[-1] if "\r\n\r\n" in t else t


print("=== 1. Portal 页加载的 JS ===")
page = get("/srun_portal_pc?ac_id=1&theme=pro")
for m in re.finditer(r'<script[^>]*src=["\']([^"\']+)', page):
    print("  " + m.group(1)[:110])

print()
print("=== 2. 页面里的 form / input ===")
for m in re.finditer(r"<form[^>]*>", page):
    print("  FORM: " + m.group(0)[:180])
for m in re.finditer(r"<input[^>]*>", page):
    print("  INPUT: " + m.group(0)[:180])

print()
ts = str(int(time.time() * 1000))
p = "/cgi-bin/get_challenge?callback=cb&username=" + USER + "&ip=" + IP + "&_=" + ts

print("=== 3. get_challenge 无 Referer ===")
print("  " + body(get(p))[:200])

print()
print("=== 4. get_challenge 带 Referer + X-Requested-With ===")
h = ("Referer: http://" + PORTAL + "/srun_portal_pc?ac_id=1&theme=pro\r\n"
     "X-Requested-With: XMLHttpRequest\r\n"
     "Accept: */*\r\n")
print("  " + body(get(p, h))[:200])

print()
print("=== 5. 试不带 callback（纯 JSON 接口）===")
p2 = p.replace("callback=cb&", "")
print("  " + body(get(p2, h))[:300])
