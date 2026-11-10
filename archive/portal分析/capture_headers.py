# -*- coding: utf-8 -*-
"""抓浏览器 login 请求的【全部请求头】，找出我遗漏的头"""
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

    def on_req(req):
        if "cgi-bin/srun_portal" in req.url and "action=login" in req.url:
            cap["headers"] = dict(req.headers)
            cap["all_headers"] = req.all_headers()
            cap["params"] = dict(parse_qsl(urlparse(req.url).query, keep_blank_values=True))

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

print("=== 浏览器 login 请求的全部头 ===")
for k, v in (cap.get("all_headers") or {}).items():
    print("  %-22s : %s" % (k, str(v)[:120]))

print()
print("=== cookie 相关 ===")
ctx_cookies = cap.get("headers", {})
for k, v in (cap.get("all_headers") or {}).items():
    if "cookie" in k.lower():
        print("  %s = %s" % (k, v))
