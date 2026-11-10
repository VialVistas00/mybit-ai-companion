# -*- coding: utf-8 -*-
"""
诊断 BAS respond timeout：
  1. 看完整响应（可能有更多字段）
  2. 直接从板子测：如果板子认证时请求能到达 BAS，说明网络通路是通的
  3. 关键验证：板子 IP 的认证请求，服务器返回 auth_info_error，
     而浏览器（电脑 IP）返回 login_error。
     说明板子的请求在被 BAS 处理前就被拒绝了。
"""
import json
import socket
import sys
import time
import urllib.parse

PORTAL = "PORTAL_IP"
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S


def http(path, maxlen=3000):
    s = socket.socket()
    s.settimeout(12)
    s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
    s.send(("GET " + path + " HTTP/1.1\r\nHost: " + PORTAL
            + "\r\nConnection: close\r\nUser-Agent: Mozilla/5.0\r\n\r\n").encode())
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


def login(user, pwd, ip, label):
    ts = str(int(time.time() * 1000))
    r = http("/cgi-bin/get_challenge?callback=cb&username=" + urllib.parse.quote(user)
             + "&ip=" + ip + "&_=" + ts)
    j = jof(r)
    if not j or "challenge" not in j:
        return "challenge失败"
    token = j["challenge"]
    hmd5 = S.hmac_md5_hex(token, pwd)
    info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (user, pwd, ip)
    info_enc = "{SRBX1}" + S.b64(S.xencode(info, token))
    chksum = S.sha1(token + user + token + hmd5 + token + "1" + token + ip
                    + token + "200" + token + "1" + token + info_enc)
    url = ("/cgi-bin/srun_portal?callback=cb&action=login&username=" + urllib.parse.quote(user)
           + "&password=" + urllib.parse.quote("{MD5}" + hmd5, safe="")
           + "&os=Windows+10&name=Windows&nas_ip=&double_stack=0"
           + "&chksum=" + chksum + "&info=" + urllib.parse.quote(info_enc, safe="")
           + "&ac_id=1&ip=" + ip + "&n=200&type=1&captchaVal=&ap_id=&ap_ip=&mac=&_=" + ts)
    r2 = http(url, 3000)
    j2 = jof(r2)
    return json.dumps(j2, ensure_ascii=False) if j2 else r2[-200:]


print("=== 完整响应对比 ===\n")
print("[电脑IP + YOUR_ACCOUNT]")
print(" ", login("YOUR_ACCOUNT", "YOUR_PASSWORD", "CLIENT_IP", "pc"))
print()
time.sleep(2)
print("[电脑IP + YOUR_STUDENT_ID]")
print(" ", login("YOUR_STUDENT_ID", "YOUR_PASSWORD", "CLIENT_IP", "pc2"))
print()
time.sleep(2)
print("[板子IP + YOUR_ACCOUNT]（用电脑代发，测服务器是否接受该 IP）")
print(" ", login("YOUR_ACCOUNT", "YOUR_PASSWORD", "BOARD_IP", "board"))
