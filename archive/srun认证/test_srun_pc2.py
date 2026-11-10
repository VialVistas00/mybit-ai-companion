# -*- coding: utf-8 -*-
"""用 YOUR_ACCOUNT / YOUR_PASSWORD 在电脑上做 SRun 认证测试（先登出再登入，拿到真实错误码）"""
import base64
import hashlib
import hmac
import json
import socket
import sys
import time
import urllib.parse

PORTAL = "PORTAL_IP"
USER = "YOUR_ACCOUNT"
PWD = "YOUR_PASSWORD"
MY_IP = "PC_IP"


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


# 用 CPython 的 hashlib/hmac，避免 MicroPython 差异
def md5(s):
    return hashlib.md5(s.encode()).hexdigest()


def sha1(s):
    return hashlib.sha1(s.encode()).hexdigest()


ts = str(int(time.time() * 1000))
r = http("/cgi-bin/get_challenge?callback=cb&username=" + USER + "&ip=" + MY_IP + "&_=" + ts)
j = jof(r)
print("challenge 响应:", (j or {}).get("error"), "token:", (j or {}).get("challenge", "")[:20], "...")
if not j or "challenge" not in j:
    print("原始:", r[:400])
    sys.exit(1)

token = j["challenge"]
hmd5 = md5(PWD + token)
info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, MY_IP)

# 复用板子上的 xencode（纯 Python，CPython 也能跑）
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S
info_enc = "{SRBX1}" + S.b64(S.xencode(info, token))
chksum = sha1(token + USER + token + hmd5 + token + "1" + token + MY_IP
              + token + "200" + token + "1" + token + info_enc)

print("hmd5  :", hmd5)
print("chksum:", chksum)

url = ("/cgi-bin/srun_portal?callback=cb&action=login&username=" + USER
       + "&password=" + urllib.parse.quote("{MD5}" + hmd5, safe="")
       + "&ac_id=1&ip=" + MY_IP + "&chksum=" + chksum
       + "&info=" + urllib.parse.quote(info_enc, safe="")
       + "&n=200&type=1&os=Windows&name=Windows&double_stack=0&_=" + ts)

resp = http(url, maxlen=1500)
print("\n登录响应:")
print(resp.split("\r\n\r\n")[-1][:600])
