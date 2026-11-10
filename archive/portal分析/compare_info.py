# -*- coding: utf-8 -*-
"""逐字节对比：我的 info 加密 vs 浏览器的 info 加密"""
import base64
import hashlib
import sys

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S

# 浏览器抓到的真实值
BROWSER_TOKEN = None   # 需要同一 token 才能对比
BROWSER_INFO = "8NE+T8S/IJnq2mhkx25iRVlWSFKXoAOEtLLLOGYY2zm+NYEOZ0FAVCTF/Sn5cB4xX/nXHK0gG7QnJEqRDtF56VOAqvYl7lvF5GEjTbE6zuq+tU8cr0hhkvcxiPpPcTUlE8N0ilA2re2="
BROWSER_CHKSUM = "REDACTED_40HEX"
BROWSER_HMD5 = "REDACTED_32HEX"

print("浏览器 info 长度:", len(BROWSER_INFO))
raw = base64.b64decode(BROWSER_INFO)
print("解码后长度:", len(raw), "(应为 xxtea 块大小 4 的倍数)")
print("解码后 hex 前 32:", raw[:32].hex())
print()

# 我的实现产出的长度
token = "REDACTED_64HEX"
info_json = '{"username":"YOUR_STUDENT_ID","password":"YOUR_PASSWORD","ip":"CLIENT_IP","acid":"1","enc_ver":"srun_bx1"}'
print("明文 JSON:", info_json)
print("明文长度:", len(info_json))
enc = S.xencode(info_json, token)
print("我的加密长度:", len(enc))
print("我的 base64 长度:", len(S.b64(enc)))
print()

# 关键检查：base64 是否有填充
print("浏览器 base64 结尾:", BROWSER_INFO[-4:])
print("我的 base64 结尾:", S.b64(enc)[-4:])
print()

# 检查 xxtea 输出的字节长度逻辑
# n = len(pwd)-1，lencode(key=False) 输出 (n+1)*4 字节
import math
n_words = (len(info_json) + 3) // 4
print("按 4 字节对齐后的字数:", n_words, "-> 输出字节:", n_words * 4)
print("我的实际输出:", len(enc))
