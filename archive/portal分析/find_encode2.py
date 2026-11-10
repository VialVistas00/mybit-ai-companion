# -*- coding: utf-8 -*-
"""
在浏览器页面内直接调用 encode 逻辑（通过 Portal 对象的方法）
测一个极简输入，比如明文 "ABCD"，快速定位 xxtea 差异
"""
import sys
import time

from playwright.sync_api import sync_playwright

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S

PORTAL = "PORTAL_IP"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False,
                                args=["--ignore-certificate-errors"])
    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()
    page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
    page.wait_for_timeout(3000)

    # 尝试找到 encode 逻辑：搜索页面里所有含 "SRBX1" 的地方
    print("=== 搜索源码中含 SRBX1 的部分 ===")
    try:
        res = page.evaluate("""() => {
            var out = [];
            // 遍历所有 script 标签
            var scripts = document.querySelectorAll('script');
            for (var i = 0; i < scripts.length; i++) {
                var t = scripts[i].textContent || '';
                if (t.indexOf('SRBX1') >= 0) out.push('inline script ' + i + ' len=' + t.length);
            }
            // 检查已加载的全局对象
            if (typeof Utils !== 'undefined') out.push('Utils: ' + Object.keys(Utils).join(','));
            if (typeof CREATER !== 'undefined') out.push('CREATER keys: ' + Object.keys(CREATER).join(','));
            return out.join(' | ');
        }""")
        print("  ", str(res)[:600])
    except Exception as e:
        print("  ", e)

    # 直接用 Utils 里的函数
    print()
    print("=== Utils 对象 ===")
    try:
        r = page.evaluate("""() => {
            try { return JSON.stringify(Object.keys(Utils)) } catch(e) { return 'ERR ' + e.message }
        }""")
        print("  ", r[:500])
    except Exception as e:
        print("  ", e)

    # 试各种可能的 encode 函数
    print()
    print("=== 尝试调用各种 encode ===")
    tests = [
        "typeof Utils.encode",
        "typeof Utils.xencode",
        "typeof encode",
        "typeof xencode",
        "typeof tea",
        "typeof xxtea",
        "typeof Utils.md5",
        "typeof Utils.sha1",
    ]
    for t in tests:
        try:
            v = page.evaluate("() => { try { return String(%s) } catch(e) { return 'ERR' } }" % t)
            if v != "undefined":
                print("  %-24s = %s" % (t, v))
        except Exception:
            pass

    browser.close()
