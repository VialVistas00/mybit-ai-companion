# -*- coding: utf-8 -*-
"""重新验证麦克风：连续多次采样 + 录音期间同步看 sound 值
之前我只看 3 次瞬时采样就下结论，可能是采样时机/状态问题"""
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import gc, time
from npython import sound, audio

print('=== A. 连续 40 次采样 sound.read() ===')
vals = []
for i in range(40):
    vals.append(sound.read())
    time.sleep_ms(50)
print('  值:', vals)
print('  最大:%d 最小:%d 非零个数:%d' % (max(vals), min(vals), len([v for v in vals if v > 0])))

print()
print('=== B. recorder_init 之后再连续采样 ===')
gc.collect()
audio.recorder_init()
time.sleep_ms(300)
vals2 = []
for i in range(40):
    vals2.append(sound.read())
    time.sleep_ms(50)
print('  值:', vals2)
print('  最大:%d 最小:%d 非零个数:%d' % (max(vals2), min(vals2), len([v for v in vals2 if v > 0])))
'''

d = MyBit("COM3")
try:
    d.ser.write(b"\x03\x03")
    time.sleep(0.5)
    d._drain(0.4)
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\mic2.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "mic2.py")
    d.ser.write(b"\x03\x03")
    time.sleep(0.4)
    d._drain(0.4)
    print(d.exec("import gc;gc.collect()\nexec(open('mic2.py').read())", deadline=60).strip()[:2000])
finally:
    d.close()
