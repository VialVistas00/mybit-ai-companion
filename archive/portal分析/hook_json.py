# -*- coding: utf-8 -*-
"""
终极方案：直接 hook 住 xxtea 加密的【输入】
浏览器生成 info 时，必然调用某个加密函数处理明文 JSON
我 hook String.prototype 构造，捕获所有包含 username 的字符串
"""
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

    # hook JSON.stringify —— info 明文很可能由它生成
    page.add_init_script("""
    (function(){
        window.__jsonlog = [];
        var orig = JSON.stringify;
        JSON.stringify = function(obj) {
            var out = orig.apply(this, arguments);
            try {
                if (out && (out.indexOf('username') >= 0 || out.indexOf('enc_ver') >= 0)) {
                    window.__jsonlog.push(out);
                }
            } catch(e) {}
            return out;
        };
    })();
    """)

    page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
    page.wait_for_timeout(3000)

    if page.query_selector_all("input"):
        page.fill("#username", USER, timeout=6000)
        page.fill("#password", PWD, timeout=6000)
        try:
            page.click("#login-account", timeout=3000)
        except Exception:
            page.keyboard.press("Enter")
        page.wait_for_timeout(5000)

    logs = page.evaluate("() => window.__jsonlog || []")
    print("=== JSON.stringify 捕获 (%d 条) ===" % len(logs))
    for i, s in enumerate(logs[:5]):
        print()
        print("[%d] 长度 %d" % (i, len(s)))
        print("  " + s[:400])

    browser.close()
