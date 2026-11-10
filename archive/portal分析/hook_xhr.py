# -*- coding: utf-8 -*-
"""
关键实验：在页面里 hook 住 info 字符串的生成
方法：重写 String.prototype 或拦截 ajax，把 info 传给服务端前截获
最直接：拦截 XMLHttpRequest / fetch / jQuery.jsonp
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

    # 注入 hook：拦截 jQuery.getJSON / jsonp
    page.add_init_script("""
    (function(){
        window.__req = [];
        var origOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(m, u){
            window.__req.push({method: m, url: u});
            return origOpen.apply(this, arguments);
        };
        // 拦截图片/脚本请求（jsonp 用的是 script 标签）
        var origCreate = document.createElement;
        document.createElement = function(tag){
            var el = origCreate.call(document, tag);
            if (String(tag).toLowerCase() === 'script') {
                var origSet = Object.getOwnPropertyDescriptor(HTMLScriptElement.prototype, 'src');
                if (origSet && origSet.set) {
                    Object.defineProperty(el, 'src', {
                        set: function(v) {
                            if (v && v.indexOf('srun_portal') >= 0) {
                                window.__req.push({type: 'script', url: v});
                            }
                            origSet.set.call(this, v);
                        },
                        get: origSet.get
                    });
                }
            }
            return el;
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

    reqs = page.evaluate("() => window.__req || []")
    print("=== 拦截到的请求 ===")
    for r in reqs:
        u = r.get("url", "")
        if "srun" in u or "cgi-bin" in u:
            print("  %s %s" % (r.get("method", r.get("type", "?")), u[:180]))

    browser.close()
