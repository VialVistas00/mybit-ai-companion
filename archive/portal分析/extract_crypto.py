# -*- coding: utf-8 -*-
"""从 Utils.js 提取 sha1 / md5 的真实实现"""
import re
import urllib.request

BASE = "http://PORTAL_IP"
VER = "90cd879880515c55"

for name in ("Utils.js", "main.js", "lite.js"):
    url = BASE + "/static/themes/pro/js/" + name + "?v=" + VER
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        js = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
    except Exception as e:
        print(name, "下载失败", e)
        continue
    print("=" * 66)
    print(name, "长度", len(js))

    for kw in ("sha1", "md5"):
        idxs = [m.start() for m in re.finditer(kw, js)]
        if not idxs:
            print("  无", kw)
            continue
        print("  %s 出现 %d 次，位置示例 %s" % (kw, len(idxs), idxs[:6]))

    # 找函数定义
    for pat in (r"function\s+sha1\s*\([^)]*\)\s*\{", r"sha1\s*[:=]\s*function",
                r"function\s+md5\s*\([^)]*\)\s*\{", r"md5\s*[:=]\s*function"):
        for m in re.finditer(pat, js):
            s = m.start()
            print("\n  [定义] ..." + js[s:s + 400].replace("\n", " ")[:400])

    # 找调用
    for m in re.finditer(r"md5\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)", js):
        print("\n  [调用] " + js[max(0, m.start() - 120):m.end() + 80].replace("\n", " "))
