# -*- coding: utf-8 -*-
"""在板子上测试流式 send_wav：录 3 秒，然后按新逻辑发送，确认不 MemoryError"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import audio, sys, os, gc, time
try:
    import ubinascii as b64
except ImportError:
    import binascii as b64

CHUNK = 120

def sleep_ms(ms):
    time.sleep_ms(ms)

def send(line):
    sys.stdout.write(line + "\n")

def send_wav(path):
    size = os.stat(path)[6]
    n = (size + CHUNK - 1) // CHUNK
    send("A|S|%d" % n)
    sleep_ms(40)
    f = open(path, "rb")
    i = 0
    while i < n:
        b = f.read(CHUNK)
        if not b:
            break
        send("A|D|%d|%s" % (i, b64.b2a_base64(b).strip().decode()))
        del b
        i += 1
        if i % 6 == 0:
            sleep_ms(15)
            gc.collect()
    f.close()
    sleep_ms(40)
    send("A|E")
    return n

# 录音
try:
    os.remove('s.wav')
except Exception:
    pass
gc.collect()
audio.recorder_init()
sleep_ms(120)
audio.record('s.wav', 3)
try:
    audio.recorder_deinit()
except Exception:
    pass
size = os.stat('s.wav')[6]
print('录音文件', size, '字节')
print('发送前 free =', gc.mem_free())

t0 = time.ticks_ms()
n = send_wav('s.wav')
t1 = time.ticks_ms()
print('发送完成: %d 块, 耗时 %d ms' % (n, t1 - t0))
print('发送后 free =', gc.mem_free())
os.remove('s.wav')
print('DONE')
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\sendtest.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "sendtest.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.3)
    out = d.exec("exec(open('sendtest.py').read())", deadline=180)
    # 输出里会有大量 A|D| 行，只打印关键信息
    lines = out.split("\n")
    key = [l for l in lines if l.startswith(("录音", "发送", "DONE", "Traceback", "  File", "MemoryError", "OSError"))]
    print("关键输出:")
    for l in key:
        print("  " + l[:150])
    total = len([l for l in lines if l.startswith("A|D|")])
    print("\n实际收到 A|D| 数据块: %d 个" % total)
    if total:
        first = [l for l in lines if l.startswith("A|D|")][0]
        print("首块示例:", first[:60] + "...")
finally:
    d.close()
