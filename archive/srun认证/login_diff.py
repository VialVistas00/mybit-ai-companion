# -*- coding: utf-8 -*-
"""差分诊断：逐个改坏字段，通过错误码变化定位真正的失败点"""
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
print('ip =', ip)
print()

def build(mutate=None):
    ts = str(int(time.time() * 1000))
    r = S.http_get(PORTAL, 80, '/cgi-bin/get_challenge?callback=cb&username=' + S.quote(USER) + '&ip=' + ip + '&_=' + ts)
    j = S._json_of(r)
    token = j['challenge']
    hmd5 = S.md5(PWD + token)
    info_json = '{"username":"%s","password":"%s","ip":"%s","acid":"%s","enc_ver":"srun_bx1"}' % (USER, PWD, ip, AC)
    info_enc = '{SRBX1}' + S.b64(S.xencode(info_json, token))
    chksum = S.sha1(token + USER + token + hmd5 + token + AC + token + ip + token + '200' + token + '1' + token + info_enc)
    pw = '{MD5}' + hmd5
    if mutate == 'bad_chksum':
        chksum = '0' * 40
    elif mutate == 'bad_info':
        info_enc = '{SRBX1}REDACTED'
    elif mutate == 'bad_pwd':
        pw = '{MD5}' + '0' * 32
    elif mutate == 'no_chksum':
        chksum = ''
    url = ('/cgi-bin/srun_portal?callback=cb&action=login&username=' + S.quote(USER)
           + '&password=' + S.quote(pw) + '&ac_id=' + AC + '&ip=' + ip
           + '&chksum=' + chksum + '&info=' + S.quote(info_enc)
           + '&n=200&type=1&os=Windows&name=Windows&double_stack=0&_=' + ts)
    r2 = S.http_get(PORTAL, 80, url)
    j2 = S._json_of(r2)
    if not j2:
        return 'empty_response'
    return 'error=%-22s msg=%s' % (str(j2.get('error')), str(j2.get('error_msg')))

cases = [
    (None, 'baseline(正常参数)'),
    ('bad_pwd', '密码改成全0'),
    ('bad_info', 'info改成垃圾'),
    ('bad_chksum', 'chksum改成全0'),
    ('no_chksum', 'chksum留空'),
]
for m, label in cases:
    try:
        print('%-18s -> %s' % (label, build(m)))
    except Exception as e:
        print('%-18s -> EXC %s %s' % (label, type(e).__name__, e))
    time.sleep(1.2)
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\v3.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    print("[upload]", d.put(tmp, "login_diff.py"), "bytes")

    d.ser.write(b"\x03\x03"); time.sleep(0.25); d._drain(0.3)
    d.ser.write(b"\x04"); time.sleep(1.6)
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.5)

    print(d.exec("exec(open('login_diff.py').read())", deadline=240).strip()[:4000])
finally:
    d.close()
