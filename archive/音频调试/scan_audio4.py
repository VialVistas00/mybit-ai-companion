# -*- coding: utf-8 -*-
"""确定 record(file_name, ...) 的完整签名"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import audio, os, time
audio.recorder_init()

def try_call(desc, fn):
    try:
        r = fn()
        print('   %-34s -> OK %s' % (desc, repr(r)[:70]))
        return True
    except TypeError as e:
        print('   %-34s -> TypeError %s' % (desc, str(e)[:100]))
    except Exception as e:
        print('   %-34s -> %s: %s' % (desc, type(e).__name__, str(e)[:80]))
    return False

print('--- record 参数探测 ---')
try_call("record('a.wav')", lambda: audio.record('a.wav'))
try_call("record('b.wav', 1)", lambda: audio.record('b.wav', 1))
try_call("record('c.wav', 3)", lambda: audio.record('c.wav', 3))
try_call("record('d.wav', 3000)", lambda: audio.record('d.wav', 3000))
try_call("record('e.wav', 3, 16000)", lambda: audio.record('e.wav', 3, 16000))

print()
print('--- 生成的文件 ---')
for f in ('a.wav','b.wav','c.wav','d.wav','e.wav'):
    try:
        print('  %-8s %d bytes' % (f, os.stat(f)[6]))
    except Exception:
        print('  %-8s 无' % f)
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\audiorec.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "audiorec.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.3)
    print(d.exec("exec(open('audiorec.py').read())", deadline=120).strip()[:3000])
finally:
    d.close()
