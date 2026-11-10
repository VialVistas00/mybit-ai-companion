# -*- coding: utf-8 -*-
"""
核心对比实验：
浏览器密文 hex = be0177956102e43c...（104 字节）
我需要同 token 同明文的密文来对比
做法：一次性抓 token + 密文，然后立刻用 Python 复算
"""
import base64
import json
import sys
import time

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

    page.on("response", on_resp)
    page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
    page.wait_for_timeout(3000)

    # hook base64
    page.evaluate("""() => {
        window.__log = [];
        var orig = $.base64.encode;
        $.base64.encode = function(s) {
            var out = orig.apply(this, arguments);
            try {
                var hex = '';
                for (var i = 0; i < s.length; i++) {
                    hex += s.charCodeAt(i).toString(16).padStart(2, '0');
                }
                window.__log.push({inLen: s.length, inHex: hex});
            } catch(e) {}
            return out;
        };
        return 'ok';
    }""")

    if page.query_selector_all("input"):
        page.fill("#username", USER, timeout=6000)
        page.fill("#password", PWD, timeout=6000)
        try:
            page.click("#login-account", timeout=3000)
        except Exception:
            page.keyboard.press("Enter")
        page.wait_for_timeout(5000)

    logs = page.evaluate("() => window.__log || []")
    browser.close()

token = cap.get("token")
print("token:", token)

if not logs:
    print("没抓到 base64 调用")
    sys.exit(1)

browser_hex = logs[0]["inHex"]
browser_bytes = bytes.fromhex(browser_hex)
print("浏览器密文长度:", len(browser_bytes))
print("浏览器密文:", browser_hex[:80], "...")
print()

ip = "CLIENT_IP"
plain = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, ip)
print("明文:", plain)
print("明文长:", len(plain))
print()

mine = S.xencode(plain, token)
print("我的密文长度:", len(mine))
print("我的密文:", mine.hex()[:80], "...")
print()

print("长度相同:", len(mine) == len(browser_bytes))
if len(mine) == len(browser_bytes):
    diff = [i for i in range(len(mine)) if mine[i] != browser_bytes[i]]
    print("差异字节数:", len(diff), "/", len(mine))
    if diff:
        print("前 16 个差异位置:", diff[:16])
        # 看第一个差异
        d0 = diff[0]
        print("首个差异 @ %d: 浏览器=%02x 我的=%02x" % (d0, browser_bytes[d0], mine[d0]))
