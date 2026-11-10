# -*- coding: utf-8 -*-
"""彻底注销：试多种注销接口，直到页面回到登录页"""
import json
import time

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"

LOGOUTS = [
    "http://%s/cgi-bin/srun_portal?action=logout&callback=cb" % PORTAL,
    "http://%s/cgi-bin/srun_portal?action=logout&callback=cb&ac_id=1" % PORTAL,
    "http://%s/srun_portal_pc?ac_id=1&theme=pro&action=logout" % PORTAL,
    "https://%s:8800/site/logout" % PORTAL,
]

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False,
                                args=["--ignore-certificate-errors"])
    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()

    for u in LOGOUTS:
        try:
            page.goto(u, timeout=15000)
            page.wait_for_timeout(2000)
            txt = page.inner_text("body")[:150].replace("\n", " ")
            print("注销 %-60s" % u[:58])
            print("   -> %s" % txt[:120])
        except Exception as e:
            print("注销 %-60s 失败 %s" % (u[:58], str(e)[:50]))

    print()
    print("=== 检查是否回到登录页 ===")
    page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
    page.wait_for_timeout(3000)
    print("  URL:", page.url[:100])
    inputs = page.query_selector_all("input")
    print("  input 数:", len(inputs))
    for e in inputs[:5]:
        print("   ", e.evaluate("el => ({id: el.id, type: el.type})"))

    # 如果还在成功页，看页面显示什么
    if len(inputs) == 0:
        print()
        print("  页面文字:")
        print("  " + page.inner_text("body")[:300].replace("\n", " | "))

    browser.close()
