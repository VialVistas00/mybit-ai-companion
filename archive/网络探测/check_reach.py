# -*- coding: utf-8 -*-
"""确认板子在 YOUR_CAMPUS_SSID 下能否访问 SERVER_IP"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import network, time, socket

w = network.WLAN(network.STA_IF)
if not w.isconnected():
    w.connect('YOUR_CAMPUS_SSID'); t = time.time()
    while not w.isconnected() and time.time() - t < 20: time.sleep(0.4)
print('板子 ifconfig:', w.ifconfig())
print('rssi:', w.status('rssi'))
print()

def req(ip, port, path, timeout=8):
    s = socket.socket(); s.settimeout(timeout)
    try:
        s.connect((ip, port))
        s.send(('GET ' + path + ' HTTP/1.0\r\nHost: ' + ip + '\r\n\r\n').encode())
        buf = b''
        while len(buf) < 400:
            try: c = s.recv(200)
            except Exception: break
            if not c: break
            buf += c
        s.close()
        return buf.decode('utf-8', 'replace')
    except Exception as e:
        s.close()
        return 'ERR ' + type(e).__name__ + ' ' + str(e)

for port, path in ((8080, '/'), (8080, '/health'), (80, '/')):
    print('--- SERVER_IP:%d%s ---' % (port, path))
    print(req('SERVER_IP', port, path)[:300])
    print()
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\reach.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "reach.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.25); d._drain(0.3)
    d.ser.write(b"\x04"); time.sleep(1.6)
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.5)
    print(d.exec("exec(open('reach.py').read())", deadline=120).strip()[:3000])
finally:
    d.close()
