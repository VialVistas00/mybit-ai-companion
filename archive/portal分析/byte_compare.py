# -*- coding: utf-8 -*-
"""让浏览器用新 token 生成 info，我同时用同样输入加密，逐个字节对比"""
import base64
import json
import sys
from urllib.parse import urlparse, parse_qsl

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
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
        page.wait_for_timeout(5000)
    browser.close()

token = cap.get("token")
params = cap.get("params") or {}
ip = params.get("ip")
real_info = params.get("info") or ""

plain = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, ip)
mine = "{SRBX1}" + S.b64(S.xencode(plain, token))

print("token:", token)
print("明文 :", plain)
print()
print("浏览器:", real_info)
print("我的  :", mine)
print()
print("相同:", real_info == mine)

real_raw = base64.b64decode(real_info.replace("{SRBX1}", ""))
mine_raw = base64.b64decode(mine.replace("{SRBX1}", ""))
print()
print("原始字节长度: 真实 %d / 我的 %d" % (len(real_raw), len(mine_raw)))
print()
print("真实 hex:", real_raw.hex())
print("我的 hex:", mine_raw.hex())

# 逐字节差异位置
if len(real_raw) == len(mine_raw):
    diff = [i for i in range(len(real_raw)) if real_raw[i] != mine_raw[i]]
    print()
    print("差异字节数:", len(diff), "/", len(real_raw))
    print("前 10 个差异位置:", diff[:10])
