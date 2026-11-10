# -*- coding: utf-8 -*-
"""恢复后全面检查：文件系统 / 声音通道 / 内存"""
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import os, gc
print('=== 文件系统 ===')
print(sorted(os.listdir('/')))
print()
print('=== 内存 ===')
gc.collect()
print('free', gc.mem_free())
print()
print('=== 声音通道 ===')
print('sound:', type(sound), 'read:', sound.read(), sound.read(), sound.read())
print()
print('=== 各 ADC ===')
from machine import ADC, Pin
for gp in (34, 35, 36, 37, 39):
    try:
        c = ADC(Pin(gp))
        print('  GPIO%-3d %s' % (gp, [c.read() for _ in range(3)]))
    except Exception as e:
        print('  GPIO%-3d err %s' % (gp, e))
'''

d = MyBit("COM3")
try:
    d.ser.write(b"\x03\x03")
    time.sleep(0.4)
    d._drain(0.4)
    d.exec("import gc;gc.collect()", deadline=20)

    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\post.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "post.py")
    d.ser.write(b"\x03\x03")
    time.sleep(0.4)
    d._drain(0.4)
    print(d.exec("import gc;gc.collect()\nexec(open('post.py').read())", deadline=60).strip()[:2000])
finally:
    d.close()
