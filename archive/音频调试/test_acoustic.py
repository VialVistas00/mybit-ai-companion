# -*- coding: utf-8 -*-
"""
真实声学测试：
  1. 板子录音（同时电脑扬声器放语音）
  2. 回传 PCM 到电脑
  3. 去直流 + 归一化
  4. whisper 识别
用于验证麦克风能不能录到声音、识别效果如何。
"""
import base64
import os
import struct
import sys
import threading
import time
import wave

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

PLAY_WAV = r"D:\数据文件\上课\信电导论\开发板\_scratch\play.wav"
OUT_WAV = r"D:\数据文件\上课\信电导论\开发板\_scratch\acoustic.wav"

# 先启动播放（异步）
player = None
if os.path.exists(PLAY_WAV):
    import subprocess
    player = subprocess.Popen(
        ["powershell", "-NoProfile", "-c",
         "(New-Object Media.SoundPlayer '%s').PlaySync()" % PLAY_WAV])

d = MyBit("COM3")
try:
    # 关键：先强制回收，否则残留对象导致录音 MemoryError
    print("[0] 清理板子内存")
    print("    ", d.exec("import gc;gc.collect();print('free', gc.mem_free())", deadline=20).strip())
    print("    ", d.exec("import gc;gc.collect();gc.collect();print('free2', gc.mem_free())", deadline=20).strip())

    print("[1] 板子录音 3 秒（同时播放语音）")
    out = d.exec(
        "import audio, gc, os\n"
        "try:\n"
        "    os.remove('ac.wav')\n"
        "except Exception:\n"
        "    pass\n"
        "gc.collect(); gc.collect(); gc.collect()\n"
        "print('BEFORE', gc.mem_free())\n"
        "audio.recorder_init()\n"
        "gc.collect()\n"
        "audio.record('ac.wav', 3)\n"
        "try:\n"
        "    audio.recorder_deinit()\n"
        "except Exception:\n"
        "    pass\n"
        "print('SIZE', os.stat('ac.wav')[6])", deadline=60)

    size = 0
    for line in out.split("\n"):
        if line.startswith("SIZE"):
            size = int(line.split()[1])
    print("    录音 %d 字节" % size)

    print("[2] 分块回传")
    data = b""
    f = d.exec("print('OPEN')", deadline=10)
    # 用 raw REPL 里循环读取，每次请求 512 字节
    off = 0
    while off < size:
        n = min(512, size - off)
        b64 = d.exec(
            "import ubinascii\n"
            "f=open('ac.wav','rb');f.seek(%d);d=f.read(%d);f.close()\n"
            "print(ubinascii.b2a_base64(d).decode())" % (off, n), deadline=25).strip()
        data += base64.b64decode(b64 + "===")
        off += n
    print("    回传 %d 字节" % len(data))
    with open(OUT_WAV, "wb") as fh:
        fh.write(data)
finally:
    d.close()
    if player:
        try:
            player.wait(timeout=20)
        except Exception:
            player.kill()

# 分析
w = wave.open(OUT_WAV, "rb")
pcm = w.readframes(w.getnframes())
sr = w.getframerate()
w.close()
n = len(pcm) // 2
s = struct.unpack("<%dh" % n, pcm[:n * 2])
mean = sum(s) / n
c = [int(v - mean) for v in s]
c[:200] = [0] * 200
seg = n // 10
print("\n[3] 波形分析（去掉开头 200 样本）")
print("    直流偏置 %.0f" % mean)
print("    分段峰值:", [max(max(c[k*seg:(k+1)*seg]), -min(c[k*seg:(k+1)*seg])) for k in range(10) if c[k*seg:(k+1)*seg]])

print("\n[4] whisper 识别")
import local_asr
text, err = local_asr.transcribe_pcm(pcm, sr)
print("    结果:", repr(text))
print("    错误:", err)
