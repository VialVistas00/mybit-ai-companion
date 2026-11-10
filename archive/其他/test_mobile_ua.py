# -*- coding: utf-8 -*-
"""
手机端 UA 模拟登录：看是否与 PC 端有任何差异
同时打印完整请求与响应
"""
import json
import time

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"

IPHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")

cap = {}


def run(label, ua, is_mobile):
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False,
                                    args=["--ignore-certificate-errors"])
        dev = p.devices["iPhone 13"] if is_mobile else {}
        kwargs = dict(dev) if dev else {}
        kwargs["ignore_https_errors"] = True
        if not dev:
            kwargs["user_agent"] = ua
        ctx = browser.new_context(**kwargs)
        page = ctx.new_page()

        def on_resp(resp):
            if "cgi-bin/srun_portal" in resp.url and "action=login" in resp.url:
                try:
                    cap[label] = resp.text()
                except Exception:
                    pass

        def on_req(req):
            if "cgi-bin/srun_portal" in req.url and "action=login" in req.url:
                cap[label + "_url"] = req.url

        page.on("response", on_resp)
        page.on("request", on_req)

        try:
            page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
            page.wait_for_timeout(2500)
            # 手机版可能用不同 selector
            for sel in ("#username", "input[name=username]", ".input-box"):
                try:
                    page.fill(sel, USER, timeout=3000)
                    break
                except Exception:
                    continue
            for sel in ("#password", "input[type=password]"):
                try:
                    page.fill(sel, PWD, timeout=3000)
                    break
                except Exception:
                    continue
            for sel in ("#login-account", ".login-btn", "button"):
                try:
                    page.click(sel, timeout=2000)
                    break
                except Exception:
                    continue
            else:
                page.keyboard.press("Enter")
            page.wait_for_timeout(5000)
            cap[label + "_final"] = page.url
        except Exception as e:
            cap[label + "_err"] = str(e)[:120]
        browser.close()


print("=== 手机 UA 登录 ===")
run("mobile", IPHONE_UA, True)
time.sleep(2)

for k in sorted(cap.keys()):
    v = str(cap[k])
    if k.endswith("_url"):
        print()
        print("[%s]" % k)
        print("  " + v[:400])
    elif k.endswith("_final"):
        print("[%s] %s" % (k, v[:100]))
    elif k.endswith("_err"):
        print("[%s] %s" % (k, v[:120]))
    else:
        print("[%s] %s" % (k, v[:300]))
