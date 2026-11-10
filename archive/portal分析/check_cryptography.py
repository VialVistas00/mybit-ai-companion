# -*- coding: utf-8 -*-
"""查 CREATER.cryptography 的值，以及它对密码处理的影响"""
import base64
import hashlib
import hmac
import json
import sys
import time
import urllib.parse
from urllib.parse import urlparse, parse_qsl

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"

cap = {}

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

    # 查 cryptography
    print("=== CREATER.cryptography ===")
    try:
        v = page.evaluate("() => { try { return String(CREATER.cryptography) } catch(e){ return 'ERR '+e.message } }")
        print("  ", v)
    except Exception as e:
        print("  ", e)

    # 查 $.base64
    print()
    print("=== $.base64 ===")
    try:
        v = page.evaluate("() => { try { return Object.keys($.base64).join(',') } catch(e){ return 'ERR '+e.message } }")
        print("  keys:", v)
        v2 = page.evaluate("() => { try { return $.base64.encode('YOUR_PASSWORD') } catch(e){ return 'ERR '+e.message } }")
        print("  encode('YOUR_PASSWORD') =", v2)
        v3 = page.evaluate("() => { try { return String($.base64.alpha || '') } catch(e){ return 'ERR' } }")
        print("  alpha:", v3)
    except Exception as e:
        print("  ", e)

    # 正常登录
    page.fill("#username", USER, timeout=6000)
    page.fill("#password", PWD, timeout=6000)
    try:
        page.click("#login-account", timeout=3000)
    except Exception:
        page.keyboard.press("Enter")
    page.wait_for_timeout(5000)
    browser.close()

token = cap.get("token")
params = cap.get("params") or {}
ip = params.get("ip")
real_hmd5 = (params.get("password") or "").replace("{MD5}", "")
real_info = params.get("info") or ""

print()
print("=" * 60)
print("token:", token)
print("ip   :", ip)
print("hmd5 :", real_hmd5)

# 测试密码变体
print()
print("=== 密码变体测试（HMAC-MD5 key=token）===")
variants = {
    "raw": PWD,
    "b64(enc)": base64.b64encode(urllib.parse.quote(PWD).encode()).decode(),
    "enc": urllib.parse.quote(PWD),
    "b64": base64.b64encode(PWD.encode()).decode(),
}
for vname, v in variants.items():
    h = hmac.new(token.encode(), v.encode(), hashlib.md5).hexdigest()
    print("  %-12s %s %s" % (vname, h[:32], "<<< 匹配" if h == real_hmd5 else ""))

# info 变体
print()
print("=== info 明文变体测试 ===")
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S

for vname, v in variants.items():
    plain = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, v, ip)
    mine = "{SRBX1}" + S.b64(S.xencode(plain, token))
    ok = "*** 匹配 ***" if mine == real_info else ""
    print("  %-12s len=%d %s" % (vname, len(mine), ok))
