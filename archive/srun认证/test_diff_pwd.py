# -*- coding: utf-8 -*-
"""决策性实验：对比正确密码 vs 错误密码，看错误码是否不同"""
import hashlib
import json
import socket
import sys
import time
import urllib.parse

PORTAL = "PORTAL_IP"
MY_IP = "PC_IP"
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


def try_login(user, pwd):
    ts = str(int(time.time() * 1000))
    r = http("/cgi-bin/get_challenge?callback=cb&username=" + urllib.parse.quote(user)
             + "&ip=" + MY_IP + "&_=" + ts)
    j = jof(r)
    if not j or "challenge" not in j:
        return "challenge失败"
    token = j["challenge"]
    hmd5 = hashlib.md5((pwd + token).encode()).hexdigest()
    info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (user, pwd, MY_IP)
    info_enc = "{SRBX1}" + S.b64(S.xencode(info, token))
    chksum = hashlib.sha1((token + user + token + hmd5 + token + "1" + token + MY_IP
                           + token + "200" + token + "1" + token + info_enc).encode()).hexdigest()
    url = ("/cgi-bin/srun_portal?callback=cb&action=login&username=" + urllib.parse.quote(user)
           + "&password=" + urllib.parse.quote("{MD5}" + hmd5, safe="")
           + "&ac_id=1&ip=" + MY_IP + "&chksum=" + chksum
           + "&info=" + urllib.parse.quote(info_enc, safe="")
           + "&n=200&type=1&os=Windows&name=Windows&double_stack=0&_=" + ts)
    r2 = http(url)
    j2 = jof(r2)
    if not j2:
        return "空响应"
    return "%s / %s" % (j2.get("error"), j2.get("error_msg", ""))


CASES = [
    ("YOUR_STUDENT_ID", "YOUR_PASSWORD", "正确密码"),
    ("YOUR_STUDENT_ID", "wrongpass123", "故意错误密码"),
    ("YOUR_STUDENT_ID", "", "空密码"),
    ("nonexistent_user_9999", "YOUR_PASSWORD", "不存在的账号"),
    ("YOUR_ACCOUNT", "YOUR_PASSWORD", "旧账号 YOUR_ACCOUNT"),
]

print("账号密码对照实验：")
print("-" * 66)
for user, pwd, label in CASES:
    try:
        r = try_login(user, pwd)
    except Exception as e:
        r = "EXC " + str(e)[:40]
    print("  %-20s %-14s -> %s" % (user[:20], label, r))
    time.sleep(1.2)
