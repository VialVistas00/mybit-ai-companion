# -*- coding: utf-8 -*-
"""
在电脑上打开浏览器，但让请求带上板子的 IP 参数
浏览器能成功，我就能看到它到底哪里不同
关键：用 Playwright 拦截并修改请求的 ip 参数为板子 IP
"""
import json
import time
from urllib.parse import urlparse, parse_qsl

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"
BOARD_IP = "BOARD_IP"

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
            cap["url"] = req.url

    page.on("response", on_resp)
    page.on("request", on_req)

    page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
    page.wait_for_timeout(3000)
    print("页面 URL:", page.url[:90])

    if not page.query_selector_all("input"):
        print("不在登录页，先访问")
        page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
        page.wait_for_timeout(3000)

    page.fill("#username", USER, timeout=6000)
    page.fill("#password", PWD, timeout=6000)
    try:
        page.click("#login-account", timeout=3000)
    except Exception:
        page.keyboard.press("Enter")
    page.wait_for_timeout(6000)
    print("登录后 URL:", page.url[:100])
    browser.close()

print()
print("=== 浏览器视角 ===")
print("  challenge 返回的 client_ip:", cap.get("cip"))
print("  请求中的 ip 参数:", (cap.get("params") or {}).get("ip"))
print("  服务端响应:", cap.get("resp", "")[:250])
print()
print("  完整参数:")
for k in ("action", "username", "os", "name", "ac_id", "ip", "n", "type"):
    v = (cap.get("params") or {}).get(k)
    if v is not None:
        print("    %-12s = %r" % (k, v))
