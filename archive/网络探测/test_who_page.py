# -*- coding: utf-8 -*-
"""关键验证：板子访问 SERVER_IP:80 时，拿到的到底是谁的页面"""
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
ip = w.ifconfig()[0]
print('板子 IP:', ip)
print()

def fetch(ip, port, path, maxlen=800):
    s = socket.socket()
    s.settimeout(8)
    try:
        s.connect((ip, port))
        s.send(('GET ' + path + ' HTTP/1.0\r\nHost: ' + ip + '\r\nConnection: close\r\n\r\n').encode())
        buf = b''
        while len(buf) < maxlen:
            try:
                c = s.recv(400)
            except Exception:
                break
            if not c:
                break
            buf += c
        s.close()
        return buf.decode('utf-8', 'replace')
    except Exception as e:
        s.close()
        return 'ERR ' + type(e).__name__ + ' ' + str(e)[:40]

print('--- 板子 GET http://SERVER_IP/ ---')
r = fetch('SERVER_IP', 80, '/')
print(r[:500])
print()
print('--- 板子 GET http://SERVER_IP/health ---')
print(fetch('SERVER_IP', 80, '/health')[:300])
print()
print('--- 板子 GET http://PORTAL_IP/ ---')
print(fetch('PORTAL_IP', 80, '/')[:300])
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\whopage.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "whopage.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.4); d._drain(0.4)
    print(d.exec("import gc;gc.collect()\nexec(open('whopage.py').read())", deadline=90).strip()[:2000])
finally:
    d.close()
