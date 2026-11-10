# -*- coding: utf-8 -*-
"""在 Portal.js 里定位 sha1 / md5 / hmd5 的实现与调用"""
import re
import urllib.request

URL = "http://PORTAL_IP/static/themes/pro/js/Portal.js?v=a32e00343444a19a"
req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
js = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
print("长度", len(js))

def show(pattern, label, count=3, before=150, after=500):
    print("\n" + "=" * 68)
    print("### " + label)
    n = 0
    for m in re.finditer(pattern, js):
        s = max(0, m.start() - before)
        e = min(len(js), m.end() + after)
        print("\n--- @" + str(m.start()) + " ---")
        print(js[s:e].replace("\n", " ").replace("\r", " "))
        n += 1
        if n >= count:
            break
    if n == 0:
        print("(无命中)")

# chksum / sha1 调用
show(r"chksum:\s*sha1\([^)]*\)", "chksum: sha1(...)")
# 变量 str 的完整构造
show(r"var str = token \+ username", "str 构造", count=2, before=100, after=520)
# md5 定义
show(r"var md5\s*=|function md5\s*\(|md5:\s*function", "md5 定义", count=3, before=80, after=400)
# sha1 定义
show(r"var sha1\s*=|function sha1\s*\(|sha1:\s*function", "sha1 定义（自定义？）", count=3, before=80, after=400)
# md5(password, token) 的调用
show(r"var hmd5 = md5\(", "hmd5 调用", count=2, before=150, after=200)
