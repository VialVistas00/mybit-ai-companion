# -*- coding: utf-8 -*-
"""
用固定 token + 固定明文，对比浏览器生成的 info 与我的
浏览器端通过调用页面内部的 encodeUserInfo 生成
"""
import base64
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
    if not page.query_selector_all("input"):
        print("不在登录页")
        browser.close()
        sys.exit(0)
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

print("token:", token)
print("ip   :", ip)
print("浏览器 info:", real_info)
print()

plain = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, ip)
print("假设明文:", plain)
print("明文长度:", len(plain))
print()

mine = "{SRBX1}" + S.b64(S.xencode(plain, token))
print("我的   info:", mine)
print("长度: 真实 %d / 我的 %d" % (len(real_info), len(mine)))
print()

# 解码对比
real_raw = base64.b64decode(real_info.replace("{SRBX1}", ""))
mine_raw = base64.b64decode(mine.replace("{SRBX1}", ""))
print("解码后长度: 真实 %d / 我的 %d" % (len(real_raw), len(mine_raw)))
print("真实 hex 前 32:", real_raw[:32].hex())
print("我的 hex 前 32:", mine_raw[:32].hex())
print()
print("是否相同:", real_raw == mine_raw)

# 关键：长度相同但内容不同，说明 xxtea 实现有差异
# 检查我的 lencode 是否丢了长度字节
print()
print("=== 检查明文长度对齐 ===")
n_words = (len(plain) + 3) // 4
print("  按 4 字节对齐:", n_words, "字 ->", n_words * 4, "字节")
print("  加密结果:", len(mine_raw), "字节")
print("  期望:", n_words * 4, "字节")
