# -*- coding: utf-8 -*-
"""验证 C(token, pwd) 是否是 HMAC-MD5，或某种带 key 的 md5"""
import hashlib
import hmac
import time

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False,
                                args=["--ignore-certificate-errors"])
    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()
    page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
    page.wait_for_timeout(2500)

    # 取几个样本
    samples = []
    tests = [("aaa", "bbb"), ("password123", "abc"), ("P", "T")]
    for pwd, tok in tests:
        v = page.evaluate("() => md5('%s','%s')" % (pwd, tok))
        samples.append((pwd, tok, v))
        print("md5(%r, %r) = %s" % (pwd, tok, v))

    # 看 C 的源码
    try:
        src = page.evaluate("() => { try { return C.toString() } catch(e) { return 'ERR' } }")
        print()
        print("=== C 函数 ===")
        print(src[:600])
    except Exception:
        pass
    try:
        src = page.evaluate("() => { try { return s.toString() } catch(e) { return 'ERR' } }")
        print()
        print("=== s 函数 ===")
        print(src[:600])
    except Exception:
        pass
    try:
        src = page.evaluate("() => { try { return p.toString() } catch(e) { return 'ERR' } }")
        print()
        print("=== p 函数 ===")
        print(src[:600])
    except Exception:
        pass
    try:
        src = page.evaluate("() => { try { return m.toString() } catch(e) { return 'ERR' } }")
        print()
        print("=== m 函数 ===")
        print(src[:600])
    except Exception:
        pass

    browser.close()

print()
print("=" * 60)
print("对照各种猜测：")
for pwd, tok, real in samples:
    print("样本 pwd=%r token=%r" % (pwd, tok))
    print("  真实     :", real)
    print("  md5(p+t) :", hashlib.md5((pwd + tok).encode()).hexdigest())
    print("  md5(t+p) :", hashlib.md5((tok + pwd).encode()).hexdigest())
    print("  hmac(p,t):", hmac.new(tok.encode(), pwd.encode(), hashlib.md5).hexdigest())
    print("  hmac(t,p):", hmac.new(pwd.encode(), tok.encode(), hashlib.md5).hexdigest())
    print()
