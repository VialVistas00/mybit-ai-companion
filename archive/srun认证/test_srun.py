# -*- coding: utf-8 -*-
"""摸清 SRun Portal 认证接口（不需要密码的部分）"""
import sys
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = """import socket, time

def http(host, port, path, hosthdr=None, maxlen=900):
    try:
        s = socket.socket(); s.settimeout(8)
        s.connect(socket.getaddrinfo(host, port)[0][4])
        hh = hosthdr if hosthdr else host
        req = 'GET ' + path + ' HTTP/1.1\\r\\nHost: ' + hh + '\\r\\nConnection: close\\r\\nUser-Agent: Mozilla/5.0\\r\\n\\r\\n'
        s.send(req.encode())
        buf = b''
        while len(buf) < maxlen:
            try: c = s.recv(300)
            except Exception: break
            if not c: break
            buf += c
        s.close()
        return buf.decode('utf-8', 'replace')
    except Exception as e:
        return 'ERR ' + type(e).__name__ + ' ' + str(e)

ip = network.WLAN(network.STA_IF).ifconfig()[0]
ts = str(int(time.time() * 1000))
print('板子 IP:', ip)
print()
print('=== 1. 取 challenge / token ===')
r = http('PORTAL_IP', 80,
         '/cgi-bin/get_challenge?callback=cb&username=YOUR_STUDENT_ID&ip=' + ip + '&_=' + ts)
print(r[:600])
print()
print('=== 2. 取认证页面 ===')
r2 = http('PORTAL_IP', 80, '/srun_portal_pc?ac_id=1&theme=pro', maxlen=1200)
print(r2[:900])
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
        "print('connected', w.isconnected(), w.ifconfig()[0])", deadline=60).strip())
    print()
    print(d.exec(CODE, deadline=90).strip())
finally:
    d.close()
