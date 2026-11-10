# -*- coding: utf-8 -*-
"""排查固件里有哪些音频采集能力"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import sys
print('=== 1. 找 microphone / mic / audio / sound 相关模块 ===')
cands = ['microphone', 'mic', 'audio', 'sound', 'record', 'es8388', 'i2s',
         'unipython', 'npython', 'wave', 'adc']
for m in cands:
    try:
        mod = __import__(m)
        print('  有:', m, '->', [x for x in dir(mod) if not x.startswith('_')][:10])
    except ImportError:
        print('  无:', m)
    except Exception as e:
        print('  错:', m, type(e).__name__)

print()
print('=== 2. npython 里与音频有关的对象 ===')
from npython import *
import npython
names = [x for x in dir(npython) if not x.startswith('_')]
audio = [x for x in names if any(k in x.lower() for k in ('mic','sound','audio','record','voice','speak','beep','music'))]
print('  候选:', audio)

print()
print('=== 3. 逐个看类型与可用方法 ===')
for n in audio:
    try:
        obj = getattr(npython, n)
        meth = [x for x in dir(obj) if not x.startswith('_')]
        print('  %-12s %-24s %s' % (n, str(type(obj))[:22], meth[:12]))
    except Exception as e:
        print('  %-12s 取不到 %s' % (n, e))
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\audioscan.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "audioscan.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.3)
    print(d.exec("exec(open('audioscan.py').read())", deadline=60).strip()[:3500])
finally:
    d.close()
