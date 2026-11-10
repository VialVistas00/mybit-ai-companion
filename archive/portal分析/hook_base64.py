# -*- coding: utf-8 -*-
"""hook $.base64.encode 和 setAlpha，捕获 info 加密前后的数据"""
import json
import sys
import time

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False,
                                args=["--ignore-certificate-errors"])
    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()
    page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
    page.wait_for_timeout(3000)

    # 页面加载后再 hook（此时 $ 已存在）
    r = page.evaluate("""() => {
        try {
            window.__log = [];
            var orig = $.base64.encode;
            $.base64.encode = function(s) {
                var out = orig.apply(this, arguments);
                try {
                    var hex = '';
                    for (var i = 0; i < Math.min(s.length, 120); i++) {
                        hex += s.charCodeAt(i).toString(16).padStart(2, '0');
                    }
                    window.__log.push({inLen: s.length, outLen: out.length, inHex: hex, out: out.substring(0,80)});
                } catch(e) {}
                return out;
            };
            return 'hooked ok';
        } catch(e) { return 'ERR ' + e.message }
    }""")
    print("hook:", r)

    if page.query_selector_all("input"):
        page.fill("#username", USER, timeout=6000)
        page.fill("#password", PWD, timeout=6000)
        try:
            page.click("#login-account", timeout=3000)
        except Exception:
            page.keyboard.press("Enter")
        page.wait_for_timeout(5000)

    logs = page.evaluate("() => window.__log || []")
    print()
    print("=== base64.encode 调用 (%d 条) ===" % len(logs))
    for i, l in enumerate(logs):
        print()
        print("[%d] 输入 len=%d 输出 len=%d" % (i, l["inLen"], l["outLen"]))
        print("   输入 hex:", l["inHex"][:160])
        print("   输出:", l["out"])

    browser.close()
