# -*- coding: utf-8 -*-
"""抓 Portal.js 找登录请求的真实构造方式"""
import os, sys, time
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import network, time
import srun_client as S

PORTAL = 'PORTAL_IP'
w = network.WLAN(network.STA_IF)
if not w.isconnected():
    w.connect('YOUR_CAMPUS_SSID'); t=time.time()
    while not w.isconnected() and time.time()-t<20: time.sleep(0.4)

js = S.http_get(PORTAL, 80, '/static/themes/pro/js/Portal.js?v=a32e00343444a19a', maxlen=20000, timeout=15)
print('Portal.js 长度', len(js))
body = js.split('\r\n\r\n')
body = body[1] if len(body) > 1 else js

keys = ['srun_portal', 'get_challenge', 'cgi-bin', 'chksum', 'enc_ver', 'info', 'action', 'login', 'callback']
print()
print('--- 关键片段 ---')
seen = []
low = body.lower()
for k in keys:
    idx = 0
    cnt = 0
    while True:
        idx = low.find(k.lower(), idx)
        if idx < 0 or cnt >= 4:
            break
        seg = body[max(0, idx - 120): idx + 200]
        seg = seg.replace('\n', ' ').replace('\r', ' ')
        if seg not in seen:
            seen.append(seg)
            print('[' + k + '] ...' + seg + '...')
            print()
        idx += len(k)
        cnt += 1
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\pj.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    print("[upload]", d.put(tmp, "portal_js.py"), "bytes")

    d.ser.write(b"\x03\x03"); time.sleep(0.25); d._drain(0.3)
    d.ser.write(b"\x04"); time.sleep(1.6)
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.5)

    print(d.exec("exec(open('portal_js.py').read())", deadline=180).strip()[:8000])
finally:
    d.close()
