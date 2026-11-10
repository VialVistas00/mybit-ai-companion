# -*- coding: utf-8 -*-
"""验证内置纯 Python SHA1 与标准 hashlib 一致"""
import sys
import hashlib

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
import srun_client as S

# 强制走纯 Python 分支（模拟 MicroPython 无 sha1 的环境）
class _FakeHash:
    @staticmethod
    def md5(b):
        return hashlib.md5(b)

S._hash = _FakeHash

vectors = [
    "",
    "abc",
    "a" * 1000,
    "The quick brown fox jumps over the lazy dog",
    '{"username":"YOUR_ACCOUNT","password":"YOUR_PASSWORD","ip":"BOARD_IP","acid":"1","enc_ver":"srun_bx1"}',
    "x" * 500,
]

ok = True
for v in vectors:
    mine = S.sha1(v)
    std = hashlib.sha1(v.encode("utf-8")).hexdigest()
    flag = "OK " if mine == std else "MISMATCH"
    if mine != std:
        ok = False
    label = v if len(v) <= 40 else v[:37] + "..."
    print("%-8s len=%-4d %r" % (flag, len(v), label))
    if mine != std:
        print("        mine:", mine)
        print("        std :", std)

print("\n全部通过:", ok)
