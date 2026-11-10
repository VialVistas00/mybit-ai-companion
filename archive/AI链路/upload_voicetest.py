# -*- coding: utf-8 -*-
"""上传 voicetest.py：板子录音 -> 分块发送 -> 等桥处理"""
import os
import sys

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

VOICETEST = r'''import audio, sys, os, gc, time
try:
    import ubinascii as b64
except ImportError:
    import binascii as b64

CHUNK = 180
WAV = 'vt.wav'

try:
    os.remove(WAV)
except Exception:
    pass
gc.collect()

print('REC_START')
audio.recorder_init()
time.sleep_ms(120)
audio.record(WAV, 3)
try:
    audio.recorder_deinit()
except Exception:
    pass
size = os.stat(WAV)[6]
print('REC_OK', size)

n = (size + CHUNK - 1) // CHUNK
sys.stdout.write('A|S|%d\n' % n)
f = open(WAV, 'rb')
i = 0
while i < n:
    b = f.read(CHUNK)
    if not b:
        break
    sys.stdout.write('A|D|%d|%s\n' % (i, b64.b2a_base64(b).strip().decode()))
    del b
    i += 1
    if i % 20 == 0:
        gc.collect()
f.close()
sys.stdout.write('A|E\n')
print('SENT', n)

t0 = time.ticks_ms()
got = None
while time.ticks_ms() - t0 < 120000:
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
print('VOICE_DONE', got)
try:
    os.remove(WAV)
except Exception:
    pass
'''

tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\vt.py"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(VOICETEST)

d = MyBit("COM3")
try:
    n = d.put(tmp, "voicetest.py")
    print("voicetest.py 上传:", n, "字节")
finally:
    d.close()
    print("串口已释放")
