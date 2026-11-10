# -*- coding: utf-8 -*-
"""用 ServiceIP (PORTAL_IP:8800) 走认证，而不是 80"""
import hashlib
import json
import socket
import ssl
import sys
import time
import urllib.parse

PORTAL = "PORTAL_IP"
SVC_PORT = 8800
USER = "YOUR_ACCOUNT"
PWD = "YOUR_PASSWORD"
MY_IP = "PC_IP"

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S


def http(host, port, path, tls=False, timeout=12, maxlen=3000):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(socket.getaddrinfo(host, port)[0][4])
        if tls:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            s = ctx.wrap_socket(s, server_hostname=host)
        s.send(("GET " + path + " HTTP/1.1\r\nHost: " + host
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
        return buf.decode("utf-8", "replace")
    finally:
        try:
            s.close()
        except Exception:
            pass


def jof(t):
    a, b = t.find("{"), t.rfind("}")
    if a < 0:
        return None
    try:
        return json.loads(t[a:b + 1])
    except Exception:
        return None


# 1. 先看 8800 是否可达
print("=== 探测 8800 ===")
for tls in (True, False):
    try:
        r = http(PORTAL, SVC_PORT, "/", tls=tls, maxlen=300)
        print("  tls=%s -> %s" % (tls, r.split("\r\n")[0]))
    except Exception as e:
        print("  tls=%s -> %s" % (tls, str(e)[:60]))

# 2. 从 8800 取 challenge
print()
print("=== 从 8800 取 challenge ===")
ts = str(int(time.time() * 1000))
r = http(PORTAL, SVC_PORT, "/cgi-bin/get_challenge?callback=cb&username=" + USER
         + "&ip=" + MY_IP + "&_=" + ts, tls=True, maxlen=1500)
print("  " + r.split("\r\n\r\n")[-1][:300])

j = jof(r)
if not j or "challenge" not in j:
    print("  拿不到 token，试试非 TLS")
    r = http(PORTAL, SVC_PORT, "/cgi-bin/get_challenge?callback=cb&username=" + USER
             + "&ip=" + MY_IP + "&_=" + ts, tls=False, maxlen=1500)
    print("  " + r.split("\r\n\r\n")[-1][:300])
    j = jof(r)

if j and "challenge" in j:
    token = j["challenge"]
    hmd5 = hashlib.md5((PWD + token).encode()).hexdigest()
    info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, MY_IP)
    info_enc = "{SRBX1}" + S.b64(S.xencode(info, token))
    chksum = hashlib.sha1((token + USER + token + hmd5 + token + "1" + token + MY_IP
                           + token + "200" + token + "1" + token + info_enc).encode()).hexdigest()
    url = ("/cgi-bin/srun_portal?callback=cb&action=login&username=" + USER
           + "&password=" + urllib.parse.quote("{MD5}" + hmd5, safe="")
           + "&ac_id=1&ip=" + MY_IP + "&chksum=" + chksum
           + "&info=" + urllib.parse.quote(info_enc, safe="")
           + "&n=200&type=1&os=Windows&name=Windows&double_stack=0&_=" + ts)
    print()
    print("=== 通过 8800 登录 ===")
    for tls in (True, False):
        resp = http(PORTAL, SVC_PORT, url, tls=tls, maxlen=1500)
        print("  tls=%s -> %s" % (tls, resp.split("\r\n\r\n")[-1][:400]))
