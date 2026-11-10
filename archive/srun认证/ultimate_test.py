# -*- coding: utf-8 -*-
"""
终极对照：会话已清空状态下，
  A. 手写代码在【电脑 IP】认证 -> 应该成功（如果算法正确）
  B. 手写代码在【板子 IP】认证 -> 看是否 sign_error
这样能彻底区分「算法错」还是「IP 受限」
"""
import hashlib
import hmac
import json
import socket
import sys
import time
import urllib.parse

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"
BOARD_IP = "BOARD_IP"

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S


def http(path, maxlen=2500):
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


def login(ip, label):
    ts = str(int(time.time() * 1000))
    r = http("/cgi-bin/get_challenge?callback=cb&username=" + USER + "&ip=" + ip + "&_=" + ts)
    j = jof(r)
    if not j or "challenge" not in j:
        print("  [%s] challenge 失败" % label)
        return
    token = j["challenge"]
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
    if j2:
        print("  [%-10s] ip=%-15s error=%-22s msg=%s" % (
            label, ip, j2.get("error"), j2.get("error_msg") or ""))
        return j2.get("error")
    print("  [%s] 空响应" % label)
    return None


# 本机 IP
r = http("/cgi-bin/rad_user_info?callback=cb")
j = jof(r)
print("当前本机会话:", (j or {}).get("error"), " client_ip:", (j or {}).get("client_ip"))
print()

pc_ip = (j or {}).get("client_ip") or "PC_IP"

print("=== 对照认证 ===")
login(pc_ip, "电脑IP")
time.sleep(1.5)
login(BOARD_IP, "板子IP")
