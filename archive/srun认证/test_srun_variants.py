# -*- coding: utf-8 -*-
"""SRun auth_info_error 排查：试 username 后缀、ip 参数、info 结构"""
import base64
import hashlib
import json
import socket
import sys
import time
import urllib.parse

PORTAL = "PORTAL_IP"
USER = "YOUR_ACCOUNT"
PWD = "YOUR_PASSWORD"
MY_IP = "PC_IP"

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S


def http(path, timeout=12, maxlen=2000):
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


def jof(t):
    a, b = t.find("{"), t.rfind("}")
    if a < 0:
        return None
    try:
        return json.loads(t[a:b + 1])
    except Exception:
        return None


def attempt(user, ip, info_user=None, label=""):
    ts = str(int(time.time() * 1000))
    r = http("/cgi-bin/get_challenge?callback=cb&username=" + urllib.parse.quote(user)
             + "&ip=" + ip + "&_=" + ts)
    j = jof(r)
    if not j or "challenge" not in j:
        return "challenge失败"
    token = j["challenge"]
    hmd5 = hashlib.md5((PWD + token).encode()).hexdigest()
    iu = info_user if info_user else user
    info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (iu, PWD, ip)
    info_enc = "{SRBX1}" + S.b64(S.xencode(info, token))
    chksum = hashlib.sha1((token + user + token + hmd5 + token + "1" + token + ip
                           + token + "200" + token + "1" + token + info_enc).encode()).hexdigest()
    url = ("/cgi-bin/srun_portal?callback=cb&action=login&username=" + urllib.parse.quote(user)
           + "&password=" + urllib.parse.quote("{MD5}" + hmd5, safe="")
           + "&ac_id=1&ip=" + ip + "&chksum=" + chksum
           + "&info=" + urllib.parse.quote(info_enc, safe="")
           + "&n=200&type=1&os=Windows&name=Windows&double_stack=0&_=" + ts)
    resp = http(url, maxlen=1200)
    j2 = jof(resp)
    if not j2:
        return "空响应"
    return "%-24s %s" % (j2.get("error"), (label or user))


cases = [
    (USER, MY_IP, None, "YOUR_ACCOUNT"),
    (USER + "@mac", MY_IP, None, "YOUR_ACCOUNT@mac"),
    (USER + "@local", MY_IP, None, "YOUR_ACCOUNT@local"),
    ("YOUR_STUDENT_ID", MY_IP, None, "学号"),
    ("YOUR_STUDENT_ID@mac", MY_IP, None, "学号@mac"),
    ("YOUR_ACCOUNT", "0.0.0.0", None, "ip=0.0.0.0"),
]

for user, ip, iu, label in cases:
    try:
        r = attempt(user, ip, iu, label)
    except Exception as e:
        r = "EXC " + str(e)[:40]
    print("%-18s -> %s" % (label, r))
    time.sleep(1.2)
