# -*- coding: utf-8 -*-
"""在电脑上验证 SRun login（chksum 改用 SHA1）"""
import sys
import time
import urllib.parse

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S

PORTAL = "PORTAL_IP"
USER = "YOUR_ACCOUNT"
PWD = "YOUR_PASSWORD"
MY_IP = "PC_IP"


def http(path, timeout=10):
    import socket
    s = socket.socket()
    s.settimeout(timeout)
    s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
    req = ("GET " + path + " HTTP/1.1\r\nHost: " + PORTAL
           + "\r\nConnection: close\r\nUser-Agent: Mozilla/5.0\r\n\r\n")
    s.send(req.encode())
    buf = b""
    while True:
        try:
            c = s.recv(400)
        except Exception:
            break
        if not c:
            break
        buf += c
    s.close()
    return buf.decode("utf-8", "replace")


ts = str(int(time.time() * 1000))
r = http("/cgi-bin/get_challenge?callback=cb&username=" + USER + "&ip=" + MY_IP + "&_=" + ts)
j = S._json_of(r)
token = j["challenge"]
print("challenge:", token[:24], "...  client_ip:", j.get("client_ip"))

hmd5 = S.md5(PWD + token)
info_json = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, MY_IP)
info_enc = "{SRBX1}" + S.b64(S.xencode(info_json, token))
chk_src = (token + USER + token + hmd5 + token + "1" + token + MY_IP
           + token + "200" + token + "1" + token + info_enc)
chksum = S.sha1(chk_src)
print("chksum(sha1):", chksum)

url = ("/cgi-bin/srun_portal?callback=cb&action=login&username=" + USER
       + "&password=" + urllib.parse.quote("{MD5}" + hmd5, safe="")
       + "&ac_id=1&ip=" + MY_IP + "&chksum=" + chksum
       + "&info=" + urllib.parse.quote(info_enc, safe="")
       + "&n=200&type=1&os=Windows&name=Windows&double_stack=0&_=" + ts)

resp = http(url)
parts = resp.split("\r\n\r\n")
body = parts[1] if len(parts) > 1 else ""
print("\n状态行:", parts[0].split("\r\n")[0])
print("响应体:", body[:500] if body else "(空)")
