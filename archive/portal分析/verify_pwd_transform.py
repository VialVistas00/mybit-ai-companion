# -*- coding: utf-8 -*-
"""验证：password = base64(encodeURIComponent(原始密码))"""
import base64
import hashlib
import sys
import urllib.parse

PWD = "YOUR_PASSWORD"
TOKEN = "REDACTED_64HEX"
REAL_HMD5 = "REDACTED_32HEX"

print("原始密码:", repr(PWD))
print("真实 hmd5:", REAL_HMD5)
print()

# 方案1: base64(encodeURIComponent(pwd))
enc = urllib.parse.quote(PWD)
print("encodeURIComponent:", enc)

# JS 的 $.base64.encode 用的是标准 base64
b64 = base64.b64encode(enc.encode()).decode()
print("base64 后:", b64)

h1 = hashlib.md5((b64 + TOKEN).encode()).hexdigest()
print("md5(b64 + token):", h1)
print("  匹配:", h1 == REAL_HMD5)
print()

# 方案2: 只 encodeURIComponent 不 base64
h2 = hashlib.md5((enc + TOKEN).encode()).hexdigest()
print("md5(enc + token):", h2, " 匹配:", h2 == REAL_HMD5)
print()

# 方案3: 只用 base64
b64b = base64.b64encode(PWD.encode()).decode()
h3 = hashlib.md5((b64b + TOKEN).encode()).hexdigest()
print("md5(base64raw + token):", h3, " 匹配:", h3 == REAL_HMD5)
print()

# 方案4: 原始密码
h4 = hashlib.md5((PWD + TOKEN).encode()).hexdigest()
print("md5(原始 + token):", h4, " 匹配:", h4 == REAL_HMD5)
print()

print("=" * 50)
print("总结：")
for label, val in (("base64(enc)", h1), ("enc", h2), ("base64(raw)", h3), ("raw", h4)):
    print("  %-14s %s" % (label, "*** 匹配 ***" if val == REAL_HMD5 else "不匹配"))
