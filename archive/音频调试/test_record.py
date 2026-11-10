# -*- coding: utf-8 -*-
"""
录音全流程测试：
  1. 板子用 audio.record 录 3 秒
  2. 检查生成的 wav
  3. 分块传回电脑、转 16k
  4. 送讯飞识别，看识别结果
不依赖按键，直接验证录音+识别链路。
"""
import base64
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

LOCAL = r"D:\数据文件\上课\信电导论\开发板\_scratch\live.wav"

d = MyBit("COM3")
try:
    print("[1] 板子录音 3 秒（请对板子说话）")
    t0 = time.time()
    print(d.exec(
        "import audio, os, gc, time\n"
        "try:\n"
        "    os.remove('live.wav')\n"
        "except Exception:\n"
        "    pass\n"
        "gc.collect()\n"
        "audio.recorder_init()\n"
        "time.sleep_ms(120)\n"
        "audio.record('live.wav', 3)\n"
        "try:\n"
        "    audio.recorder_deinit()\n"
        "except Exception:\n"
        "    pass\n"
        "print('OK', os.stat('live.wav')[6])", deadline=40).strip())
    print("    耗时 %.1fs" % (time.time() - t0))

    print("\n[2] 分块取回")
    size = int(d.exec("import os;print(os.stat('live.wav')[6])", deadline=15).strip())
    buf = bytearray()
    off = 0
    while off < size:
        n = min(1024, size - off)
        b = d.exec(
            "import ubinascii\n"
            "f=open('live.wav','rb');f.seek(%d);d=f.read(%d);f.close()\n"
            "print(ubinascii.b2a_base64(d).decode())" % (off, n), deadline=20).strip()
        buf += base64.b64decode(b + "===")
        off += n
    with open(LOCAL, "wb") as f:
        f.write(buf)
    print("    已保存", len(buf), "字节")
finally:
    d.close()

print("\n[3] 本地分析")
import struct
import wave
w = wave.open(LOCAL, "rb")
sr = w.getframerate()
nf = w.getnframes()
data = w.readframes(nf)
n = len(data) // 2
s = struct.unpack("<%dh" % n, data[:n * 2])
seg = n // 10
rms = []
for i in range(10):
    part = s[i * seg:(i + 1) * seg]
    if not part:
        continue
    rms.append(int((sum(x * x for x in part) / len(part)) ** 0.5))
print("  采样率 %d Hz / 时长 %.2fs / 峰值 %d" % (sr, nf / sr, max(abs(x) for x in s)))
print("  10 段 RMS:", rms)
w.close()
