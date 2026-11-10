# -*- coding: utf-8 -*-
"""
在浏览器上下文里直接调用页面自己的 md5 / getUserPassword
直接得到正确答案，不用反推
"""
import json
import sys
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

        page.on("response", on_resp)
        page.on("request", on_req)

        page.goto("http://%s/cgi-bin/srun_portal?action=logout&callback=cb" % PORTAL, timeout=15000)
        page.wait_for_timeout(1500)
        page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
        page.wait_for_timeout(3000)

        # 在页面上下文里探测可用的加密函数
        probes = [
            "typeof md5",
            "typeof sha1",
            "typeof PORTAL",
            "typeof portal",
            "typeof CREATER",
            "Object.keys(window).filter(k=>/portal|creater|md5|sha1|base64|utils/i.test(k)).join(',')",
            "typeof window.md5",
            "typeof $.base64",
        ]
        print("=== 环境探测 ===")
        for expr in probes:
            try:
                v = page.evaluate("() => { try { return String(%s) } catch(e) { return 'ERR ' + e.message } }" % expr)
                print("  %-70s = %s" % (expr[:68], v[:80]))
            except Exception as e:
                print("  %-70s ERR %s" % (expr[:68], str(e)[:40]))

        # 尝试调用 md5
        print()
        print("=== 尝试调用 md5 ===")
        tests = [
            ("md5('YOUR_PASSWORD', 'abc')", "md5(密码, token)"),
            ("md5('abc')", "md5(单参)"),
        ]
        for expr, label in tests:
            try:
                v = page.evaluate("() => { try { return %s } catch(e) { return 'ERR ' + e.message } }" % expr)
                print("  %-30s = %s" % (label, str(v)[:80]))
            except Exception as e:
                print("  %-30s ERR %s" % (label, str(e)[:50]))

        # 正常登录一次
        print()
        print("=== 正常登录 ===")
        try:
            page.fill("#username", USER, timeout=6000)
            page.fill("#password", PWD, timeout=6000)
            try:
                page.click("#login-account", timeout=3000)
            except Exception:
                page.keyboard.press("Enter")
            page.wait_for_timeout(5000)
        except Exception as e:
            print("  失败:", str(e)[:80])

        browser.close()

    params = cap.get("params") or {}
    token = (cap.get("token_json") or {}).get("challenge")
    if params and token:
        print()
        print("=== 抓到的关键值 ===")
        print("  token  =", token)
        print("  hmd5   =", (params.get("password") or "").replace("{MD5}", ""))
        print("  ip     =", params.get("ip"))
        print()
        print("  => 需要满足: md5(<password>, token) = 上面的 hmd5")


main()
