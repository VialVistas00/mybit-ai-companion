# -*- coding: utf-8 -*-
"""
直接在浏览器里拿到真实的 info 生成结果，用最小输入反推 xxtea
策略：注入 hook，在页面生成 info 的那一刻把明文和密文都抓下来
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

    page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
    page.wait_for_timeout(3000)

    # 关键：遍历所有 script 内容，找含 xencode / encode 的函数体
    print("=== 遍历所有脚本找加密实现 ===")
    found = page.evaluate("""() => {
        var out = [];
        var scripts = document.querySelectorAll('script');
        for (var i = 0; i < scripts.length; i++) {
            var t = scripts[i].textContent || '';
            if (!t) continue;
            // 找 SRBX1 附近
            var idx = t.indexOf('SRBX1');
            if (idx >= 0) {
                out.push({i: i, len: t.length, seg: t.substring(Math.max(0, idx-400), idx+200)});
            }
        }
        // 也看外部 js 是否已加载到 window 上
        return out;
    }""")
    print("  找到 %d 处" % len(found))
    for f in found[:3]:
        print()
        print("  [script %d, len=%d]" % (f["i"], f["len"]))
        print("  " + f["seg"].replace("\n", " ")[:700])

    # 另一个思路：看 Portal.prototype 上是否有能间接调用的
    print()
    print("=== 尝试调用 Portal.prototype.getUserPassword ===")
    try:
        r = page.evaluate("""() => {
            try {
                var s = Portal.prototype.getUserPassword.toString();
                return s.substring(0, 300);
            } catch(e) { return 'ERR ' + e.message }
        }""")
        print("  " + r.replace("\n", " "))
    except Exception as e:
        print("  ", e)

    browser.close()
