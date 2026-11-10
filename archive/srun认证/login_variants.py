# -*- coding: utf-8 -*-
"""在板子上遍历 username 变体 + hmd5 两种算法，找出能通过 SRun 校验的组合"""
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
print('板子 IP =', ip)
print()

def attempt(user, pwd_mode):
    ts = str(int(time.time() * 1000))
    r = S.http_get(PORTAL, 80, '/cgi-bin/get_challenge?callback=cb&username=' + S.quote(user) + '&ip=' + ip + '&_=' + ts)
    j = S._json_of(r)
    if not j or 'challenge' not in j:
        return 'challenge_fail'
    token = j['challenge']
    if pwd_mode == 'pwd_first':
        hmd5 = S.md5(PWD + token)
    else:
        hmd5 = S.md5(token + PWD)
    info_json = '{"username":"%s","password":"%s","ip":"%s","acid":"%s","enc_ver":"srun_bx1"}' % (user, PWD, ip, AC)
    info_enc = '{SRBX1}' + S.b64(S.xencode(info_json, token))
    chksum = S.sha1(token + user + token + hmd5 + token + AC + token + ip + token + '200' + token + '1' + token + info_enc)
    url = ('/cgi-bin/srun_portal?callback=cb&action=login&username=' + S.quote(user)
           + '&password=' + S.quote('{MD5}' + hmd5) + '&ac_id=' + AC + '&ip=' + ip
           + '&chksum=' + chksum + '&info=' + S.quote(info_enc)
           + '&n=200&type=1&os=Windows&name=Windows&double_stack=0&_=' + ts)
    r2 = S.http_get(PORTAL, 80, url)
    j2 = S._json_of(r2)
    if not j2:
        return 'empty'
    return str(j2.get('error')) + ' / ' + str(j2.get('error_msg'))

for user in ('YOUR_ACCOUNT', 'YOUR_ACCOUNT@mac', 'YOUR_STUDENT_ID', 'YOUR_STUDENT_ID@mac'):
    for mode in ('pwd_first', 'token_first'):
        try:
            res = attempt(user, mode)
        except Exception as e:
            res = 'EXC ' + type(e).__name__ + ' ' + str(e)
        print('%-14s %-12s -> %s' % (user, mode, res))
        time.sleep(1.5)
'''

d = MyBit("COM3")
try:
    print("[upload srun_client]", d.put(r"D:\数据文件\上课\信电导论\开发板\srun_client.py", "srun_client.py"), "bytes")
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\v.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    print("[upload variants]", d.put(tmp, "login_variants.py"), "bytes")

    d.ser.write(b"\x03\x03"); time.sleep(0.25); d._drain(0.3)
    d.ser.write(b"\x04"); time.sleep(1.6)
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.5)

    print(d.exec("exec(open('login_variants.py').read())", deadline=240).strip()[:4000])
finally:
    d.close()
