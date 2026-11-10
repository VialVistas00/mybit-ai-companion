# -*- coding: utf-8 -*-
"""修复 boot.py 陷阱 -> 重烧贪吃蛇 -> 监听按键值"""
import os, sys, time
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

DEV = r"D:\数据文件\上课\信电导论\开发板"

d = MyBit("COM3")
try:
    print("[0] 当前板载:", d.ls())

    print("\n[1] 替换 boot.py（不再删除 main.py）")
    n = d.put(os.path.join(DEV, "boot_safe.py"), "boot.py")
    print("    ", n, "bytes")
    print("     校验:", d.exec(
        "f=open('boot.py');s=f.read();f.close();print('含remove:', 'os.remove' in s)",
        deadline=15).strip())

    print("\n[2] 重新烧录贪吃蛇为 main.py")
    n = d.put(os.path.join(DEV, "snake.py"), "main.py")
    print("    ", n, "bytes")
    print("     板载:", d.ls())

    print("\n[3] 软重启")
    d.ser.write(b"\x03\x03")
    time.sleep(0.25)
    d._drain(0.3)
    d.ser.write(b"\x04")

    print("[4] 监听 18 秒 —— 请先按一下 B，再按一下 A")
    print("    " + "-" * 52)
    t_end = time.time() + 18
    buf = b""
    while time.time() < t_end:
        chunk = d.ser.read(d.ser.in_waiting or 1)
        if chunk:
            buf += chunk
            sys.stdout.write(chunk.decode("utf-8", "replace"))
            sys.stdout.flush()
    print("\n    " + "-" * 52)
    print("[5] 原始回显:")
    print(repr(buf.decode("utf-8", "replace"))[:2000])
    print("\n[6] 重连后板载文件:")
    print("    ", d.ls())
finally:
    d.close()
