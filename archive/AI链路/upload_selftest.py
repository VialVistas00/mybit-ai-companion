# -*- coding: utf-8 -*-
"""上传 selftest.py 到板子"""
import os
import sys

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

SELFTEST = r'''import sys, time
try:
    import ubinascii as b64
except ImportError:
    import binascii as b64

sys.stdout.write('Q|' + b64.b2a_base64('用一句话介绍你自己'.encode('utf-8')).strip().decode() + '\n')
t0 = time.ticks_ms()
got = None
while time.ticks_ms() - t0 < 70000:
    line = sys.stdin.readline()
    if not line:
        continue
    line = line.strip()
    if line.startswith('R|') or line.startswith('E|'):
        try:
            got = b64.a2b_base64(line[2:].encode()).decode('utf-8')
        except Exception:
            got = line[2:]
        break
print('FINAL|' + str(got))
'''

tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\st.py"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(SELFTEST)

d = MyBit("COM3")
try:
    n = d.put(tmp, "selftest.py")
    print("selftest.py 上传:", n, "bytes")
    print("板载:", d.ls())
finally:
    d.close()
