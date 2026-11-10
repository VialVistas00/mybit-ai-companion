# -*- coding: utf-8 -*-
"""
用浏览器真实登录，截取结果页面文字
用途：确认 YOUR_STUDENT_ID / YOUR_PASSWORD 到底能不能登录成功
"""
import json
import time

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"

results = {}


def run(user, pwd, label):
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False,
                                    args=["--ignore-certificate-errors"])
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        resp_data = {}

        def on_response(resp):
            if "cgi-bin/srun_portal" in resp.url and "action=login" in resp.url:
                try:
                    resp_data["body"] = resp.text()
                except Exception:
                    pass

        page.on("response", on_response)
        try:
            page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
            page.wait_for_timeout(2000)
            page.fill("#username", user, timeout=6000)
            page.fill("#password", pwd, timeout=6000)
            try:
                page.click("#login-account", timeout=3000)
            except Exception:
                page.keyboard.press("Enter")
            page.wait_for_timeout(5000)
            url_now = page.url
            try:
                txt = page.inner_text("body")[:500]
            except Exception:
                txt = "(读不到)"
        except Exception as e:
            url_now = "ERR " + str(e)[:60]
            txt = ""

        browser.close()

    body = resp_data.get("body", "")
    a, b = body.find("{"), body.rfind("}")
    parsed = None
    if a >= 0:
        try:
            parsed = json.loads(body[a:b + 1])
        except Exception:
            pass

    print("=" * 60)
    print("测试:", label, " 账号:", user, " 密码:", pwd)
    print("  最终 URL:", url_now[:100])
    if parsed:
        print("  error    :", parsed.get("error"))
        print("  error_msg:", parsed.get("error_msg"))
        print("  res      :", parsed.get("res"))
    else:
        print("  响应体:", body[:200])
    print("  页面文字:", txt[:200].replace("\n", " "))


run(USER, PWD, "原样小写")
time.sleep(2)
run(USER, PWD.upper(), "全大写")
