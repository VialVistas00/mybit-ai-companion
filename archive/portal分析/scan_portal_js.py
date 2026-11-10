# -*- coding: utf-8 -*-
"""下载 Portal 各 JS，定位 login 参数的真实构造代码"""
import re
import sys
import urllib.request

BASE = "http://PORTAL_IP"
FILES = [
    "/static/themes/pro/js/main.js?v=a32e00343444a19a",
    "/static/themes/pro/js/Portal.js?v=a32e00343444a19a",
    "/static/themes/pro/js/Utils.js?v=a32e00343444a19a",
    "/static/themes/pro/js/creater.js?v=a32e00343444a19a",
    "/static/themes/pro/js/lite.js?v=a32e00343444a19a",
]
KEYS = ["chksum", "enc_ver", "SRBX1", "srun_portal?", "action=login", "password", "double_stack",
        "agreeProtocol", "srun_portal_agree"]

for f in FILES:
    try:
        req = urllib.request.Request(BASE + f, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "replace")
    except Exception as e:
        print(f"[ERR] {f}: {e}")
        continue
    print("=" * 70)
    print(f, "长度", len(data))
    hits = 0
    for k in KEYS:
        for m in re.finditer(re.escape(k), data):
            s = max(0, m.start() - 200)
            e = min(len(data), m.end() + 300)
            seg = data[s:e].replace("\n", " ").replace("\r", " ")
            print(f"\n  [{k}] ...{seg}...")
            hits += 1
            if hits > 18:
                break
        if hits > 18:
            break
    if hits == 0:
        print("  (无命中)")
