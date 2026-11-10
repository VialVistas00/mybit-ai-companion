# -*- coding: utf-8 -*-
"""
flash_plane.py —— 把 plane.py（飞机打外星人）烧成板子的 main.py
用法：插好 USB，关掉其它占用 COM3 的软件（编程工具/串口助手），然后
      python flash_plane.py
会自动：备份现有 main.py -> 上传 plane.py 为 main.py -> 软重启 -> 打印启动输出
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mybit import MyBit

DEV = os.path.dirname(os.path.abspath(__file__))
PORT = sys.argv[1] if len(sys.argv) > 1 else "COM3"
BACKUP = os.path.join(DEV, "_board_backup", "main_before_plane.py")

d = MyBit(PORT)
try:
    # 1) 备份现有 main.py
    try:
        n = d.get("main.py", BACKUP)
        print("已备份原 main.py ->", BACKUP, "(%d bytes)" % n)
    except Exception as e:
        print("原 main.py 备份失败（可能本来就没有）:", e)

    # 2) 上传
    n = d.put(os.path.join(DEV, "plane.py"), "main.py")
    print("已上传 main.py:", n, "bytes")

    # 3) 核对板载大小
    size = d.exec("import os;print(os.stat('main.py')[6])", deadline=20).strip()
    print("板载 main.py 大小:", size)

    # 4) 软重启看启动输出
    d.ser.write(b"\x03\x03")
    time.sleep(0.25)
    d._drain(0.3)
    d.ser.write(b"\x04")
    print("\n重启后 3 秒内的串口输出：")
    t_end = time.time() + 3
    buf = b""
    while time.time() < t_end:
        chunk = d.ser.read(d.ser.in_waiting or 1)
        if chunk:
            buf += chunk
    print(repr(buf.decode("utf-8", "replace"))[:900])
finally:
    d.close()
    print("\n串口已释放。屏幕上应该出现 PLANE vs ALIEN 标题，按 A 或 B 开始。")
