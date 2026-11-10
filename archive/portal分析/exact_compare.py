# -*- coding: utf-8 -*-
"""
用 Playwright 在同一时刻抓包，把浏览器成功时的 hmd5 立刻用我的算法复算
消除 token 时效带来的干扰，精确对比
"""
import hashlib
import json
import sys
import time
from urllib.parse import urlparse, parse_qsl

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S

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
                    cap["token"] = json.loads(t[a:b + 1]).get("challenge")
                except Exception:
                    pass

        def on_req(req):
            if "cgi-bin/srun_portal" in req.url and "action=login" in req.url:
                cap["params"] = dict(parse_qsl(urlparse(req.url).query, keep_blank_values=True))

        page.on("response", on_resp)
        page.on("request", on_req)

        page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
        page.wait_for_timeout(3000)
        print("页面 URL:", page.url[:90])

        ins = page.query_selector_all("input")
        if not ins:
            print("不在登录页")
            browser.close()
            return

        page.fill("#username", USER, timeout=6000)
        page.fill("#password", PWD, timeout=6000)
        try:
            page.click("#login-account", timeout=3000)
        except Exception:
            page.keyboard.press("Enter")
        page.wait_for_timeout(5000)
        browser.close()

    token = cap.get("token")
    params = cap.get("params") or {}

    if not token or not params:
        print("抓取失败")
        return

    real_hmd5 = (params.get("password") or "").replace("{MD5}", "")
    ip = params.get("ip")

    print()
    print("=" * 62)
    print("token :", token)
    print("ip    :", ip)
    print("浏览器 hmd5:", real_hmd5)
    print()
    print("我的 HMAC  :", S.hmac_md5_hex(token, PWD))
    print("匹配:", S.hmac_md5_hex(token, PWD) == real_hmd5)
    print()

    # 如果匹配，再看 chksum
    my_hmd5 = S.hmac_md5_hex(token, PWD)
    info_b = (params.get("info") or "").replace("{SRBX1}", "")
    plain = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, ip)
    my_info = "{SRBX1}" + S.b64(S.xencode(plain, token))
    print("info 一致:", my_info == params.get("info"))
    print("  真实:", (params.get("info") or "")[:60])
    print("  我的:", my_info[:60])

    # chksum 用真实的 info 复算（排除 info 影响）
    ck_with_real_info = S.sha1(token + USER + token + real_hmd5 + token + "1" + token + ip
                               + token + "200" + token + "1" + token + params.get("info"))
    print()
    print("chksum(用真实info+真实hmd5):", ck_with_real_info)
    print("chksum(浏览器):            ", params.get("chksum"))
    print("匹配:", ck_with_real_info == params.get("chksum"))

    print()
    print("完整参数:")
    for k in ("action", "username", "os", "name", "nas_ip", "double_stack",
              "ac_id", "ip", "n", "type", "captchaVal", "ap_id", "ap_ip", "mac"):
        if k in params:
            print("  %-14s = %r" % (k, params[k]))


main()
