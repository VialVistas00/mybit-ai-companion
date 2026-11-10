# -*- coding: utf-8 -*-
"""打印 Portal 完整 CONFIG 配置块"""
import socket


PORTAL = "PORTAL_IP"


def http(path, timeout=10, maxlen=12000):
    s = socket.socket()
    s.settimeout(timeout)
    s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
    s.send(("GET " + path + " HTTP/1.1\r\nHost: " + PORTAL
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
    return buf.decode("utf-8", "replace")


body = http("/srun_portal_pc?ac_id=1&theme=pro")
body = body.split("\r\n\r\n", 1)[-1] if "\r\n\r\n" in body else body

i = body.find("var CONFIG")
if i >= 0:
    seg = body[i:i + 3000]
    end = seg.find("};")
    print(seg[:end + 2] if end > 0 else seg)
else:
    print("未找到 CONFIG")
