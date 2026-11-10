# -*- coding: utf-8 -*-
"""
决定性验证：在同一个 token 下，对比浏览器 info 与我的 info
如果我把浏览器 token 对应的 info 解出来，就能看到它到底放了什么
"""
import base64
import sys

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S


def xxtea_decode(data, key):
    """xxtea 解密（SRun lencode(key=False) 的逆）"""
    pwd = S._sencode(data.decode("latin-1"), False)
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
        q -= 1
    return S._lencode(pwd, True)


# 浏览器的 info（来自抓包）
BROWSER_INFO_B64 = ("8NE+T8S/IJnq2mhkx25iRVlWSFKXoAOEtLLLOGYY2zm+NYEOZ0FAVCTF/Sn5cB4xX/nXHK0gG7QnJEqR"
                    "DtF56VOAqvYl7lvF5GEjTbE6zuq+tU8cr0hhkvcxiPpPcTUlE8N0ilA2re2=")

# 对应的 token 需要抓包时的那个，我们没有。
# 但可以从 login_url.txt 里取，这里的 token 没有直接保存。
# 换一个思路：反向验证 —— 用我们的 xencode + 任意 token 加密，
# 再用同一个函数解密，确认算法闭环；然后检查明文字段顺序。
print("=== 1. 算法闭环验证 ===")
tok = "abc123token"
plain = '{"username":"YOUR_STUDENT_ID","password":"YOUR_PASSWORD","ip":"CLIENT_IP","acid":"1","enc_ver":"srun_bx1"}'
enc = S.xencode(plain, tok)
dec = xxtea_decode(enc, tok)
print("  加密后:", len(enc), "字节")
print("  解密后:", dec.decode("utf-8", "replace") if dec else None)
print("  与原文一致:", dec == plain.encode())

print()
print("=== 2. 检查浏览器 info 的结构特征 ===")
raw = base64.b64decode(BROWSER_INFO_B64)
print("  长度:", len(raw))
print("  明文长度推测:", "浏览器明文可能是", len(raw) - 4, "字节左右")
print("  我的明文是 98 字节")
print("  差值:", len(raw) - 4 - 98)
