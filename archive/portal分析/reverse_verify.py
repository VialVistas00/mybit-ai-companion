# -*- coding: utf-8 -*-
"""
手握真实数据反推：
抓一次完整的 token + hmd5 + chksum + info，然后验证我的计算式
如果 chksum 对不上，就能确定公式哪里错了
"""
import base64
import json
import sys
import time
from urllib.parse import urlparse, parse_qsl

from playwright.sync_api import sync_playwright

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S

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

        page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
        page.wait_for_timeout(2500)

        # 如果已在成功页，先注销
        if "success" in page.url:
            print("当前在成功页，先尝试注销...")
            try:
                page.click("text=注销", timeout=3000)
                page.wait_for_timeout(4000)
            except Exception:
                page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=20000)
                page.wait_for_timeout(2500)

        try:
            page.fill("#username", USER, timeout=6000)
            page.fill("#password", PWD, timeout=6000)
            try:
                page.click("#login-account", timeout=3000)
            except Exception:
                page.keyboard.press("Enter")
            page.wait_for_timeout(5000)
        except Exception as e:
            print("填表失败:", str(e)[:100])

        browser.close()

    token = (cap.get("token_json") or {}).get("challenge")
    params = cap.get("params") or {}

    print()
    print("=== 抓到的真实数据 ===")
    print("  token  :", (token or "")[:40])
    print("  ip     :", params.get("ip"))
    print("  hmd5   :", (params.get("password") or "")[:40])
    print("  chksum :", params.get("chksum"))
    print("  info   :", (params.get("info") or "")[:50], "...")

    if not token or not params:
        print("数据不完整")
        return

    real_hmd5 = (params["password"] or "").replace("{MD5}", "")
    real_chksum = params["chksum"]
    real_info = params["info"]
    ip = params["ip"]

    print()
    print("=== 验证 hmd5 = md5(password + token) ===")
    import hashlib
    my_hmd5 = hashlib.md5((PWD + token).encode()).hexdigest()
    print("  真实:", real_hmd5)
    print("  我的:", my_hmd5)
    print("  一致:", real_hmd5 == my_hmd5)

    print()
    print("=== 验证 chksum 公式 ===")
    # 公式：sha1(token+username+token+hmd5+token+acid+token+ip+token+n+token+type+token+info)
    user = params.get("username")
    acid = params.get("ac_id")
    n = params.get("n")
    typ = params.get("type")
    src = (token + user + token + real_hmd5 + token + acid + token + ip
           + token + n + token + typ + token + real_info)
    my_ck = hashlib.sha1(src.encode()).hexdigest()
    print("  真实:", real_chksum)
    print("  我的:", my_ck)
    print("  一致:", real_chksum == my_ck)

    print()
    print("=== 验证 info 是否能被我的 xencode 复现 ===")
    # 明文假定
    plain = '{"username":"%s","password":"%s","ip":"%s","acid":"%s","enc_ver":"srun_bx1"}' % (
        user, PWD, ip, acid)
    my_info = "{SRBX1}" + S.b64(S.xencode(plain, token))
    print("  真实长度:", len(real_info), " 我的长度:", len(my_info))
    print("  一致:", real_info == my_info)
    print("  我的明文:", plain)


main()
