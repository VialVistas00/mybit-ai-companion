# -*- coding: utf-8 -*-
"""先注销，再回到登录页抓包"""
import json
import time
from urllib.parse import urlparse, parse_qsl

from playwright.sync_api import sync_playwright

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

        # 1. 先直接调注销接口
        print("调用注销接口...")
        try:
            ip_info = page.request.get("http://%s/cgi-bin/rad_user_info?callback=cb" % PORTAL)
            print("  当前:", ip_info.text()[:150])
        except Exception as e:
            print("  查询失败", e)

        try:
            page.goto("http://%s/cgi-bin/srun_portal?action=logout&callback=cb" % PORTAL,
                      timeout=15000)
            print("  注销响应:", page.inner_text("body")[:200])
        except Exception as e:
            print("  注销请求异常:", str(e)[:80])

        time.sleep(2)

        # 2. 回到认证页
        print("打开认证页...")
        page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
        page.wait_for_timeout(3000)
        print("  当前 URL:", page.url[:100])

        # 3. 找 input
        inputs = page.query_selector_all("input")
        print("  input 数量:", len(inputs))
        for e in inputs[:6]:
            print("   ", e.evaluate("el => ({id: el.id, type: el.type})"))

        if len(inputs) == 0:
            print("  没有登录表单，可能已在线")
            browser.close()
            return

        # 4. 登录
        try:
            page.fill("#username", USER, timeout=6000)
            page.fill("#password", PWD, timeout=6000)
            try:
                page.click("#login-account", timeout=3000)
            except Exception:
                page.keyboard.press("Enter")
            page.wait_for_timeout(5000)
            print("  最终 URL:", page.url[:100])
        except Exception as e:
            print("  填表失败:", str(e)[:120])

        browser.close()

    token = (cap.get("token_json") or {}).get("challenge")
    params = cap.get("params") or {}

    print()
    print("=== 真实数据 ===")
    if not token or not params:
        print("  抓取失败")
        return
    print("  token :", token[:40])
    print("  ip    :", params.get("ip"))
    print("  hmd5  :", (params.get("password") or "")[:42])
    print("  chksum:", params.get("chksum"))
    real_info = params.get("info", "")
    print("  info  :", real_info[:60], "...")

    import hashlib
    import sys
    sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
    import srun_client as S

    real_hmd5 = (params["password"] or "").replace("{MD5}", "")
    my_hmd5 = hashlib.md5((PWD + token).encode()).hexdigest()

    print()
    print("=== hmd5 校验 ===")
    print("  真实:", real_hmd5)
    print("  我的:", my_hmd5)
    print("  一致:", real_hmd5 == my_hmd5)

    print()
    print("=== chksum 校验 ===")
    user = params.get("username")
    acid = params.get("ac_id")
    n = params.get("n")
    typ = params.get("type")
    ip = params.get("ip")
    src = (token + user + token + real_hmd5 + token + acid + token + ip
           + token + n + token + typ + token + real_info)
    my_ck = hashlib.sha1(src.encode()).hexdigest()
    print("  真实:", params.get("chksum"))
    print("  我的:", my_ck)
    print("  一致:", params.get("chksum") == my_ck)

    print()
    print("=== info 校验 ===")
    plain = '{"username":"%s","password":"%s","ip":"%s","acid":"%s","enc_ver":"srun_bx1"}' % (
        user, PWD, ip, acid)
    my_info = "{SRBX1}" + S.b64(S.xencode(plain, token))
    print("  真实长度:", len(real_info), "我的长度:", len(my_info))
    print("  一致:", real_info == my_info)
    print("  假设明文:", plain)


main()
