# -*- coding: utf-8 -*-
"""验证板子对 SERVER_IP:80 的响应到底是目标服务还是 Portal 劫持"""
import sys
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = """import socket

def raw(ip, port, path='/', maxlen=700):
    s = socket.socket(); s.settimeout(8)
    try:
        s.connect((ip, port))
        s.send(('GET ' + path + ' HTTP/1.1\\r\\nHost: ' + ip + '\\r\\nConnection: close\\r\\n\\r\\n').encode())
        buf = b''
        while len(buf) < maxlen:
            try: c = s.recv(300)
            except Exception: break
            if not c: break
            buf += c
        s.close()
        return buf.decode('utf-8', 'replace')
    except Exception as e:
        s.close()
        return 'ERR ' + type(e).__name__ + ' ' + str(e)

print('=== 板子 GET http://SERVER_IP/ ===')
print(raw('SERVER_IP', 80)[:600])
print()
print('=== 板子 GET http://SERVER_IP:8080/ ===')
print(raw('SERVER_IP', 8080)[:300])
print()
print('=== 板子 GET http://PC_IP:8080/ (电脑) ===')
print(raw('PC_IP', 8080)[:300])
"""

d = MyBit("COM3")
try:
    print(d.exec(
        "import network,time\n"
        "w=network.WLAN(network.STA_IF)\n"
        "w.active(0);time.sleep(0.8);w.active(1);time.sleep(1.2)\n"
        "if not w.isconnected():\n"
        "    w.connect('YOUR_CAMPUS_SSID')\n"
        "    t=time.time()\n"
        "    while not w.isconnected() and time.time()-t<20: time.sleep(0.4)\n"
        "print('ifconfig', w.ifconfig())", deadline=60).strip())
    print()
    print(d.exec(CODE, deadline=90).strip())
finally:
    d.close()
