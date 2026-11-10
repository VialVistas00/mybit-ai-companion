# -*- coding: utf-8 -*-
"""检查当前认证页面结构（可能已被重定向到成功页或换了模板）"""
import time

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False,
                                args=["--ignore-certificate-errors"])
    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()

    page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=30000)
    page.wait_for_timeout(3000)

    print("当前 URL:", page.url)
    print()
    print("=== 页面标题 ===")
    try:
        print(" ", page.title())
    except Exception as e:
        print(" ", e)

    print()
    print("=== 所有 input 元素 ===")
    try:
        els = page.query_selector_all("input")
        print("  共 %d 个" % len(els))
        for e in els[:10]:
            info = e.evaluate("el => ({tag: el.tagName, type: el.type, id: el.id, name: el.name, ph: el.placeholder})")
            print("   ", info)
    except Exception as e:
        print("  ", e)

    print()
    print("=== 页面文字前 600 字 ===")
    try:
        print(page.inner_text("body")[:600])
    except Exception as e:
        print(" ", e)

    page.screenshot(path=r"D:\数据文件\上课\信电导论\开发板\_scratch\current_page.png")
    print()
    print("截图已保存")

    time.sleep(2)
    browser.close()
