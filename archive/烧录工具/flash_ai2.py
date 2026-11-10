# -*- coding: utf-8 -*-
"""烧录新版 ai_companion_serial.py（audio 模块录音）到板子"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

DEV = r"D:\数据文件\上课\信电导论\开发板"
SRC = os.path.join(DEV, "ai_companion_serial.py")

size_local = os.path.getsize(SRC)
print("本地文件 %d 字节" % size_local)

d = MyBit("COM3")
try:
    # 先确认没有残留的 raw REPL
    d.ser.write(b"\x02\x02")
    time.sleep(0.3)
    d._drain(0.3)

    print("[1] 上传 -> main.py")
    n = d.put(SRC, "main.py")
    print("    写入 %d 字节" % n)

    print("[2] 校验板载大小")
    onb = d.exec("import os;print(os.stat('main.py')[6])", deadline=15).strip()
    print("    板载 %s 字节，本地 %d 字节，一致: %s" % (onb, size_local, onb == str(size_local)))

    print("[3] 校验关键代码已进入板子")
    chk = d.exec(
        "f=open('main.py');s=f.read();f.close()\n"
        "print('含 audio.record:', 'audio.record' in s)\n"
        "print('含 recorder_init:', 'recorder_init' in s)\n"
        "print('含 无麦克风模块:', '无麦克风模块' in s)\n"
        "print('含 无录音模块:', '无录音模块' in s)", deadline=20).strip()
    print("    " + chk.replace("\n", "\n    "))
finally:
    d.close()
