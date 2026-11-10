# -*- coding: utf-8 -*-
"""一次性抓取 token + info，存下来后解密对比"""
import base64
import json
import sys
from urllib.parse import urlparse, parse_qsl

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"

token_box = {}
info_box = {}


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False,
                                    args=["--ignore-certificate-errors"])
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        def on_response(resp):
            if "get_challenge" in resp.url:
                try:
                    txt = resp.text()
                    a, b = txt.find("{"), txt.rfind("}")
                    j = json.loads(txt[a:b + 1])
                    token_box["token"] = j.get("challenge")
                    token_box["ip"] = j.get("client_ip")
                except Exception:
                    pass

        def on_request(req):
            if "cgi-bin/srun_portal" in req.url and "action=login" in req.url:
                q = urlparse(req.url).query
                info_box.update(dict(parse_qsl(q, keep_blank_values=True)))

        page.on("response", on_response)
        page.on("request", on_request)

        page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=30000)
        page.wait_for_timeout(2500)
        page.fill("#username", USER)
        page.fill("#password", PWD)
        try:
            page.click("#login-account", timeout=4000)
        except Exception:
            page.keyboard.press("Enter")
        page.wait_for_timeout(6000)
        browser.close()

    print("token:", (token_box.get("token") or "")[:30], "...")
    print("ip   :", token_box.get("ip"))
    print("info :", (info_box.get("info") or "")[:60], "...")
    print("hmd5 :", (info_box.get("password") or "")[:40])

    if not token_box.get("token") or not info_box.get("info"):
        print("抓取不完整")
        return

    # 解密
    sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
    import srun_client as S

    def xxtea_decode(data, key):
        pwd = S._sencode(data.decode("latin-1"), False)
        pwdk = S._sencode(key, False)
        while len(pwdk) < 4:
            pwdk.append(0)
        n = len(pwd) - 1
        z = pwd[n]
        y = pwd[0]
        c = 0x86014019 | 0x183639A0
        d = (6 + 52 // (n + 1)) * c
        qq = int(6 + 52 / (n + 1))
        while qq > 0:
            e = (d >> 2) & 3
            p2 = n
            while p2 > 0:
                z = pwd[p2 - 1]
                m = (z >> 5) ^ (y << 2)
                m = m + (((y >> 3) ^ (z << 4)) ^ (d ^ y))
                m = m + (pwdk[(p2 & 3) ^ e] ^ z)
                pwd[p2] = (pwd[p2] - m) & 0xFFFFFFFF
                y = pwd[p2]
                p2 -= 1
            z = pwd[n]
            m = (z >> 5) ^ (y << 2)
            m = m + (((y >> 3) ^ (z << 4)) ^ (d ^ y))
            m = m + (pwdk[(0 & 3) ^ e] ^ z)
            pwd[0] = (pwd[0] - m) & 0xFFFFFFFF
            y = pwd[0]
            d = (d - c) & 0xFFFFFFFF
            qq -= 1
        return S._lencode(pwd, True)

    b64 = info_box["info"].replace("{SRBX1}", "")
    raw = base64.b64decode(b64)
    tok = token_box["token"]
    dec = xxtea_decode(raw, tok)
    print()
    print("=== 解密结果 ===")
    if dec:
        try:
            print(dec.decode("utf-8"))
        except Exception:
            print(repr(dec))
    else:
        print("解密失败（lencode 校验不过）")


main()
