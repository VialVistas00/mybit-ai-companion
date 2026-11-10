# -*- coding: utf-8 -*-
"""实测声音通道：sound.read() 与 audio.record 在不同条件下的表现"""
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

d = MyBit("COM3")
try:
    print("=" * 56)
    print(" 声音通道实测")
    print("=" * 56)

    # 1. 先看 sound.read 反复采样
    print("\n[1] sound.read() 连续采样 12 次")
    out = d.exec(
        "import time\n"
        "for i in range(12):\n"
        "    print(sound.read())\n"
        "    time.sleep(0.25)", deadline=40)
    vals = [l.strip() for l in out.split("\n") if l.strip() and l.strip().isdigit()]
    print("    数值:", vals)

    # 2. 测试 recorder_init 前后的 sound.read
    print("\n[2] audio.recorder_init() 之后再读 sound.read()")
    out = d.exec(
        "import audio, gc, time\n"
        "gc.collect()\n"
        "print('before', sound.read())\n"
        "audio.recorder_init()\n"
        "time.sleep_ms(300)\n"
        "print('after_init', sound.read())\n"
        "print('after2', sound.read())\n"
        "try:\n"
        "    audio.recorder_deinit()\n"
        "except Exception:\n"
        "    pass\n", deadline=40)
    print("   ", " | ".join(l.strip() for l in out.split("\n") if l.strip()))

    # 3. 录音时的原始数据统计（录音同时读 sound）
    print("\n[3] 录音 2 秒并统计样本幅度")
    out = d.exec(
        "import audio, gc, os\n"
        "try:\n"
        "    os.remove('t1.wav')\n"
        "except Exception:\n"
        "    pass\n"
        "gc.collect(); gc.collect()\n"
        "audio.recorder_init()\n"
        "audio.record('t1.wav', 2)\n"
        "try:\n"
        "    audio.recorder_deinit()\n"
        "except Exception:\n"
        "    pass\n"
        "f = open('t1.wav','rb')\n"
        "f.seek(44)\n"
        "mx = -32768\n"
        "mn = 32767\n"
        "nb = 0\n"
        "while True:\n"
        "    b = f.read(300)\n"
        "    if not b:\n"
        "        break\n"
        "    n = len(b) // 2\n"
        "    for i in range(n):\n"
        "        v = b[i*2] | (b[i*2+1] << 8)\n"
        "        if v > 32767:\n"
        "            v -= 65536\n"
        "        if v > mx:\n"
        "            mx = v\n"
        "        if v < mn:\n"
        "            mn = v\n"
        "        nb += 1\n"
        "f.close()\n"
        "print('RES max=%d min=%d span=%d n=%d' % (mx, mn, mx-mn, nb))\n"
        "os.remove('t1.wav')", deadline=60)
    for l in out.split("\n"):
        if "RES" in l or "Error" in l or "error" in l:
            print("   ", l.strip())

    # 4. 检查是否有其他麦克风相关 API
    print("\n[4] 固件里所有可能与麦克风相关的接口")
    out = d.exec(
        "import npython\n"
        "names = [x for x in dir(npython) if not x.startswith('_')]\n"
        "hits = []\n"
        "for n in names:\n"
        "    ln = n.lower()\n"
        "    if any(k in ln for k in ('sound','mic','audio','adc','p0','p1','pin0','pin1')):\n"
        "        hits.append(n)\n"
        "print('候选:', hits)\n"
        "print('pin0 type:', type(pin0))\n"
        "print('pin0 analog:', pin0.read_analog())\n"
        "print('pin1 analog:', pin1.read_analog())\n"
        "print('sound obj:', type(sound), 'val:', sound.read())", deadline=40)
    print("   ", "\n    ".join(l.strip() for l in out.split("\n") if l.strip())[:900])
finally:
    d.close()
