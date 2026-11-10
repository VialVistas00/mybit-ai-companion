# -*- coding: utf-8 -*-
"""在 Portal.js 里找 getUserPassword 的实现"""
import re
import urllib.request

VER = "90cd879880515c55"
URL = "http://PORTAL_IP/static/themes/pro/js/Portal.js?v=" + VER

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
js = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
print("长度:", len(js))

for kw in ("getUserPassword", "userPassword", "#password", "btoa", "encrypt",
           "sha1", "hex_md5", "md5("):
    idxs = [m.start() for m in re.finditer(re.escape(kw), js)]
    print("  %-16s 出现 %d 次" % (kw, len(idxs)))

print()
print("=" * 66)
print("### getUserPassword 定义")
for m in re.finditer(r"getUserPassword[^\n]{0,40}function", js):
    s = m.start()
    print(js[s:s + 500].replace("\n", " "))
    print()

for m in re.finditer(r"function\s+getUserPassword|getUserPassword\s*[:=]", js):
    s = max(0, m.start() - 50)
    print("..." + js[s:s + 500].replace("\n", " "))
    print()

print("=" * 66)
print("### md5( 调用的上下文")
count = 0
for m in re.finditer(r"md5\([^)]{0,60}\)", js):
    seg = js[max(0, m.start() - 150):m.end() + 80].replace("\n", " ")
    print("  " + seg[:280])
    print()
    count += 1
    if count >= 6:
        break
