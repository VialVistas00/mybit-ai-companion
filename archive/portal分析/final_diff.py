# -*- coding: utf-8 -*-
"""
决定性对比：拦截浏览器的 login 请求，用同一 token 用我的算法复算全部参数
逐项比对 hmd5 / info / chksum，找出唯一差异
"""
import json
import sys
import time
from urllib.parse import urlparse, parse_qsl

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_ACCOUNT"
PWD = "YOUR_PASSWORD"

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S

cap = {}

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
    if page.query_selector_all("input"):
        page.fill("#username", USER, timeout=6000)
        page.fill("#password", PWD, timeout=6000)
        try:
            page.click("#login-account", timeout=3000)
        except Exception:
            page.keyboard.press("Enter")
        page.wait_for_timeout(6000)
    browser.close()

token = cap.get("token")
p_ = cap.get("params") or {}
if not token or not p_:
    print("抓取失败")
    sys.exit(1)

ip = p_["ip"]
real_hmd5 = p_["password"].replace("{MD5}", "")
real_info = p_["info"]
real_chksum = p_["chksum"]

my_hmd5 = S.hmac_md5_hex(token, PWD)
info_plain = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, ip)
my_info = "{SRBX1}" + S.b64(S.xencode(info_plain, token))
my_chk = S.sha1(token + USER + token + real_hmd5 + token + "1" + token + ip
                + token + "200" + token + "1" + token + real_info)

print("token:", token)
print()
print("--- hmd5 ---")
print("  浏览器:", real_hmd5)
print("  我的  :", my_hmd5)
print("  一致  :", real_hmd5 == my_hmd5)
print()
print("--- info ---")
print("  浏览器:", real_info[:60], "...")
print("  我的  :", my_info[:60], "...")
print("  一致  :", real_info == my_info)
print()
print("--- chksum（用真实 info 复算）---")
print("  浏览器:", real_chksum)
print("  我的  :", my_chk)
print("  一致  :", real_chksum == my_chk)
print()
print("--- 参数全表 ---")
for k, v in p_.items():
    if k in ("info", "chksum", "password", "callback", "_"):
        continue
    print("  %-14s = %r" % (k, v))
