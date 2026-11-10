# -*- coding: utf-8 -*-
"""导出 md5/sha1 源码（先注销确保在登录页）"""
import time

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False,
                                    args=["--ignore-certificate-errors"])
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        page.goto("http://%s/cgi-bin/srun_portal?action=logout&callback=cb" % PORTAL, timeout=15000)
        page.wait_for_timeout(2000)
        page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
        page.wait_for_timeout(3000)
        print("当前 URL:", page.url[:100])

        src = page.evaluate("() => md5.toString()")
        print()
        print("=" * 66)
        print("### md5 函数源码")
        print("=" * 66)
        print(src[:2500])

        print()
        print("=" * 66)
        print("### sha1 函数源码")
        print("=" * 66)
        s2 = page.evaluate("() => sha1.toString()")
        print(s2[:800])

        print()
        print("=" * 66)
        print("### 用不同输入测 md5，推断拼接规则")
        print("=" * 66)
        tests = [
            ("md5('aaa','bbb')", "判断是否 md5(pwd+token)"),
            ("md5('aaabbb')", "对照 md5('aaa'+'bbb')"),
            ("md5('bbbaaa')", "对照 md5('bbb'+'aaa')"),
        ]
        for expr, note in tests:
            try:
                v = page.evaluate("() => { try { return %s } catch(e){ return 'ERR '+e.message } }" % expr)
                print("  %-24s = %-34s  # %s" % (expr, v, note))
            except Exception as e:
                print("  %-24s ERR %s" % (expr, str(e)[:40]))

        browser.close()


main()
