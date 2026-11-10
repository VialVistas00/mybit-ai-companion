# -*- coding: utf-8 -*-
"""先确保连上 YOUR_CAMPUS_SSID，再测隔离 + SERVER_IP + Portal"""
import sys
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CONNECT = """import network, time
w = network.WLAN(network.STA_IF)
w.active(0); time.sleep(0.8); w.active(1); time.sleep(1.5)
if w.isconnected():
    print('已在线:', w.ifconfig())
else:
    print('重连 YOUR_CAMPUS_SSID ...')
    try:
        w.connect('YOUR_CAMPUS_SSID')
    except Exception as e:
        print('connect err', e)
    t = time.time()
    while not w.isconnected() and time.time() - t < 20:
        time.sleep(0.4)
    print('connected =', w.isconnected())
    print('ifconfig  =', w.ifconfig())
"""

PROBE = """import socket

def probe(ip, port, timeout=4):
    s = socket.socket(); s.settimeout(timeout)
    try:
        s.connect((ip, port)); s.close(); return '通'
    except Exception as e:
        s.close(); return 'Err' + str(e)

print('--- A. 网关 CAMPUS_GW ---')
for p in (80, 443):
    print('   :%d' % p, probe('CAMPUS_GW', p))

print('--- B. 同网段 10.60.x 隔离测试 ---')
for ip in ('PC_IP', '10.60.204.1', '10.60.204.254'):
    print('  ', ip, probe(ip, 80))

print('--- C. 目标 SERVER_IP ---')
for p in (80, 443, 22, 8080, 5000, 1883, 3389):
    print('   :%-5d' % p, probe('SERVER_IP', p, 5))

print('--- D. 对照 10.61.x ---')
for ip in ('CAMPUS_DNS', '10.61.0.1'):
    print('  ', ip, probe(ip, 80))
"""

d = MyBit("COM3")
try:
    print("[0] 建立/确认 WiFi 连接")
    print(d.exec(CONNECT, deadline=60).strip())

    print("\n[1] 可达性探测")
    print(d.exec(PROBE, deadline=120).strip())

    print("\n[2] Portal 认证页（前 2200 字节）")
    print(d.exec(
        "import socket\n"
        "s=socket.socket(); s.settimeout(8)\n"
        "s.connect(socket.getaddrinfo('PORTAL_IP',80)[0][4])\n"
        "s.send(b'GET /index_1.html HTTP/1.1\\r\\nHost: PORTAL_IP\\r\\nConnection: close\\r\\nUA: Mozilla/5.0\\r\\n\\r\\n')\n"
        "buf=b''\n"
        "while len(buf)<2600:\n"
        "    try: c=s.recv(400)\n"
        "    except Exception: break\n"
        "    if not c: break\n"
        "    buf+=c\n"
        "s.close()\n"
        "print(buf.decode('utf-8','replace')[:2200])", deadline=40).strip())
finally:
    d.close()
