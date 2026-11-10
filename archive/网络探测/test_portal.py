# -*- coding: utf-8 -*-
"""确认 AP 隔离 + 抓 Portal 表单 + 探测 SERVER_IP 可达性
   注：ESP32 MicroPython 无原生 ICMP ping，用 TCP connect 判定可达性（等价且更严格）
"""
import sys
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = """import socket

def tcp_probe(ip, port, timeout=3):
    s = socket.socket(); s.settimeout(timeout)
    try:
        s.connect((ip, port))
        s.close()
        return '通'
    except Exception as e:
        s.close()
        return type(e).__name__ + ' ' + str(e)

def http_get(host, port, path, maxlen=1200):
    try:
        addr = socket.getaddrinfo(host, port)[0][4]
        s = socket.socket(); s.settimeout(7)
        s.connect(addr)
        s.send(('GET ' + path + ' HTTP/1.1\\r\\nHost: ' + host + '\\r\\nConnection: close\\r\\nUA: t\\r\\n\\r\\n').encode())
        buf = b''
        while len(buf) < maxlen:
            try: c = s.recv(256)
            except Exception: break
            if not c: break
            buf += c
        s.close()
        return buf.decode('utf-8', 'replace')
    except Exception as e:
        return 'ERR ' + type(e).__name__ + ' ' + str(e)

print('--- 0. 板子网络 ---')
import network
w = network.WLAN(network.STA_IF)
print('ifconfig', w.ifconfig())

print()
print('--- A. 网关 CAMPUS_GW ---')
for p in (80, 443):
    print('  ', p, tcp_probe('CAMPUS_GW', p))

print()
print('--- B. 同网段 (10.60.x) 隔离测试 ---')
for ip in ('PC_IP', '10.60.204.1', '10.60.204.254'):
    print('  ', ip, ':80', tcp_probe(ip, 80))

print()
print('--- C. 目标 SERVER_IP 多端口探测 ---')
for p in (80, 443, 22, 8080, 5000, 1883):
    print('   SERVER_IP:', p, tcp_probe('SERVER_IP', p, 4))

print()
print('--- D. 10.61.x 网段其他地址对照 ---')
for ip in ('CAMPUS_DNS', '10.61.0.1'):
    print('  ', ip, ':80', tcp_probe(ip, 80))
"""

d = MyBit("COM3")
try:
    print(d.exec(CODE, deadline=120).strip())

    print("\n\n=== E. Portal 认证页结构 ===")
    print(d.exec(
        "import socket\n"
        "addr=socket.getaddrinfo('PORTAL_IP',80)[0][4]\n"
        "s=socket.socket(); s.settimeout(8); s.connect(addr)\n"
        "s.send(b'GET /index_1.html HTTP/1.1\\r\\nHost: PORTAL_IP\\r\\nConnection: close\\r\\nUA: Mozilla/5.0\\r\\n\\r\\n')\n"
        "buf=b''\n"
        "while len(buf)<3500:\n"
        "    try: c=s.recv(512)\n"
        "    except Exception: break\n"
        "    if not c: break\n"
        "    buf+=c\n"
        "s.close()\n"
        "print(buf.decode('utf-8','replace')[:3000])", deadline=40).strip())
finally:
    d.close()
