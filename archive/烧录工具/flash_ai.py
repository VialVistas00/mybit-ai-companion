# -*- coding: utf-8 -*-
"""烧录串口版 AI 学伴到板子 main.py 并启动"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

DEV = r"D:\数据文件\上课\信电导论\开发板"

d = MyBit("COM3")
try:
    print("[1] 上传 ai_companion_serial.py -> main.py")
    n = d.put(os.path.join(DEV, "ai_companion_serial.py"), "main.py")
    print("    ", n, "bytes")
    print("     校验:", d.exec(
        "import os;print('main.py', os.stat('main.py')[6], 'bytes')", deadline=15).strip())

    print("\n[2] 软重启，观察启动")
    d.ser.write(b"\x03\x03")
    time.sleep(0.25)
    d._drain(0.3)
    d.ser.write(b"\x04")
    time.sleep(3.5)
    out = d._drain(1.5)
    print("     回显:", repr(out)[:400])
finally:
    d.close()
    print("\n[*] 串口已释放")
