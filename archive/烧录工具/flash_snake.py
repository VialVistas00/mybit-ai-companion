# -*- coding: utf-8 -*-
"""烧录贪吃蛇到板子并验证启动"""
import os, sys, time
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

DEV = r"D:\数据文件\上课\信电导论\开发板"
BK = os.path.join(DEV, "_board_backup")

d = MyBit("COM3")
try:
    print("[0] 先备份当前 main.py（报时时钟版）")
    n = d.get("main.py", os.path.join(BK, "main_clock.py"))
    print("    ->", n, "bytes")

    print("\n[1] 上传贪吃蛇为 main.py")
    src = os.path.join(DEV, "snake.py")
    n = d.put(src, "main.py")
    print("    ", n, "bytes")
    print("     板载:", d.ls())
    print("     校验:", d.exec(
        "import ubinascii;f=open('main.py','rb');b=f.read();f.close();"
        "print(len(b), ubinascii.hexlify(b[:16]).decode())", deadline=20).strip())

    print("\n[2] 软重启，观察启动输出（游戏在等按键）")
    d.ser.write(b"\x03\x03"); time.sleep(0.2); d._drain(0.3)
    d.ser.write(b"\x04")
    time.sleep(3.0)
    out = d._drain(2.0).decode("utf-8", "replace")
    print("     回显:", repr(out[:500]))

    print("\n[3] 中断，看程序停在哪个位置（应在等待按键处）")
    d.ser.write(b"\x03"); time.sleep(0.25)
    d.ser.write(b"\x03"); time.sleep(0.2)
    intr = d._drain(1.2).decode("utf-8", "replace")
    print("     ", repr(intr[:600]))
finally:
    d.close()
