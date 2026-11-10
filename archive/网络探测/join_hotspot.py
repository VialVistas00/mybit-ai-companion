# -*- coding: utf-8 -*-
"""板子连接电脑热点 MYBIT_HOTSPOT，验证到网关的连通性"""
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
time.sleep(1.2)
r = w.scan()
hit = [s for s in r if b'MYBIT' in s[0]]
print('扫描到 MYBIT 热点:', len(hit))
for s in hit:
    try:
        print('  ', s[0].decode('utf-8', 'replace'), 'ch', s[2], 'rssi', s[3])
    except Exception:
        print('  ', s[0], s[2], s[3])

try:
    w.connect('MYBIT_HOTSPOT', 'YOUR_WIFI_PASSWORD')
except Exception as e:
    print('connect err', e)
t = time.time()
while not w.isconnected() and time.time() - t < 25:
    time.sleep(0.4)
print('connected =', w.isconnected())
print('ifconfig  =', w.ifconfig())

if w.isconnected():
    s = socket.socket()
    s.settimeout(8)
    try:
        s.connect(('HOTSPOT_IP', 8080))
        s.send(b'GET /api/ping HTTP/1.0\r\nHost: gw\r\n\r\n')
        buf = b''
        while len(buf) < 400:
            c = s.recv(200)
            if not c:
                break
            buf += c
        print('网关响应:')
        print(buf.decode('utf-8', 'replace')[-220:])
    except Exception as e:
        print('网关连接失败:', type(e).__name__, e)
    s.close()
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\joinhot.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "joinhot.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.25); d._drain(0.3)
    d.ser.write(b"\x04"); time.sleep(1.6)
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.5)
    print(d.exec("exec(open('joinhot.py').read())", deadline=120).strip()[:2500])
finally:
    d.close()
