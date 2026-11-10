# -*- coding: utf-8 -*-
"""
决定性测试：登录时用「板子的 IP」而不是电脑 IP
如果服务器按 ip 参数做绑定校验，用板子 IP 应该返回不同错误
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
PC_IP = "PC_IP"
BOARD_IP = "BOARD_IP"

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


def attempt(user, pwd, ip, label):
    ts = str(int(time.time() * 1000))
    r = http("/cgi-bin/get_challenge?callback=cb&username=" + urllib.parse.quote(user)
             + "&ip=" + ip + "&_=" + ts)
    j = jof(r)
    if not j or "challenge" not in j:
        return "challenge失败: " + r[200:300]
    token = j["challenge"]
    hmd5 = hashlib.md5((pwd + token).encode()).hexdigest()
    info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (user, pwd, ip)
    info_enc = "{SRBX1}" + S.b64(S.xencode(info, token))
    chksum = hashlib.sha1((token + user + token + hmd5 + token + "1" + token + ip
                           + token + "200" + token + "1" + token + info_enc).encode()).hexdigest()
    url = ("/cgi-bin/srun_portal?callback=cb&action=login&username=" + urllib.parse.quote(user)
           + "&password=" + urllib.parse.quote("{MD5}" + hmd5, safe="")
           + "&ac_id=1&ip=" + ip + "&chksum=" + chksum
           + "&info=" + urllib.parse.quote(info_enc, safe="")
           + "&n=200&type=1&os=Windows&name=Windows&double_stack=0&_=" + ts)
    r2 = http(url)
    j2 = jof(r2)
    if not j2:
        return "空/" + r2.split("\r\n")[0]
    return "%s | %s" % (j2.get("error"), j2.get("error_msg") or j2.get("res") or "")


print("登录 IP 参数对照：")
print("-" * 70)
for label, ip in (("电脑 IP " + PC_IP, PC_IP), ("板子 IP " + BOARD_IP, BOARD_IP)):
    try:
        r = attempt(USER, PWD, ip, label)
    except Exception as e:
        r = "EXC " + str(e)[:40]
    print("  %-22s -> %s" % (label, r))
    time.sleep(1.2)

print()
print("=== 用板子 IP 查在线状态 ===")
ts = str(int(time.time() * 1000))
r = http("/cgi-bin/rad_user_info?callback=cb&ip=" + BOARD_IP + "&_=" + ts)
j = jof(r)
print("  ", (j or {}).get("error"), "online_ip:", (j or {}).get("online_ip"))
