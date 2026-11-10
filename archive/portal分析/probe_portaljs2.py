# -*- coding: utf-8 -*-
"""流式扫描 Portal.js（不整存，避免 MemoryError）"""
import os, sys, time
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import network, time, socket
import srun_client as S

PORTAL = 'PORTAL_IP'
w = network.WLAN(network.STA_IF)
if not w.isconnected():
    w.connect('YOUR_CAMPUS_SSID'); t=time.time()
    while not w.isconnected() and time.time()-t<20: time.sleep(0.4)

path = '/static/themes/pro/js/Portal.js?v=a32e00343444a19a'
s = socket.socket(); s.settimeout(15)
s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
s.send(('GET ' + path + ' HTTP/1.1\r\nHost: ' + PORTAL + '\r\nConnection: close\r\nUser-Agent: Mozilla/5.0\r\n\r\n').encode())

KEYS = ['srun_portal', 'get_challenge', 'cgi-bin', 'chksum', 'enc_ver', 'SRBX1', 'callback=', 'ac_id']
tail = b''
total = 0
hits = 0
while total < 300000:
    try:
        c = s.recv(700)
    except Exception:
        break
    if not c:
        break
    total += len(c)
    buf = (tail + c).decode('utf-8', 'replace')
    for k in KEYS:
        idx = buf.find(k)
        while idx >= 0 and hits < 26:
            seg = buf[max(0, idx - 130): idx + 230].replace('\n', ' ').replace('\r', ' ')
            print('[' + k + '] ' + seg)
            print()
            hits += 1
            idx = buf.find(k, idx + len(k))
    tail = c[-500:]
s.close()
print('总下载', total, '字节, 命中片段', hits)
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\pj2.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    print("[upload]", d.put(tmp, "portal_js2.py"), "bytes")

    d.ser.write(b"\x03\x03"); time.sleep(0.25); d._drain(0.3)
    d.ser.write(b"\x04"); time.sleep(1.6)
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.5)

    print(d.exec("exec(open('portal_js2.py').read())", deadline=180).strip()[:9000])
finally:
    d.close()
