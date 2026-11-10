# -*- coding: utf-8 -*-
"""方向A排查：对比登录成功页 / 检查缺失参数 / 抓真实登录流程"""
import hashlib
import json
import socket
import sys
import time
import urllib.parse

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"
MY_IP = "PC_IP"

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S


def http(path, timeout=12, maxlen=4000, extra=""):
    s = socket.socket()
    s.settimeout(timeout)
    s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
    h = ("GET " + path + " HTTP/1.1\r\nHost: " + PORTAL
         + "\r\nConnection: close\r\nUser-Agent: Mozilla/5.0\r\n" + extra + "\r\n")
    s.send(h.encode())
    buf = b""
    while len(buf) < maxlen:
        try:
            c = s.recv(800)
        except Exception:
            break
        if not c:
            break
        buf += c
    s.close()
    return buf.decode("utf-8", "replace")


def body(t):
    return t.split("\r\n\r\n", 1)[-1] if "\r\n\r\n" in t else t


def jof(t):
    a, b = t.find("{"), t.rfind("}")
    if a < 0:
        return None
    try:
        return json.loads(t[a:b + 1])
    except Exception:
        return None


print("=== 1. 成功页内容（判断会话状态）===")
r = http("/srun_portal_success?ac_id=1&theme=pro", maxlen=6000)
print("  状态:", r.split("\r\n")[0])
p = body(r)
import re
# 提取关键信息
for kw in ("online_ip", "user_name", "user_ip", "CONFIG", "error"):
    for m in re.finditer(kw, p):
        seg = p[max(0, m.start() - 60):m.start() + 160].replace("\n", " ")
        print("  [%s] %s" % (kw, seg[:200]))
        break

print()
print("=== 2. 页面的 CONFIG ===")
i = p.find("var CONFIG")
if i >= 0:
    end = p.find("};", i)
    print("  " + p[i:end + 2][:1200].replace("\n", " "))

print()
print("=== 3. 检查 nas_ip 参数 ===")
# 从 rad_user_info 取 nas 信息
r2 = http("/cgi-bin/rad_user_info?callback=cb", maxlen=4000)
j = jof(r2)
if j:
    print("  当前会话 nas_ip:", j.get("nas_ip", "(无)"))
    print("  user_ip:", j.get("user_ip", "(无)"))
    print("  online_ip:", j.get("online_ip"))
