# -*- coding: utf-8 -*-
"""在同一 token 下：先取 token，让浏览器用这个 token 加密，再解开看明文"""
import base64
import json
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S

# 使用抓包保存的完整 URL
URL_FILE = r"D:\数据文件\上课\信电导论\开发板\_scratch\login_url.txt"
with open(URL_FILE, encoding="utf-8") as f:
    url = f.read().strip()

from urllib.parse import urlparse, parse_qsl
q = urlparse(url).query
params = dict(parse_qsl(q, keep_blank_values=True))
info_b64 = params["info"].replace("{SRBX1}", "")
chksum = params["chksum"]
hmd5 = params["password"].replace("{MD5}", "")
ip = params["ip"]

print("=== 抓包里的值 ===")
print("  ip     :", ip)
print("  hmd5   :", hmd5)
print("  chksum :", chksum)
print("  info   :", info_b64[:50], "...")

# 关键：从同一批请求里找 token
# token 在 get_challenge 响应里，需要重新抓
# 这里用 hmd5 反推：hmd5 = md5(password + token)
# 我们已知 password = YOUR_PASSWORD，遍历不可能。
# 改为：重新抓一次，把 token 和 info 一起存下来

import hashlib
print()
print("=== 用 hmd5 反查 token 长度 ===")
print("  hmd5 是 md5(pwd + token)，token 通常是 64 位十六进制")


def xxtea_decode(data, key):
    pwd = S._sencode(data.decode("latin-1"), False)
    pwdk = S._sencode(key, False)
    while len(pwdk) < 4:
        pwdk.append(0)
    n = len(pwd) - 1
    z = pwd[n]
    y = pwd[0]
    c = 0x86014019 | 0x183639A0
    d = (6 + 52 // (n + 1)) * c
    qq = int(6 + 52 / (n + 1))
    while qq > 0:
        e = (d >> 2) & 3
        p = n
        while p > 0:
            z = pwd[p - 1]
            m = (z >> 5) ^ (y << 2)
            m = m + (((y >> 3) ^ (z << 4)) ^ (d ^ y))
            m = m + (pwdk[(p & 3) ^ e] ^ z)
            pwd[p] = (pwd[p] - m) & 0xFFFFFFFF
            y = pwd[p]
            p -= 1
        z = pwd[n]
        m = (z >> 5) ^ (y << 2)
        m = m + (((y >> 3) ^ (z << 4)) ^ (d ^ y))
        m = m + (pwdk[(p & 3) ^ e] ^ z)
        pwd[0] = (pwd[0] - m) & 0xFFFFFFFF
        y = pwd[0]
        d = (d - c) & 0xFFFFFFFF
        qq -= 1
    return S._lencode(pwd, True)


raw = base64.b64decode(info_b64)
print()
print("=== 用真实 token 解密失败说明需要 token，改用另一策略 ===")
print("  密文长度:", len(raw))
print("  hex:", raw[:48].hex())
print()
print("  由于 token 未保存，改用：直接对比 base64 后的字符集分布")

# 计算信息熵差异
def entropy(b):
    from collections import Counter
    c = Counter(b)
    n = len(b)
    import math
    return -sum((v / n) * math.log2(v / n) for v in c.values())


mine_enc = S.xencode(
    '{"username":"YOUR_STUDENT_ID","password":"YOUR_PASSWORD","ip":"CLIENT_IP","acid":"1","enc_ver":"srun_bx1"}',
    "testtoken")
print()
print("  浏览器密文熵:", round(entropy(raw), 3))
print("  我的密文熵  :", round(entropy(mine_enc), 3))
print("  (熵接近说明都是正常加密数据)")
