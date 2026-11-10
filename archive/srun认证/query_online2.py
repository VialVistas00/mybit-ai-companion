# -*- coding: utf-8 -*-
"""打印完整 rad_user_info 原始 JSON"""
import json
import socket
import time

PORTAL = "PORTAL_IP"
MY_IP = "PC_IP"


def http(path, timeout=10, maxlen=4000):
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


ts = str(int(time.time() * 1000))
r = http("/cgi-bin/rad_user_info?callback=cb&ip=" + MY_IP + "&_=" + ts)
body = r.split("\r\n\r\n")[1] if "\r\n\r\n" in r else r
a, b = body.find("{"), body.rfind("}")
obj = json.loads(body[a:b + 1])

print("=== 关键字段 ===")
for k in ("error", "user_name", "user_ip", "domain", "online_ip", "billing_name",
          "group_id", "online_device_total", "add_time", "keepalive_time", "uid"):
    if k in obj:
        print("  %-20s = %r" % (k, obj[k]))

print("\n=== 全部字段名 ===")
print(sorted(obj.keys()))

print("\n=== online_device_detail ===")
d = obj.get("online_device_detail", "")
try:
    print(json.dumps(json.loads(d), ensure_ascii=False, indent=2))
except Exception:
    print(d)
