# -*- coding: utf-8 -*-
"""
决定性对照：用我那套手写代码，在【电脑 IP】上认证
  - 如果成功 -> 说明代码没问题，是板子 IP/MAC 被特殊对待
  - 如果失败 -> 说明代码还有问题
"""
import hashlib
import json
import socket
import sys
import time
import urllib.parse

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S


def http(path, maxlen=2000):
    s = socket.socket()
    s.settimeout(12)
    s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
    s.send(("GET " + path + " HTTP/1.1\r\nHost: " + PORTAL
            + "\r\nConnection: close\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n\r\n").encode())
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


def jof(t):
    a, b = t.find("{"), t.rfind("}")
    if a < 0:
        return None
    try:
        return json.loads(t[a:b + 1])
    except Exception:
        return None


# 取本机 IP
r = http("/cgi-bin/rad_user_info?callback=cb")
j = jof(r)
ip = (j or {}).get("client_ip") or "PC_IP"
print("本机 IP:", ip, " 当前状态:", (j or {}).get("error"))

print()
print("=== 用手写代码在电脑 IP 上认证 ===")
ts = str(int(time.time() * 1000))
r = http("/cgi-bin/get_challenge?callback=cb&username=" + USER + "&ip=" + ip + "&_=" + ts)
j = jof(r)
token = j["challenge"]
hmd5 = hashlib.md5((PWD + token).encode()).hexdigest()
info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, ip)
info_enc = "{SRBX1}" + S.b64(S.xencode(info, token))
chksum = hashlib.sha1((token + USER + token + hmd5 + token + "1" + token + ip
                       + token + "200" + token + "1" + token + info_enc).encode()).hexdigest()
url = ("/cgi-bin/srun_portal?callback=cb&action=login&username=" + USER
       + "&password=" + urllib.parse.quote("{MD5}" + hmd5, safe="")
       + "&os=Windows+10&name=Windows&nas_ip=&double_stack=0"
       + "&chksum=" + chksum + "&info=" + urllib.parse.quote(info_enc, safe="")
       + "&ac_id=1&ip=" + ip + "&n=200&type=1"
       + "&captchaVal=&ap_id=&ap_ip=&mac=&_=" + ts)
r2 = http(url)
j2 = jof(r2)
print("  结果:", j2.get("error") if j2 else r2[-200:])
if j2 and j2.get("error") == "ok":
    print("  *** 成功 ***  说明代码没问题")
else:
    print("  *** 失败 ***  说明代码仍有问题")
    print("  error_msg:", (j2 or {}).get("error_msg"))
