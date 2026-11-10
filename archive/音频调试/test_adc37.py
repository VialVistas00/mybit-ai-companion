# -*- coding: utf-8 -*-
"""测试 GPIO37 及周围 ADC 引脚"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''from machine import ADC, Pin

print('=== GPIO37 (sound 用的脚) 各衰减档 ===')
a = ADC(Pin(37))
for att in (ADC.ATTN_0DB, ADC.ATTN_2_5DB, ADC.ATTN_6DB, ADC.ATTN_11DB):
    try:
        a.atten(att)
        print('  atten', att, '->', a.read(), a.read_u16())
    except Exception as e:
        print('  atten', att, 'err', e)

print()
print('=== 各 GPIO 直接读 ===')
for gp in (34, 35, 36, 37, 38, 39):
    try:
        c = ADC(Pin(gp))
        vals = [c.read() for _ in range(5)]
        print('  GPIO%-3d %s' % (gp, vals))
    except Exception as e:
        print('  GPIO%-3d err %s' % (gp, e))
'''

d = MyBit("COM3")
try:
    d.exec("import gc;gc.collect()", deadline=15)
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\adct.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "adct.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.3)
    print(d.exec("import gc;gc.collect()\nexec(open('adct.py').read())", deadline=60).strip()[:2000])
finally:
    d.close()
