# -*- coding: utf-8 -*-
"""用浏览器完全一致的请求头重试，唯一差别就是 cookie/accept"""
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

HEADERS = (
    "Accept: text/javascript, application/javascript, application/ecmascript, "
    "application/x-ecmascript, */*; q=0.01\r\n"
    "Accept-Language: zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6\r\n"
    "Cookie: lang=zh-CN\r\n"
    "Referer: http://PORTAL_IP/srun_portal_pc?ac_id=1&theme=pro\r\n"
    "X-Requested-With: XMLHttpRequest\r\n"
    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36 Edg/150.0.0.0\r\n"
)


def http(path, maxlen=2500):
    s = socket.socket()
    s.settimeout(12)
    s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
    s.send(("GET " + path + " HTTP/1.1\r\nHost: " + PORTAL
            + "\r\nConnection: close\r\n" + HEADERS + "\r\n").encode())
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


ts = str(int(time.time() * 1000))
r = http("/cgi-bin/get_challenge?callback=cb&username=" + USER + "&ip=CLIENT_IP&_=" + ts)
j = jof(r)
if not j or "challenge" not in j:
    print("challenge 失败:", r[:300])
else:
    token = j["challenge"]
    print("token:", token)
    hmd5 = S.hmac_md5_hex(token, PWD)
    info = '{"username":"%s","password":"%s","ip":"CLIENT_IP","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD)
    info_enc = "{SRBX1}" + S.b64(S.xencode(info, token))
    chksum = S.sha1(token + USER + token + hmd5 + token + "1" + token + "CLIENT_IP"
                    + token + "200" + token + "1" + token + info_enc)

    url = ("/cgi-bin/srun_portal?callback=cb&action=login&username=" + USER
           + "&password=" + urllib.parse.quote("{MD5}" + hmd5, safe="")
           + "&os=" + urllib.parse.quote("Windows 10", safe="") + "&name=Windows"
           + "&nas_ip=&double_stack=0&chksum=" + chksum
           + "&info=" + urllib.parse.quote(info_enc, safe="")
           + "&ac_id=1&ip=CLIENT_IP&n=200&type=1"
           + "&captchaVal=&ap_id=&ap_ip=&mac=&_=" + ts)
    r2 = http(url)
    j2 = jof(r2)
    print()
    print("=== 带完整浏览器头的结果 ===")
    print(" ", json.dumps(j2, ensure_ascii=False) if j2 else r2[-300:])
