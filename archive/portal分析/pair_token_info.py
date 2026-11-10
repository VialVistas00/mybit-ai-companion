# -*- coding: utf-8 -*-
"""
精确配对：把「浏览器发出的 token」和「它算出的 info」绑定在一起
方法：hook 页面的加密调用点，记录 (token, 明文, 密文)
"""
import json
import sys
import time

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_ACCOUNT"
PWD = "YOUR_PASSWORD"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False,
                                args=["--ignore-certificate-errors"])
    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()

    # hook base64.encode，同时记录当时的 token（从最近的 get_challenge 响应拿）
    page.add_init_script("""
    (function(){
        window.__captured = [];
        window.__lastToken = null;
        // 拦截 fetch
        var of = window.fetch;
        if (of) {
            window.fetch = function() {
                var url = arguments[0];
                return of.apply(this, arguments).then(function(resp){
                    if (typeof url === 'string' && url.indexOf('get_challenge') >= 0) {
                        return resp.clone().text().then(function(t){
                            var a = t.indexOf('{'), b = t.lastIndexOf('}');
                            try {
                                window.__lastToken = JSON.parse(t.substring(a, b+1)).challenge;
                            } catch(e) {}
                            return resp;
                        });
                    }
                    return resp;
                });
            };
        }
        // JSON.stringify hook 记录明文
        var ojs = JSON.stringify;
        window.__lastInfoPlain = null;
        JSON.stringify = function(o) {
            var out = ojs.apply(this, arguments);
            try {
                if (out && out.indexOf('enc_ver') >= 0) window.__lastInfoPlain = out;
            } catch(e) {}
            return out;
        };
    })();
    """)

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

    token = page.evaluate("() => window.__lastToken")
    plain = page.evaluate("() => window.__lastInfoPlain")
    browser.close()

print("token:", token)
print("明文 :", plain)
print()

if token and plain:
    sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
    import srun_client as S
    mine = S.b64(S.xencode(plain, token))
    print("我算的密文:", mine[:80])
    print()
    print("明文长度:", len(plain))
else:
    print("抓取不完整")
