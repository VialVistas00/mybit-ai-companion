# -*- coding: utf-8 -*-
"""
关键：hook String 构造，捕获 info 明文
info 生成时必定出现明文 JSON 字符串，用 Proxy 拦截 String 原型方法
更简单：hook btoa，因为 base64 编码必然经过它
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

    # hook btoa：打印每次编码的输入（用二进制字符串形式）
    page.add_init_script("""
    (function(){
        window.__b64log = [];
        var orig = window.btoa;
        window.btoa = function(s){
            try {
                if (s && s.length > 20) {
                    window.__b64log.push({
                        len: s.length,
                        hex: Array.from(s).map(c => c.charCodeAt(0).toString(16).padStart(2,'0')).join('').substring(0, 200),
                        raw: (function(){
                            try { return decodeURIComponent(escape(s)).substring(0, 200) } catch(e) { return s.substring(0,200) }
                        })()
                    });
                }
            } catch(e) {}
            return orig.apply(this, arguments);
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

    logs = page.evaluate("() => window.__b64log || []")
    print("=== btoa 调用记录 (%d 条) ===" % len(logs))
    for i, l in enumerate(logs[:8]):
        print()
        print("[%d] len=%d" % (i, l["len"]))
        print("   hex:", l["hex"][:160])
        print("   raw:", l["raw"][:160])

    browser.close()
