# -*- coding: utf-8 -*-
"""排查 auth_info_error：验证 info 结构、mac 认证域、以及各接口的响应"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import network, time
import srun_client as S

PORTAL = 'PORTAL_IP'
PWD = 'YOUR_PASSWORD'
USER = 'YOUR_ACCOUNT'
AC = '1'

w = network.WLAN(network.STA_IF)
if not w.isconnected():
    w.connect('YOUR_CAMPUS_SSID'); t = time.time()
    while not w.isconnected() and time.time() - t < 20: time.sleep(0.4)
ip = w.ifconfig()[0]
mac = ':'.join(['%02x' % b for b in w.config('mac')])
print('ip =', ip, 'mac =', mac)
print()

def g(path, maxlen=900):
    r = S.http_get(PORTAL, 80, path, maxlen=maxlen)
    return r.split('\r\n\r\n')[1] if '\r\n\r\n' in r else r

ts = str(int(time.time() * 1000))

print('=== 1) 本 IP 的在线状态 ===')
print(g('/cgi-bin/rad_user_info?callback=cb&_=' + ts)[:400])
print()

print('=== 2) 按 MAC 查在线 (mac 域) ===')
print(g('/cgi-bin/rad_user_info?callback=cb&user_mac=' + S.quote(mac) + '&_=' + ts)[:400])
print()

print('=== 3) 检查是否支持无感/mac快速认证接口 ===')
for p in ('/v1/srun_portal_mac', '/cgi-bin/srun_portal_mac'):
    print(p, '->', g(p + '?callback=cb&_=' + ts, 300)[:160])
print()

print('=== 4) 手工构造一次 login，打印完整响应 ===')
r = S.http_get(PORTAL, 80, '/cgi-bin/get_challenge?callback=cb&username=' + USER + '&ip=' + ip + '&_=' + ts)
token = S._json_of(r)['challenge']
hmd5 = S.md5(PWD + token)
info_json = '{"username":"%s","password":"%s","ip":"%s","acid":"%s","enc_ver":"srun_bx1"}' % (USER, PWD, ip, AC)
info_enc = '{SRBX1}' + S.b64(S.xencode(info_json, token))
chksum = S.sha1(token + USER + token + hmd5 + token + AC + token + ip + token + '200' + token + '1' + token + info_enc)
url = ('/cgi-bin/srun_portal?callback=cb&action=login&username=' + USER
       + '&password=' + S.quote('{MD5}' + hmd5) + '&ac_id=' + AC + '&ip=' + ip
       + '&chksum=' + chksum + '&info=' + S.quote(info_enc)
       + '&n=200&type=1&os=Windows&name=Windows&double_stack=0&_=' + ts)
raw = S.http_get(PORTAL, 80, url, maxlen=800)
print(raw[:700])
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\diag.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "diag.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.25); d._drain(0.3)
    d.ser.write(b"\x04"); time.sleep(1.6)
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.5)
    print(d.exec("exec(open('diag.py').read())", deadline=150).strip()[:4500])
finally:
    d.close()
