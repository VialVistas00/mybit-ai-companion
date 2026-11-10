# -*- coding: utf-8 -*-
"""找 md5(pwd, token) 的定义：是 md5(pwd+token) 还是 md5(token+pwd)？"""
import hashlib
import re
import urllib.request

VER = "90cd879880515c55"
TOKEN = "REDACTED_64HEX"
REAL_HMD5 = "REDACTED_32HEX"
PWD = "YOUR_PASSWORD"

# 先暴力验证各种组合
import base64
import urllib.parse

print("=== 暴力测试 md5 参数组合 ===")
variants = {
    "raw": PWD,
    "b64(enc)": base64.b64encode(urllib.parse.quote(PWD).encode()).decode(),
    "enc": urllib.parse.quote(PWD),
    "b64": base64.b64encode(PWD.encode()).decode(),
}
found = False
for vname, v in variants.items():
    for order, s in (("pwd+token", v + TOKEN), ("token+pwd", TOKEN + v),
                     ("pwd", v), ("token", TOKEN)):
        h = hashlib.md5(s.encode()).hexdigest()
        if h == REAL_HMD5:
            print("  *** 匹配: %s 用 %s ***" % (vname, order))
            found = True
if not found:
    print("  未匹配")

print()
print("=== 查找 md5 函数定义 ===")
baselist = []
for name in ("Portal.js", "main.js", "all.min.js", "Utils.js"):
    url = "http://PORTAL_IP/static/themes/pro/js/" + name + "?v=" + VER
    if name == "all.min.js":
        url = "http://PORTAL_IP/static/themes/pro/lib/all.min.js?v=20180302?v=" + VER
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        js = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
        print("  %s: %d 字节" % (name, len(js)))
        baselist.append((name, js))
    except Exception as e:
        print("  %s 失败 %s" % (name, str(e)[:40]))

print()
for name, js in baselist:
    # 找类似 function md5(s, key) 的定义
    for m in re.finditer(r"function\s+md5\s*\(([^)]*)\)", js):
        print("  [%s] function md5(%s)" % (name, m.group(1)))
        s = m.start()
        print("     " + js[s:s + 300].replace("\n", " ")[:300])
    for m in re.finditer(r"md5\s*=\s*function\s*\(([^)]*)\)", js):
        print("  [%s] md5 = function(%s)" % (name, m.group(1)))
        s = m.start()
        print("     " + js[s:s + 300].replace("\n", " ")[:300])
