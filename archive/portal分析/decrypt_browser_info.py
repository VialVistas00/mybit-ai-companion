# -*- coding: utf-8 -*-
"""用同一 token 解密浏览器的 info，看真实明文"""
import base64
import json
import sys
import time
from urllib.parse import urlparse, parse_qsl

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_ACCOUNT"
PWD = "YOUR_PASSWORD"

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S

cap = {}


def xxtea_decode(data, key):
    pwd = S._sencode(data.decode("latin-1"), False)
    pwdk = S._sencode(key, False)
    while len(pwdk) < 4:
        pwdk.append(0)
    n = len(pwd) - 1
    z = pwd[n]
    y = pwd[0]
    c = 0x86014019 | 0x183639A0
    d = (6 + 52 // (n + 1)) * c
    q = int(6 + 52 / (n + 1))
    while q > 0:
        e = (d >> 2) & 3
        p = n
        while p > 0:
            z = pwd[p - 1]
            m = (z >> 5) ^ (y << 2)
            m = m + (((y >> 3) ^ (z << 4)) ^ (d ^ y))
            m = m + (pwdk[(p & 3) ^ e] ^ z)
            pwd[p] = (pwd[p] - m) & 0xFFFFFFFF
            y = pwd[p]
            p -= 1
        z = pwd[n]
        m = (z >> 5) ^ (y << 2)
        m = m + (((y >> 3) ^ (z << 4)) ^ (d ^ y))
        m = m + (pwdk[(0 & 3) ^ e] ^ z)
        pwd[0] = (pwd[0] - m) & 0xFFFFFFFF
        y = pwd[0]
        d = (d - c) & 0xFFFFFFFF
        q -= 1
    return S._lencode(pwd, True)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False,
                                args=["--ignore-certificate-errors"])
    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()

    def on_resp(resp):
        if "get_challenge" in resp.url:
            try:
                t = resp.text()
                a, b = t.find("{"), t.rfind("}")
                cap["token"] = json.loads(t[a:b + 1]).get("challenge")
            except Exception:
                pass

    def on_req(req):
        if "cgi-bin/srun_portal" in req.url and "action=login" in req.url:
            cap["params"] = dict(parse_qsl(urlparse(req.url).query, keep_blank_values=True))

    page.on("response", on_resp)
    page.on("request", on_req)
    page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
    page.wait_for_timeout(3000)
    if page.query_selector_all("input"):
        page.fill("#username", USER, timeout=6000)
        page.fill("#password", PWD, timeout=6000)
        try:
            page.click("#login-account", timeout=3000)
        except Exception:
            page.keyboard.press("Enter")
        page.wait_for_timeout(6000)
    browser.close()

token = cap.get("token")
params = cap.get("params") or {}
real_info = params.get("info", "").replace("{SRBX1}", "")

raw = base64.b64decode(real_info)
print("浏览器 info 密文长度:", len(raw))
dec = xxtea_decode(raw, token)
print()
print("=== 解密结果 ===")
if dec:
    try:
        print(dec.decode("utf-8"))
    except Exception:
        print(repr(dec))
else:
    print("解密失败")

print()
print("=== 我的明文 ===")
ip = params.get("ip")
my_plain = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, ip)
print(my_plain)
print()
print("明文长度: 浏览器解密 %s / 我的 %d" % (
    (len(dec) if dec else "?"), len(my_plain)))
