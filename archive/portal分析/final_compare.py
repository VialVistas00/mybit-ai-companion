# -*- coding: utf-8 -*-
"""
终极对照：同一个 token 下，浏览器算的 hmd5 和我算的 hmd5 是否一致
做法：先在浏览器里取 token，再用同一个 token 调 md5()
"""
import hashlib
import hmac
import json
import sys
import time
from urllib.parse import urlparse, parse_qsl

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S

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
                cap["token_json"] = json.loads(t[a:b + 1])
            except Exception:
                pass

    def on_req(req):
        if "cgi-bin/srun_portal" in req.url and "action=login" in req.url:
            cap["params"] = dict(parse_qsl(urlparse(req.url).query, keep_blank_values=True))
            cap["url"] = req.url

    page.on("response", on_resp)
    page.on("request", on_req)

    # 注销
    page.goto("http://%s/cgi-bin/srun_portal?action=logout&callback=cb" % PORTAL, timeout=15000)
    page.wait_for_timeout(2500)
    info_txt = page.inner_text("body")
    print("注销响应:", info_txt[:200])

    page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
    page.wait_for_timeout(3000)
    print("URL:", page.url[:100])

    inputs = page.query_selector_all("input")
    if len(inputs) == 0:
        print("!! 不在登录页，无法继续")
        browser.close()
        sys.exit(0)

    page.fill("#username", USER, timeout=6000)
    page.fill("#password", PWD, timeout=6000)
    try:
        page.click("#login-account", timeout=3000)
    except Exception:
        page.keyboard.press("Enter")
    page.wait_for_timeout(5000)

    # 关键：让浏览器用【抓到的那个 token】算一遍 md5
    token = (cap.get("token_json") or {}).get("challenge")
    if token:
        browser_md5 = page.evaluate("(t) => md5('%s', t)" % PWD, token)
        cap["browser_md5"] = browser_md5

    browser.close()

token = (cap.get("token_json") or {}).get("challenge")
params = cap.get("params") or {}
real_hmd5 = (params.get("password") or "").replace("{MD5}", "")

print()
print("=" * 66)
print("token      :", token)
print("浏览器 hmd5 :", real_hmd5)
print("浏览器 md5():", cap.get("browser_md5"))
print()
print("我的 hmac  :", S.hmac_md5_hex(token, PWD) if token else "?")
print("我的 md5+t :", hashlib.md5((PWD + token).encode()).hexdigest() if token else "?")
print()
print("浏览器算的 == 发出的:", cap.get("browser_md5") == real_hmd5)
print()
print("完整 URL:")
print((cap.get("url") or "")[:600])
