# -*- coding: utf-8 -*-
"""
按浏览器完整参数顺序复刻登录（含所有空值字段）
"""
import hashlib
import json
import sys
import time
import urllib.parse

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S


def http(path, timeout=12, maxlen=2000):
    s = S.socket.socket() if hasattr(S, "socket") else None
    import socket
    s = socket.socket()
    s.settimeout(timeout)
    s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
    s.send(("GET " + path + " HTTP/1.1\r\nHost: " + PORTAL
            + "\r\nConnection: close\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n"
            + "Referer: http://" + PORTAL + "/srun_portal_pc?ac_id=1&theme=pro\r\n\r\n").encode())
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


def do_login(ip):
    ts = str(int(time.time() * 1000))
    r = http("/cgi-bin/get_challenge?callback=cb&username=" + USER + "&ip=" + ip + "&_=" + ts)
    j = jof(r)
    if not j or "challenge" not in j:
        print("  challenge 失败")
        return None
    token = j["challenge"]
    hmd5 = hashlib.md5((PWD + token).encode()).hexdigest()
    info = ('{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}'
            % (USER, PWD, ip))
    info_enc = "{SRBX1}" + S.b64(S.xencode(info, token))
    chksum = hashlib.sha1((token + USER + token + hmd5 + token + "1" + token + ip
                           + token + "200" + token + "1" + token + info_enc).encode()).hexdigest()

    # 完全按浏览器的顺序与字段（含空值字段）
    url = ("/cgi-bin/srun_portal?callback=cb&action=login&username=" + USER
           + "&password=" + urllib.parse.quote("{MD5}" + hmd5, safe="")
           + "&os=" + urllib.parse.quote("Windows 10", safe="")
           + "&name=Windows"
           + "&nas_ip="
           + "&double_stack=0"
           + "&chksum=" + chksum
           + "&info=" + urllib.parse.quote(info_enc, safe="")
           + "&ac_id=1&ip=" + ip + "&n=200&type=1"
           + "&captchaVal=&ap_id=&ap_ip=&mac="
           + "&_=" + ts)
    r2 = http(url, maxlen=1500)
    j2 = jof(r2)
    if not j2:
        print("  空响应:", r2.split("\r\n")[0])
        return None
    return j2


print("=== 查本机 IP ===")
r = http("/cgi-bin/rad_user_info?callback=cb")
j = jof(r)
ip = (j or {}).get("client_ip")
print("  ", ip, (j or {}).get("error"))

print()
print("=== 完整参数登录 ===")
res = do_login(ip)
if res:
    print("  error    :", res.get("error"))
    print("  error_msg:", res.get("error_msg"))
    print("  res      :", res.get("res"))
    if res.get("error") == "ok":
        print("  *** 登录成功 ***")
