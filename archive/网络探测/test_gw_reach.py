# -*- coding: utf-8 -*-
"""测试板子能否访问电脑上的 AI 网关"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import network, time, socket
w = network.WLAN(network.STA_IF)
w.active(0)
time.sleep(0.6)
w.active(1)
time.sleep(1.0)
if not w.isconnected():
    w.connect('YOUR_CAMPUS_SSID')
    t = time.time()
    while not w.isconnected() and time.time() - t < 20:
        time.sleep(0.4)
print('板子 IP:', w.ifconfig()[0])
s = socket.socket()
s.settimeout(6)
try:
    s.connect(('PC_IP', 8080))
    s.send(b'GET /api/ping HTTP/1.0\r\nHost: gw\r\n\r\n')
    buf = b''
    while len(buf) < 300:
        c = s.recv(200)
        if not c:
            break
        buf += c
    print('网关响应:')
    print(buf.decode('utf-8', 'replace')[-200:])
except Exception as e:
    print('连接失败:', type(e).__name__, e)
s.close()
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\gwreach.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "gwreach.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.25); d._drain(0.3)
    d.ser.write(b"\x04"); time.sleep(1.6)
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.5)
    print(d.exec("exec(open('gwreach.py').read())", deadline=90).strip()[:2000])
finally:
    d.close()
