# -*- coding: utf-8 -*-
"""验证板子在校园网下能否访问 SERVER_IP"""
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import network, time, socket
w = network.WLAN(network.STA_IF)
if not w.isconnected():
    w.active(0); time.sleep(0.8); w.active(1); time.sleep(1.5)
    w.connect('YOUR_CAMPUS_SSID')
    t = time.time()
    while not w.isconnected() and time.time() - t < 20:
        time.sleep(0.4)
print('板子 IP:', w.ifconfig()[0])
print()

def probe(ip, port, t=5):
    s = socket.socket()
    s.settimeout(t)
    try:
        s.connect((ip, port))
        s.close()
        return '通'
    except Exception as e:
        s.close()
        return '%s %s' % (type(e).__name__, str(e)[:30])

for port in (9446, 8080, 80, 443, 22):
    print('  SERVER_IP:%-5d %s' % (port, probe('SERVER_IP', port)))
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\srv.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "srv.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.4); d._drain(0.4)
    print(d.exec("import gc;gc.collect()\nexec(open('srv.py').read())", deadline=90).strip()[:1200])
finally:
    d.close()
