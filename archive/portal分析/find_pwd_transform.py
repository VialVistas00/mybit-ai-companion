# -*- coding: utf-8 -*-
"""
定位 hmd5 差异：页面是否对密码做了处理？
用真实 token，穷举可能的密码变形，找出能对上 real_hmd5 的那个
"""
import hashlib
import json
import sys
import time
from urllib.parse import urlparse, parse_qsl

from playwright.sync_api import sync_playwright

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"
cap = {}


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False,
                                    args=["--ignore-certificate-errors"])
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        def on_resp(resp):
            if "get_challenge" in resp.url:
                try:
                    t = resp.text()
                    a, b = t.find("{"), t.rfind("}")
                    cap["token_json"] = json.loads(t[a:b + 1])
                except Exception:
                    pass

        def on_req(req):
            if "cgi-bin/srun_portal" in req.url and "action=login" in req.url:
                cap["params"] = dict(parse_qsl(urlparse(req.url).query, keep_blank_values=True))

        page.on("response", on_resp)
        page.on("request", on_req)

        page.goto("http://%s/cgi-bin/srun_portal?action=logout&callback=cb" % PORTAL, timeout=15000)
        page.wait_for_timeout(2000)
        page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
        page.wait_for_timeout(3000)

        inputs = page.query_selector_all("input")
        if len(inputs) == 0:
            print("不在登录页")
            browser.close()
            return

        # 关键：填入密码后，读出输入框里实际的值
        page.fill("#username", USER, timeout=6000)
        page.fill("#password", PWD, timeout=6000)
        actual_user = page.input_value("#username")
        actual_pwd = page.input_value("#password")
        print("填入并读回：")
        print("  username =", repr(actual_user))
        print("  password =", repr(actual_pwd))
        print("  密码长度:", len(actual_pwd), " 期望长度:", len(PWD))
        print("  是否相同:", actual_pwd == PWD)

        try:
            page.click("#login-account", timeout=3000)
        except Exception:
            page.keyboard.press("Enter")
        page.wait_for_timeout(5000)
        browser.close()

    token = (cap.get("token_json") or {}).get("challenge")
    params = cap.get("params") or {}
    if not token or not params:
        print("抓取失败")
        return

    real_hmd5 = (params["password"] or "").replace("{MD5}", "")
    print()
    print("=== 用真实 token 穷举密码变形 ===")
    print("  token :", token)
    print("  真实 hmd5:", real_hmd5)

    candidates = {
        "PWD": PWD,
        "PWD.upper()": PWD.upper(),
        "PWD.lower()": PWD.lower(),
        "PWD.strip()": PWD.strip(),
        "''": "",
        "utf8先encode再md5": PWD,
    }
    found = None
    for label, pwd in candidates.items():
        h = hashlib.md5((pwd + token).encode()).hexdigest()
        match = "  <<< 匹配" if h == real_hmd5 else ""
        print("  %-18s -> %s%s" % (label, h[:32], match))
        if h == real_hmd5:
            found = (label, pwd)

    if found:
        print()
        print("  *** 找到匹配的密码变形: %s = %r ***" % found)
    else:
        print()
        print("  所有常见变形都不匹配")
        print("  可能：页面在提交前对密码做了额外处理（如 trim / 编码 / 混淆）")


main()
