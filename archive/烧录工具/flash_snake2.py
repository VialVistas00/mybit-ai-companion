# -*- coding: utf-8 -*-
"""烧录新版本 + 监听板子实时按键值（用于诊断"按了没反应"）"""
import os, sys, time
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

DEV = r"D:\数据文件\上课\信电导论\开发板"

d = MyBit("COM3")
try:
    print("[1] 上传新版 snak e-> main.py")
    n = d.put(os.path.join(DEV, "snake.py"), "main.py")
    print("    ", n, "bytes")

    print("[2] 软重启（注意：本次不拉 DTR/RTS，避免复位抖动）")
    d.ser.write(b"\x03\x03")
    time.sleep(0.25)
    d._drain(0.3)
    d.ser.write(b"\x04")

    print("[3] 监听 15 秒 —— 请现在按一下 B 键，再按一下 A 键")
    print("    " + "-" * 50)
    t_end = time.time() + 15
    buf = b""
    while time.time() < t_end:
        chunk = d.ser.read(d.ser.in_waiting or 1)
        if chunk:
            buf += chunk
            txt = chunk.decode("utf-8", "replace")
            sys.stdout.write(txt)
            sys.stdout.flush()
    print("\n    " + "-" * 50)
    print("[4] 收到的全部内容：")
    print(repr(buf.decode("utf-8", "replace"))[:1500])
finally:
    d.close()
