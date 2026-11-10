# -*- coding: utf-8 -*-
"""修正后用真实参数做认证（电脑 IP 已验证过可登录，先注销再登）"""
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


# 取本机 IP
r = http("/cgi-bin/rad_user_info?callback=cb")
j = jof(r)
ip = (j or {}).get("client_ip")
if not ip:
    ip = (j or {}).get("online_ip")
if not ip:
    print("拿不到 IP，用网络接口兜底")
    import subprocess
    out = subprocess.run(["powershell", "-NoProfile", "-c",
                          "(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias WLAN).IPAddress"],
                         capture_output=True, text=True).stdout.strip()
    ip = out
print("IP:", ip, " 状态:", (j or {}).get("error"))

print()
print("=== 先注销 ===")
r = http("/cgi-bin/srun_portal?action=logout&callback=cb")
print("  ", (jof(r) or {}).get("error"))

time.sleep(1)

print()
print("=== 用修正后的算法登录 ===")
ts = str(int(time.time() * 1000))
r = http("/cgi-bin/get_challenge?callback=cb&username=" + USER + "&ip=" + ip + "&_=" + ts)
j = jof(r)
token = j["challenge"]
print("  token:", token[:24], "...")

# 关键修正：HMAC-MD5
hmd5 = S.hmac_md5_hex(token, PWD)
print("  hmd5 :", hmd5)

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
r = http(url, maxlen=2500)
j2 = jof(r)
if j2:
    print()
    print("  登录结果:")
    for k in ("error", "error_msg", "res", "suc_msg", "ploy_msg"):
        if k in j2:
            print("    %-10s = %s" % (k, j2[k]))
    if j2.get("error") == "ok":
        print()
        print("  *** 认证成功 ***")
else:
    print("  ", r[-300:])
