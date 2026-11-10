# -*- coding: utf-8 -*-
"""查询本机当前的 Portal 在线信息（拿真实登录用户名）"""
import sys
import time
import socket

PORTAL = "PORTAL_IP"
MY_IP = "PC_IP"


def http(path, timeout=10):
    s = socket.socket()
    s.settimeout(timeout)
    s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
    req = ("GET " + path + " HTTP/1.1\r\nHost: " + PORTAL
           + "\r\nConnection: close\r\nUser-Agent: Mozilla/5.0\r\n\r\n")
    s.send(req.encode())
    buf = b""
    while True:
        try:
            c = s.recv(400)
        except Exception:
            break
        if not c:
            break
        buf += c
    s.close()
    return buf.decode("utf-8", "replace")


ts = str(int(time.time() * 1000))
print("=== rad_user_info (本机 %s) ===" % MY_IP)
print(http("/cgi-bin/rad_user_info?callback=cb&ip=" + MY_IP + "&_=" + ts)[:700])

print()
print("=== rad_user_info 不带 ip ===")
print(http("/cgi-bin/rad_user_info?callback=cb&_=" + ts)[:700])
