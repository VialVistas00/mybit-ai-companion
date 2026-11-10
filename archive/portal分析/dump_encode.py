# -*- coding: utf-8 -*-
"""在浏览器里导出真正的 xxtea encode 函数源码"""
import time

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False,
                                args=["--ignore-certificate-errors"])
    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()
    page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
    page.wait_for_timeout(3000)

    # 探测全局函数
    print("=== 全局函数列表 ===")
    names = page.evaluate("() => Object.getOwnPropertyNames(window).filter(n => { try { return typeof window[n] === 'function' && window[n].toString().length < 3000 } catch(e) { return false } })")
    cand = [n for n in names if any(k in n.lower() for k in ("enc", "tea", "code", "b64", "base64", "md5", "sha"))]
    print("  可疑候选:", cand[:20])

    for n in cand[:10]:
        try:
            src = page.evaluate("(n) => { try { return window[n].toString() } catch(e) { return 'ERR' } }", n)
            print()
            print("### %s" % n)
            print(src[:600])
        except Exception:
            pass

    # 直接找 Portal 实例上的 encodeUserInfo
    print()
    print("=== Portal 实例方法 ===")
    try:
        proto = page.evaluate("""() => {
            try {
                var names = [];
                var o = Portal;
                while (o && o !== Object.prototype) {
                    names = names.concat(Object.getOwnPropertyNames(o));
                    o = Object.getPrototypeOf(o);
                }
                return names.join(',');
            } catch(e) { return 'ERR ' + e.message }
        }""")
        print("  ", str(proto)[:800])
    except Exception as e:
        print("  ", e)

    browser.close()
