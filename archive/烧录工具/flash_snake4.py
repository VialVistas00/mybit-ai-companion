# -*- coding: utf-8 -*-
"""烧录带按键日志的版本"""
import os, sys, time
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

DEV = r"D:\数据文件\上课\信电导论\开发板"
d = MyBit("COM3")
try:
    n = d.put(os.path.join(DEV, "snake.py"), "main.py")
    print("上传 main.py:", n, "bytes")
    print("板载:", d.ls())

    d.ser.write(b"\x03\x03")
    time.sleep(0.25)
    d._drain(0.3)
    d.ser.write(b"\x04")

    print("\n重启后 4 秒内的输出：")
    t_end = time.time() + 4
    buf = b""
    while time.time() < t_end:
        chunk = d.ser.read(d.ser.in_waiting or 1)
        if chunk:
            buf += chunk
    print(repr(buf.decode("utf-8", "replace"))[:800])
finally:
    d.close()
    print("\n串口已释放，板子独立运行中")
