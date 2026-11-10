# -*- coding: utf-8 -*-
"""
用「完整浏览器流程」尝试登录：
  1. GET 认证页（拿 cookie）
  2. GET get_challenge（带 cookie + referer）
  3. GET srun_portal（带 cookie + referer）
在电脑上执行（电脑已在线，若成功会返回 already_online 或成功码）
同时测试板子 IP 的目标 —— 但请求会落在本机 IP，所以先验证流程本身正确性。
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
MY_IP = "PC_IP"

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S


class Session:
    def __init__(self):
        self.cookies = {}

    def merge(self, raw):
        for line in raw.split("\r\n"):
            if line.lower().startswith("set-cookie:"):
                kv = line.split(":", 1)[1].strip().split(";")[0]
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    self.cookies[k.strip()] = v.strip()

    def cookie_header(self):
        if not self.cookies:
            return ""
        return "Cookie: " + "; ".join("%s=%s" % (k, v) for k, v in self.cookies.items()) + "\r\n"

    def get(self, path, referer=None, xhr=True, maxlen=4000):
        s = socket.socket()
        s.settimeout(12)
        s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
        h = "Host: " + PORTAL + "\r\nConnection: close\r\n"
        h += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36\r\n"
        h += "Accept: */*\r\n"
        h += self.cookie_header()
        if referer:
            h += "Referer: " + referer + "\r\n"
        if xhr:
            h += "X-Requested-With: XMLHttpRequest\r\n"
        s.send(("GET " + path + " HTTP/1.1\r\n" + h + "\r\n").encode())
        buf = b""
        while len(buf) < maxlen:
            try:
                c = s.recv(1000)
            except Exception:
                break
            if not c:
                break
            buf += c
        s.close()
        raw = buf.decode("utf-8", "replace")
        self.merge(raw)
        return raw


def body(t):
    return t.split("\r\n\r\n", 1)[-1] if "\r\n\r\n" in t else t


def jof(t):
    a, b = t.find("{"), t.rfind("}")
    if a < 0:
        return None
    try:
        return json.loads(t[a:b + 1])
    except Exception:
        return None


sess = Session()

print("=== 1. 打开认证页 ===")
r = sess.get("/srun_portal_pc?ac_id=1&theme=pro", xhr=False, maxlen=6000)
print("  状态:", r.split("\r\n")[0])
print("  cookie:", list(sess.cookies.keys()))
ref = "http://" + PORTAL + "/srun_portal_pc?ac_id=1&theme=pro"

print()
print("=== 2. get_challenge ===")
ts = str(int(time.time() * 1000))
r = sess.get("/cgi-bin/get_challenge?callback=cb&username=" + USER + "&ip=" + MY_IP + "&_=" + ts,
             referer=ref)
j = jof(r)
print("  ", (j or {}).get("error"), (j or {}).get("challenge", "")[:16])
if not j or "challenge" not in j:
    sys.exit(1)

token = j["challenge"]
hmd5 = hashlib.md5((PWD + token).encode()).hexdigest()
info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, MY_IP)
info_enc = "{SRBX1}" + S.b64(S.xencode(info, token))
chksum = hashlib.sha1((token + USER + token + hmd5 + token + "1" + token + MY_IP
                       + token + "200" + token + "1" + token + info_enc).encode()).hexdigest()

url = ("/cgi-bin/srun_portal?callback=cb&action=login&username=" + USER
       + "&password=" + urllib.parse.quote("{MD5}" + hmd5, safe="")
       + "&ac_id=1&ip=" + MY_IP + "&chksum=" + chksum
       + "&info=" + urllib.parse.quote(info_enc, safe="")
       + "&n=200&type=1&os=Windows&name=Windows&double_stack=0&_=" + ts)

print()
print("=== 3. 登录请求 ===")
r = sess.get(url, referer=ref)
print("  状态:", r.split("\r\n")[0])
print("  响应:", body(r)[:400])
