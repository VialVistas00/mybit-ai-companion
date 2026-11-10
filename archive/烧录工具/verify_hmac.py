# -*- coding: utf-8 -*-
"""验证修正后的 hmac_md5_hex"""
import hashlib
import hmac
import sys

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S

print("=== 用浏览器实测样本验证 ===")
samples = [
    ("aaa", "bbb", "REDACTED_32HEX"),
    ("password123", "abc", "REDACTED_32HEX"),
    ("P", "T", "REDACTED_32HEX"),
]
ok = True
for pwd, token, expected in samples:
    got = S.hmac_md5_hex(token, pwd)
    match = got == expected
    if not match:
        ok = False
    print("  md5(%r,%r): %s  %s" % (pwd, token, got[:32], "OK" if match else "FAIL"))

print()
print("=== 标准 hmac 库对照 ===")
for pwd, token, expected in samples:
    std = hmac.new(token.encode(), pwd.encode(), hashlib.md5).hexdigest()
    print("  %s = %s" % (std[:32], "OK" if std == expected else "FAIL"))

print()
print("全部通过:" , ok)

print()
print("=== 用真实 token 验证 ===")
real_token = "REDACTED_64HEX"
real_hmd5 = "REDACTED_32HEX"
mine = S.hmac_md5_hex(real_token, "YOUR_PASSWORD")
print("  真实 hmd5:", real_hmd5)
print("  我的 hmac:", mine)
print("  匹配:", mine == real_hmd5)
