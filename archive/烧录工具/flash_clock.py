# -*- coding: utf-8 -*-
"""把作业1《报时时钟程序》烧录到板子 main.py 并验证运行"""
import datetime, os, re, time
from mybit import MyBit

DEV = r"D:\数据文件\上课\信电导论\开发板"
SRC = r"D:\数据文件\上课\信电导论\作业1电子时钟\报时时钟程序.py"
STAGE = os.path.join(DEV, "_flash_main.py")

src = open(SRC, encoding="utf-8").read()
# 把 RTC 初值改成当前时间（原文件写死 2023-11-14）
now = datetime.datetime.now()
wd = now.isoweekday() % 7            # MicroPython: 0=周一 … 6=周日
new_line = "rtc.datetime((%d, %d, %d, %d, %d, %d, %d, 0))" % (
    now.year, now.month, now.day, wd, now.hour, now.minute, now.second)
src2 = re.sub(r"rtc\.datetime\(\([^)]*\)\)\s*#\s*（年", new_line + " # （年", src, count=1)
assert src2 != src, "RTC 初值替换失败"
open(STAGE, "w", encoding="utf-8").write(src2)
print("[*] 已生成本地烧录文件 _flash_main.py  (%d 字符)" % len(src2))
print("    注入 RTC 初值 ->", new_line)

d = MyBit("COM3")
try:
    print("\n[1] 上传为板上 main.py")
    n = d.put(STAGE, "main.py")
    print("    ", n, "bytes")
    print("     板载:", d.ls())

    print("\n[2] 校验板上文件与本地一致")
    print("    ", d.exec(
        "import ubinascii;f=open('main.py','rb');b=f.read();f.close();"
        "print(len(b), ubinascii.hexlify(b[:16]).decode())", deadline=15).strip())

    print("\n[3] 软重启，让 main.py 上电执行")
    d.ser.write(b"\x02\x03\x04")
    time.sleep(0.2)
    boot = d._drain(3.5).decode("utf-8", "replace")
    print("     启动回显:", repr(boot[:400]))

    print("\n[4] 运行 4 秒后中断，验证 main.py 是否在跑")
    time.sleep(4)
    d.ser.write(b"\x03")
    time.sleep(0.2)
    d.ser.write(b"\x03")
    intr = d._drain(1.5).decode("utf-8", "replace")
    print("     ", repr(intr[:500]))

    print("\n[5] 板子当前状态")
    print("    ", d.exec(
        "from machine import RTC;r=RTC();print('RTC',r.datetime());"
        "from npython import aht20,light,sound;"
        "print('T=%.2f H=%.2f L=%d S=%d'%(aht20.read_temp(),aht20.read_hum(),light.read(),sound.read()))",
        deadline=20).strip())
finally:
    d.close()
