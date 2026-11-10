# -*- coding: utf-8 -*-
"""补全所有参数：nas_ip / ap_id / mac / user_ip 等，逐个试"""
import hashlib
import json
import socket
import sys
import time
import urllib.parse

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"
IP = "PC_IP"
MAC = "00-00-00-00-00-00"

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S


def http(path, maxlen=1500):
    s = socket.socket()
    s.settimeout(12)
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


def jof(t):
    a, b = t.find("{"), t.rfind("}")
    if a < 0:
        return None
    try:
        return json.loads(t[a:b + 1])
    except Exception:
        return None


def attempt(user, pwd, extra_params, info_extra, label):
    ts = str(int(time.time() * 1000))
    r = http("/cgi-bin/get_challenge?callback=cb&username=" + urllib.parse.quote(user)
             + "&ip=" + IP + "&_=" + ts)
    j = jof(r)
    if not j or "challenge" not in j:
        return "challenge失败"
    token = j["challenge"]
    hmd5 = hashlib.md5((pwd + token).encode()).hexdigest()
    info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"%s}' % (
        user, pwd, IP, info_extra)
    info_enc = "{SRBX1}" + S.b64(S.xencode(info, token))
    chksum = hashlib.sha1((token + user + token + hmd5 + token + "1" + token + IP
                           + token + "200" + token + "1" + token + info_enc).encode()).hexdigest()
    url = ("/cgi-bin/srun_portal?callback=cb&action=login&username=" + urllib.parse.quote(user)
           + "&password=" + urllib.parse.quote("{MD5}" + hmd5, safe="")
           + "&ac_id=1&ip=" + IP + "&chksum=" + chksum
           + "&info=" + urllib.parse.quote(info_enc, safe="")
           + "&n=200&type=1&os=Windows&name=Windows&double_stack=0" + extra_params + "&_=" + ts)
    r2 = http(url)
    j2 = jof(r2)
    if not j2:
        return "空响应"
    return "%s | %s" % (j2.get("error"), j2.get("error_msg") or "")


CASES = [
    ("基础", "", ""),
    ("+mac", "&mac=" + MAC, ',"mac":"%s"' % MAC),
    ("+nas_ip", "&nas_ip=CAMPUS_GW", ',"nas_ip":"CAMPUS_GW"'),
    ("+nas+mac", "&nas_ip=CAMPUS_GW&mac=" + MAC, ',"nas_ip":"CAMPUS_GW","mac":"%s"' % MAC),
    ("+ap_id", "&ap_id=1", ',"ap_id":"1"'),
    ("type=3", "", ""),
]

print("参数补全测试：")
print("-" * 70)
for label, ep, ie in CASES:
    try:
        r = attempt(USER, PWD, ep, ie, label)
    except Exception as e:
        r = "EXC " + str(e)[:40]
    print("  %-14s -> %s" % (label, r))
    time.sleep(1.2)
