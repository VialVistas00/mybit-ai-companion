# -*- coding: utf-8 -*-
"""
在浏览器里直接调用页面的加密函数，用最小输入反推 xxtea 行为
思路：拦截 XHR/fetch，修改 info 参数，从服务端响应反推
更简单：直接找 Portal 实例上的 _encodeUserInfo 私有方法
"""
import json
import sys
import time
from urllib.parse import urlparse, parse_qsl

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False,
                                args=["--ignore-certificate-errors"])
    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()
    page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
    page.wait_for_timeout(3000)

    print("=== 检查 Portal 全局对象 ===")
    r = page.evaluate("""() => {
        try {
            var t = typeof Portal;
            var info = '';
            if (typeof Portal !== 'undefined' && Portal) {
                info = 'type=' + t;
            }
            return info + ' | _setPortalInfo=' + typeof _setPortalInfo;
        } catch(e) { return 'ERR ' + e.message }
    }""")
    print("  ", r)

    # 关键：页面里有没有暴露 portal 实例？看看 _setPortalInfo 是什么
    print()
    print("=== _setPortalInfo 源码 ===")
    try:
        src = page.evaluate("() => { try { return _setPortalInfo.toString() } catch(e){ return 'ERR' } }")
        print(src[:800])
    except Exception as e:
        print(" ", e)

    # 找页面上能产生 info 的实际调用点，在 window 上打补丁捕获
    print()
    print("=== 打补丁捕获 encodeUserInfo 调用 ===")
    hook = """
    () => {
        window.__captured = [];
        if (typeof Portal !== 'undefined' && Portal && Portal.prototype) {
            // 遍历原型链找私有字段
            return 'Portal.prototype keys: ' + Object.getOwnPropertyNames(Portal.prototype).join(',');
        }
        return 'no proto';
    }
    """
    try:
        print("  ", page.evaluate(hook))
    except Exception as e:
        print("  ", e)

    browser.close()
