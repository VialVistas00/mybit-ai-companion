# -*- coding: utf-8 -*-
"""从新版 Portal.js 提取登录参数的构造代码"""
import re
import urllib.request

URL = "http://PORTAL_IP/static/themes/pro/js/Portal.js?v=90cd879880515c55"

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
js = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
print("Portal.js 长度:", len(js))
print()

# 找 chksum 计算
print("=" * 60)
print("### chksum 相关")
for m in re.finditer(r"chksum\s*:\s*(\w+)\(([^)]*)\)", js):
    s = max(0, m.start() - 700)
    print(js[s:m.end() + 100].replace("\n", " ")[:900])
    print()

print("=" * 60)
print("### str 构造（拼接 token 的部分）")
for m in re.finditer(r"var\s+str\s*=\s*token\s*\+", js):
    s = m.start()
    print(js[s:s + 700].replace("\n", " "))
    print()

print("=" * 60)
print("### sha1 / md5 函数定义位置")
for kw in ("function sha1", "var sha1", "sha1 =", "function md5", "var md5"):
    idx = js.find(kw)
    print("  %-14s -> %s" % (kw, idx))
