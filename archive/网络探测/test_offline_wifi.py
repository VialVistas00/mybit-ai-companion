# -*- coding: utf-8 -*-
"""离线供电方案的可行性测试：板子连 WiFi，测能否访问电脑"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import network, time, socket
w = network.WLAN(network.STA_IF)
w.active(0)
time.sleep(0.8)
w.active(1)
time.sleep(1.5)
if not w.isconnected():
    w.connect('YOUR_CAMPUS_SSID')
    t = time.time()
    while not w.isconnected() and time.time() - t < 20:
        time.sleep(0.4)
print('connected', w.isconnected())
print('ifconfig', w.ifconfig())
if w.isconnected():
    s = socket.socket()
    s.settimeout(5)
    try:
        s.connect(('PC_IP', 8080))
        s.send(b'GET / HTTP/1.0\r\n\r\n')
        d = s.recv(100)
        print('连电脑 8080: 通', d[:40])
    except Exception as e:
        print('连电脑 8080 失败:', type(e).__name__, e)
    s.close()
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\wifi_test.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "wifi_test.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.4); d._drain(0.4)
    print(d.exec("import gc;gc.collect()\nexec(open('wifi_test.py').read())", deadline=90).strip()[:1200])
finally:
    d.close()
