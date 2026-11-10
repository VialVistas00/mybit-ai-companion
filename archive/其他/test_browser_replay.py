# -*- coding: utf-8 -*-
"""
完全复刻浏览器登录请求：
  1. 先调 captcha 检查
  2. get_challenge
  3. srun_portal 用浏览器的参数顺序，不带多余字段
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


def http(path, timeout=12, maxlen=2000):
    s = socket.socket()
    s.settimeout(timeout)
    s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
    s.send(("GET " + path + " HTTP/1.1\r\nHost: " + PORTAL
            + "\r\nConnection: close\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n"
            + "Accept: */*\r\nReferer: http://" + PORTAL + "/srun_portal_pc?ac_id=1&theme=pro\r\n\r\n").encode())
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


# 先问出本机在 Portal 眼里的 IP
print("=== 0. 查本机在 Portal 侧的 IP ===")
r = http("/cgi-bin/rad_user_info?callback=cb")
j = jof(r)
myip = (j or {}).get("client_ip") or (j or {}).get("online_ip")
print("  client_ip =", myip, " error =", (j or {}).get("error"))

if not myip:
    print("拿不到 IP，退出")
    sys.exit(1)

print()
print("=== 1. captcha 检查 ===")
ts = str(int(time.time() * 1000))
r = http("/v2/srun_portal_captcha_image_info?user_name=" + USER + "&ip=" + myip + "&_=" + ts)
print("  ", r.split("\r\n\r\n")[-1][:200])

print()
print("=== 2. get_challenge ===")
r = http("/cgi-bin/get_challenge?callback=cb&username=" + USER + "&ip=" + myip + "&_=" + ts)
j = jof(r)
if not j or "challenge" not in j:
    print("  失败:", r[200:400])
    sys.exit(1)
token = j["challenge"]
print("  token:", token[:20], "...  expire:", j.get("expire"))

print()
print("=== 3. srun_portal（复刻浏览器参数）===")
hmd5 = hashlib.md5((PWD + token).encode()).hexdigest()
info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, myip)
info_enc = "{SRBX1}" + S.b64(S.xencode(info, token))
chksum = hashlib.sha1((token + USER + token + hmd5 + token + "1" + token + myip
                       + token + "200" + token + "1" + token + info_enc).encode()).hexdigest()

# 按浏览器顺序，os/name 用浏览器格式
url = ("/cgi-bin/srun_portal?callback=cb&action=login&username=" + USER
       + "&password=" + urllib.parse.quote("{MD5}" + hmd5, safe="")
       + "&os=" + urllib.parse.quote("Windows 10", safe="")
       + "&name=" + urllib.parse.quote("Windows", safe="")
       + "&double_stack=0&chksum=" + chksum
       + "&info=" + urllib.parse.quote(info_enc, safe="")
       + "&ac_id=1&ip=" + myip + "&n=200&type=1&_=" + ts)
r = http(url, maxlen=1500)
j2 = jof(r)
print("  结果:", json.dumps(j2, ensure_ascii=False)[:400] if j2 else r[200:400])
