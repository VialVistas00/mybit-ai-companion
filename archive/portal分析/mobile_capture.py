# -*- coding: utf-8 -*-
"""
模拟手机登录：用 iPhone UA + 移动端主题
手机能成功，我要看它发了什么
关键：手机端可能走 srun_portal_mobile 主题，参数不同
"""
import json
import time
from urllib.parse import urlparse, parse_qsl

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"

cap = {}


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False,
                                    args=["--ignore-certificate-errors"])
        dev = p.devices["iPhone 13"]
        ctx = browser.new_context(ignore_https_errors=True, **dev)
        page = ctx.new_page()

        def on_resp(resp):
            u = resp.url
            if "get_challenge" in u:
                try:
                    t = resp.text()
                    a, b = t.find("{"), t.rfind("}")
                    j = json.loads(t[a:b + 1])
                    cap["token"] = j.get("challenge")
                    cap["cip"] = j.get("client_ip")
                except Exception:
                    pass
            if "cgi-bin/srun_portal" in u and "action=login" in u:
                try:
                    cap["login_resp"] = resp.text()[:400]
                except Exception:
                    pass

        def on_req(req):
            u = req.url
            if "cgi-bin/srun_portal" in u and "action=login" in u:
                cap["url"] = u
                cap["params"] = dict(parse_qsl(urlparse(u).query, keep_blank_values=True))

        page.on("response", on_resp)
        page.on("request", on_req)

        page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=30000)
        page.wait_for_timeout(3500)
        print("初始 URL:", page.url[:100])

        # 手机端可能用不同的页面
        ins = page.query_selector_all("input")
        print("input 数:", len(ins))
        for e in ins[:6]:
            print("  ", e.evaluate("el => ({id: el.id, type: el.type, ph: el.placeholder})"))

        if not ins:
            print("手机 UA 下没有登录框，尝试移动端地址")
            page.goto("http://%s/srun_portal_mobile?ac_id=1&theme=pro" % PORTAL, timeout=25000)
            page.wait_for_timeout(3000)
            print("  新 URL:", page.url[:100])
            ins = page.query_selector_all("input")
            print("  input 数:", len(ins))

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
    print("=== 手机端抓包 ===")
    print("  token:", (cap.get("token") or "")[:32])
    print("  client_ip:", cap.get("cip"))
    prm = cap.get("params") or {}
    print()
    print("  参数:")
    for k, v in prm.items():
        if k == "info":
            print("    %-14s = %s...(len %d)" % (k, v[:40], len(v)))
        elif k == "chksum":
            print("    %-14s = %s" % (k, v))
        elif k == "password":
            print("    %-14s = %s" % (k, v))
        else:
            print("    %-14s = %r" % (k, v))
    print()
    print("  响应:", (cap.get("login_resp") or "")[:300])


main()
