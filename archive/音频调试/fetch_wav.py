# -*- coding: utf-8 -*-
"""分块从板子下载 WAV 并分析"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

d = MyBit("COM3")
LOCAL = r"D:\数据文件\上课\信电导论\开发板\_scratch\rec_test.wav"
try:
    # 先录一段新的
    print("[1] 让板子录 3 秒")
    print(d.exec(
        "import audio, os, gc\n"
        "audio.recorder_init()\n"
        "try:\n"
        "    os.remove('rec.wav')\n"
        "except Exception:\n"
        "    pass\n"
        "gc.collect()\n"
        "audio.record('rec.wav', 3)\n"
        "print('录完', os.stat('rec.wav')[6], 'bytes')", deadline=40).strip())

    print("\n[2] 分块下载")
    size = int(d.exec("import os;print(os.stat('rec.wav')[6])", deadline=15).strip())
    print("    总大小:", size)
    buf = bytearray()
    off = 0
    CH = 1024
    while off < size:
        n = min(CH, size - off)
        b64 = d.exec(
            "import ubinascii\n"
            "f=open('rec.wav','rb');f.seek(%d);d=f.read(%d);f.close()\n"
            "print(ubinascii.b2a_base64(d).decode())" % (off, n), deadline=20).strip()
        import base64
        buf += base64.b64decode(b64 + "===")
        off += n
        print("    %d/%d" % (off, size))
    with open(LOCAL, "wb") as f:
        f.write(buf)
    print("    已保存:", len(buf), "字节 ->", LOCAL)

    print("\n[3] 清理")
    print(d.exec("import os;os.remove('rec.wav');print('removed')", deadline=15).strip())
finally:
    d.close()
