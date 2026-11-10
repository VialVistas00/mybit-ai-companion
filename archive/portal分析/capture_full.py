# -*- coding: utf-8 -*-
"""抓取浏览器登录请求的完整 URL，逐字段对比"""
import json

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"

full_url = []


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False,
                                    args=["--ignore-certificate-errors"])
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        def on_request(req):
            if "cgi-bin/srun_portal" in req.url:
                full_url.append(req.url)

        page.on("request", on_request)
        page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=30000)
        page.wait_for_timeout(2500)
        page.fill("#username", USER, timeout=8000)
        page.fill("#password", PWD, timeout=8000)
        try:
            page.click("#login-account", timeout=4000)
        except Exception:
            page.keyboard.press("Enter")
        page.wait_for_timeout(6000)
        browser.close()

    if not full_url:
        print("没抓到登录请求")
        return

    url = full_url[0]
    print("=" * 70)
    print("完整 URL（截断 chunk 部分）:")
    print(url[:1200])
    print()
    print("=" * 70)
    print("参数逐个拆解:")
    from urllib.parse import urlparse, parse_qsl, unquote
    q = urlparse(url).query
    for k, v in parse_qsl(q, keep_blank_values=True):
        if k == "info":
            print("  info (长度 %d):" % len(v))
            print("     " + v)
        elif k == "chksum":
            print("  chksum = %s" % v)
        elif k == "password":
            print("  password = %s" % v)
        else:
            print("  %-14s = %s" % (k, v))

    with open(r"D:\数据文件\上课\信电导论\开发板\_scratch\login_url.txt", "w",
              encoding="utf-8") as f:
        f.write(url)
    print("\n已保存完整 URL")


main()
