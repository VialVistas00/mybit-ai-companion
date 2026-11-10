# -*- coding: utf-8 -*-
"""用浏览器登录 YOUR_ACCOUNT / YOUR_PASSWORD，看真实结果"""
import json
import time
from urllib.parse import urlparse, parse_qsl

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_ACCOUNT"
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
                j = json.loads(t[a:b + 1])
                cap["token"] = j.get("challenge")
                cap["cip"] = j.get("client_ip")
            except Exception:
                pass
        if "cgi-bin/srun_portal" in resp.url and "action=login" in resp.url:
            try:
                cap["resp"] = resp.text()[:400]
            except Exception:
                pass

    def on_req(req):
        if "cgi-bin/srun_portal" in req.url and "action=login" in req.url:
            cap["params"] = dict(parse_qsl(urlparse(req.url).query, keep_blank_values=True))

    page.on("response", on_resp)
    page.on("request", on_req)

    page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
    page.wait_for_timeout(3000)
    print("URL:", page.url[:100])
    ins = page.query_selector_all("input")
    print("input:", len(ins))
    if ins:
        page.fill("#username", USER, timeout=6000)
        page.fill("#password", PWD, timeout=6000)
        try:
            page.click("#login-account", timeout=3000)
        except Exception:
            page.keyboard.press("Enter")
        page.wait_for_timeout(6000)
        print("登录后 URL:", page.url[:110])
    browser.close()

print()
print("=== 结果 ===")
print("  token:", (cap.get("token") or "")[:32])
prm = cap.get("params") or {}
print("  username:", prm.get("username"))
print("  password:", prm.get("password"))
print()
print("  响应:", (cap.get("resp") or "(无)")[:320])
