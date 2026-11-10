# -*- coding: utf-8 -*-
"""
重新理解 sign_error：
用电脑 IP 但故意改坏 chksum，看错误码
如果也变 sign_error，说明 sign_error = 签名校验失败（而不是 IP 被拒）
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


def http(path, maxlen=1500):
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


def attempt(ip, break_sign=False, label=""):
    ts = str(int(time.time() * 1000))
    r = http("/cgi-bin/get_challenge?callback=cb&username=" + USER + "&ip=" + ip + "&_=" + ts)
    j = jof(r)
    if not j or "challenge" not in j:
        return "challenge失败"
    token = j["challenge"]
    hmd5 = S.hmac_md5_hex(token, PWD)
    info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, ip)
    info_enc = "{SRBX1}" + S.b64(S.xencode(info, token))
    chksum = S.sha1(token + USER + token + hmd5 + token + "1" + token + ip
                    + token + "200" + token + "1" + token + info_enc)
    if break_sign:
        chksum = "0" * 40
    url = ("/cgi-bin/srun_portal?callback=cb&action=login&username=" + USER
           + "&password=" + urllib.parse.quote("{MD5}" + hmd5, safe="")
           + "&os=Windows+10&name=Windows&nas_ip=&double_stack=0"
           + "&chksum=" + chksum + "&info=" + urllib.parse.quote(info_enc, safe="")
           + "&ac_id=1&ip=" + ip + "&n=200&type=1"
           + "&captchaVal=&ap_id=&ap_ip=&mac=&_=" + ts)
    r2 = http(url)
    j2 = jof(r2)
    if not j2:
        return "空"
    return "%s | %s" % (j2.get("error"), j2.get("error_msg") or "")


pc = "CLIENT_IP"
board = "BOARD_IP"

print("=== 理解错误码 ===")
print("  电脑IP 正常签名  :", attempt(pc, False))
time.sleep(1.2)
print("  电脑IP 破坏签名  :", attempt(pc, True))
time.sleep(1.2)
print("  板子IP 正常签名  :", attempt(board, False))
time.sleep(1.2)
print("  板子IP 破坏签名  :", attempt(board, True))
