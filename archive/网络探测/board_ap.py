# -*- coding: utf-8 -*-
"""板子开 AP，电脑连上去，验证互通"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''from npython import wifi
import network, time
try:
    wifi.disable_AP()
except Exception:
    pass
time.sleep(0.8)
wifi.enable_AP('MYBIT_AI', 'YOUR_WIFI_PASSWORD', 10)
time.sleep(2.0)
ap = network.WLAN(network.AP_IF)
print('AP active:', ap.active())
print('AP ifconfig:', ap.ifconfig())
print('AP ssid:', ap.config('essid'))
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\openap.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "openap.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.25); d._drain(0.3)
    d.ser.write(b"\x04"); time.sleep(1.6)
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.5)
    print(d.exec("exec(open('openap.py').read())", deadline=60).strip()[:1200])
finally:
    d.close()
    print("\n[串口已释放，板子热点应保持开启]")
