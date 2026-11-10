# -*- coding: utf-8 -*-
"""补充 mac / nas_ip / ap_id 等参数，看 auth_info_error 是否消失"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import network, time
import srun_client as S

PORTAL = 'PORTAL_IP'
PWD = 'YOUR_PASSWORD'
AC = '1'

w = network.WLAN(network.STA_IF)
if not w.isconnected():
    w.connect('YOUR_CAMPUS_SSID'); t = time.time()
    while not w.isconnected() and time.time() - t < 20: time.sleep(0.4)
ip = w.ifconfig()[0]
mac_raw = w.config('mac')
mac = ':'.join(['%02x' % b for b in mac_raw])
print('板子 IP =', ip, ' MAC =', mac)
print()

def attempt(user, extra, label):
    ts = str(int(time.time() * 1000))
    r = S.http_get(PORTAL, 80, '/cgi-bin/get_challenge?callback=cb&username=' + S.quote(user) + '&ip=' + ip + '&_=' + ts)
    j = S._json_of(r)
    if not j or 'challenge' not in j:
        return 'challenge_fail'
    token = j['challenge']
    hmd5 = S.md5(PWD + token)
    info_json = '{"username":"%s","password":"%s","ip":"%s","acid":"%s","enc_ver":"srun_bx1"}' % (user, PWD, ip, AC)
    info_enc = '{SRBX1}' + S.b64(S.xencode(info_json, token))
    chksum = S.sha1(token + user + token + hmd5 + token + AC + token + ip + token + '200' + token + '1' + token + info_enc)
    url = ('/cgi-bin/srun_portal?callback=cb&action=login&username=' + S.quote(user)
           + '&password=' + S.quote('{MD5}' + hmd5) + '&ac_id=' + AC + '&ip=' + ip
           + '&chksum=' + chksum + '&info=' + S.quote(info_enc)
           + '&n=200&type=1&os=Windows&name=Windows&double_stack=0'
           + extra + '&_=' + ts)
    r2 = S.http_get(PORTAL, 80, url)
    j2 = S._json_of(r2)
    if not j2:
        return 'empty'
    return str(j2.get('error')) + ' | ' + str(j2.get('error_msg'))

tests = [
    ('YOUR_ACCOUNT', '', 'baseline'),
    ('YOUR_ACCOUNT', '&mac=' + S.quote(mac), 'with mac'),
    ('YOUR_ACCOUNT', '&mac=' + S.quote(mac.replace(':', '')), 'with mac nonsep'),
    ('YOUR_ACCOUNT', '&nas_ip=' + w.ifconfig()[2], 'with nas_ip'),
    ('YOUR_ACCOUNT', '&mac=' + S.quote(mac) + '&nas_ip=' + w.ifconfig()[2], 'mac+nas'),
    ('YOUR_ACCOUNT@mac', '&mac=' + S.quote(mac), 'YOUR_ACCOUNT@mac + mac'),
]
for user, extra, label in tests:
    try:
        res = attempt(user, extra, label)
    except Exception as e:
        res = 'EXC ' + type(e).__name__ + ' ' + str(e)
    print('%-18s %-12s -> %s' % (user, label, res))
    time.sleep(1.5)
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\v2.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    print("[upload]", d.put(tmp, "login_mac.py"), "bytes")

    d.ser.write(b"\x03\x03"); time.sleep(0.25); d._drain(0.3)
    d.ser.write(b"\x04"); time.sleep(1.6)
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.5)

    print(d.exec("exec(open('login_mac.py').read())", deadline=240).strip()[:4000])
finally:
    d.close()
