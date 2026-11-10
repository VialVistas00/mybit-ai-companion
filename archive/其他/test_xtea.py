# -*- coding: utf-8 -*-
"""本地验证 srun_client 的 xxtea/base64 自洽性（CPython 环境）"""
import sys
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S

# 用 srun_portal 的 xdecode 反解，验证 xencode 可逆
def _sdecode(msg, key):
    return S._sencode(msg, False) if False else None

def xdecode(msg_bytes, key):
    """把 xxtea 加密后的 bytes 解回明文（用于自洽验证）"""
    pwd = S._sencode(msg_bytes.decode('latin-1'), False)
    pwdk = S._sencode(key, False)
    while len(pwdk) < 4:
        pwdk.append(0)
    n = len(pwd) - 1
    z = pwd[n]
    y = pwd[0]
    c = 0x86014019 | 0x183639A0
    d = (6 + 52 // (n + 1)) * c
    q = int(6 + 52 / (n + 1))
    while q > 0:
        e = (d >> 2) & 3
        p = n
        while p > 0:
            z = pwd[p - 1]
            m = (z >> 5) ^ (y << 2)
            m = m + (((y >> 3) ^ (z << 4)) ^ (d ^ y))
            m = m + (pwdk[(p & 3) ^ e] ^ z)
            pwd[p] = (pwd[p] - m) & 0xffffffff
            y = pwd[p]
            p -= 1
        z = pwd[n]
        m = (z >> 5) ^ (y << 2)
        m = m + (((y >> 3) ^ (z << 4)) ^ (d ^ y))
        m = m + (pwdk[(p & 3) ^ e] ^ z)
        pwd[0] = (pwd[0] - m) & 0xffffffff
        y = pwd[0]
        d = (d - c) & 0xffffffff
        q -= 1
    return S._lencode(pwd, True)

token = "REDACTED_64HEX"
plain = '{"username":"YOUR_ACCOUNT","password":"YOUR_PASSWORD","ip":"BOARD_IP","acid":"1","enc_ver":"srun_bx1"}'

enc = S.xencode(plain, token)
print("xencode 输出长度:", len(enc))
print("前 32 字节 hex:", enc[:32].hex())
b = S.b64(enc)
print("base64 前 60 字符:", b[:60])
print("base64 长度:", len(b))

dec = xdecode(enc, token)
print("\n往返解码结果:", dec)
print("与原文一致:", dec == plain.encode('utf-8'))

print("\n--- md5 自测 ---")
print("MD5('') =", S.md5(""))
print("MD5('abc') =", S.md5("abc"), "(应为 REDACTED_32HEX)")
print("MD5('YOUR_PASSWORD' + token) =", S.md5("YOUR_PASSWORD" + token))
