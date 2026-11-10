# -*- coding: utf-8 -*-
"""抓 Portal 页面 JS，找出真实的登录请求格式"""
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

page = S.http_get(PORTAL, 80, '/srun_portal_pc?ac_id=1&theme=pro', maxlen=8000)
print('页面长度', len(page))
print()
print('--- 含 script / src 的行 ---')
for line in page.split('\n'):
    l = line.strip()
    if 'script' in l and ('src=' in l or '.js' in l):
        print(' ', l[:160])
print()
print('--- 含 cgi / srun_portal / login 的行 ---')
for line in page.split('\n'):
    l = line.strip()
    if ('cgi' in l) or ('srun_portal' in l) or ('get_challenge' in l):
        print(' ', l[:200])
print()
print('--- 前 1200 字节正文 ---')
parts = page.split('\r\n\r\n')
body = parts[1] if len(parts) > 1 else page
print(body[:1200])
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\p.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    print("[upload]", d.put(tmp, "portal_probe.py"), "bytes")

    d.ser.write(b"\x03\x03"); time.sleep(0.25); d._drain(0.3)
    d.ser.write(b"\x04"); time.sleep(1.6)
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.5)

    print(d.exec("exec(open('portal_probe.py').read())", deadline=120).strip())
finally:
    d.close()
