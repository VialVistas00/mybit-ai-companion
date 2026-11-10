# -*- coding: utf-8 -*-
"""
验证：一次 get_challenge 后，立刻用它算完并提交（不给任何中间请求）
严格单流程，避免 token 失效
"""
import json
import socket
import sys
import time
import urllib.parse

PORTAL = "PORTAL_IP"
USER = "YOUR_ACCOUNT"
PWD = "YOUR_PASSWORD"

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S


def http(path, maxlen=2500):
    s = socket.socket()
    s.settimeout(12)
    s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
    hop = "keep-alive"
    s.send(("GET " + path + " HTTP/1.1\r\nHost: " + PORTAL
            + "\r\nConnection: " + hop + "\r\nUser-Agent: Mozilla/5.0\r\n\r\n").encode())
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


def jof(t):
    a, b = t.find("{"), t.rfind("}")
    if a < 0:
        return None
    try:
        return json.loads(t[a:b + 1])
    except Exception:
        return None


ip = "CLIENT_IP"
# ---- 严格三步，中间不做任何额外请求 ----
ts = str(int(time.time() * 1000))
r1 = http("/cgi-bin/get_challenge?callback=cb&username=" + USER + "&ip=" + ip + "&_=" + ts)
j1 = jof(r1)
token = j1["challenge"]
expire = j1.get("expire")
print("token :", token)
print("expire:", expire, "秒")

# 立刻计算并提交
hmd5 = S.hmac_md5_hex(token, PWD)
info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, ip)
info_enc = "{SRBX1}" + S.b64(S.xencode(info, token))
chksum = S.sha1(token + USER + token + hmd5 + token + "1" + token + ip
                + token + "200" + token + "1" + token + info_enc)

url = ("/cgi-bin/srun_portal?callback=cb&action=login&username=" + USER
       + "&password=" + urllib.parse.quote("{MD5}" + hmd5, safe="")
       + "&os=" + urllib.parse.quote("Windows 10", safe="") + "&name=Windows"
       + "&nas_ip=&double_stack=0&chksum=" + chksum
       + "&info=" + urllib.parse.quote(info_enc, safe="")
       + "&ac_id=1&ip=" + ip + "&n=200&type=1&captchaVal=&ap_id=&ap_ip=&mac=&_=" + ts)
r2 = http(url)
j2 = jof(r2)
print()
print("=== 结果 ===")
print(" ", json.dumps(j2, ensure_ascii=False) if j2 else r2[-300:])
