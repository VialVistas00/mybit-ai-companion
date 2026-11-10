# -*- coding: utf-8 -*-
"""
让板子自己发起 SRun 认证
关键：认证请求必须由板子自己（用板子 IP）发出，服务器才认
"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

LOGIN_CODE = r'''import network, time
import srun_client as S

PORTAL = 'PORTAL_IP'
USER = 'YOUR_STUDENT_ID'
PWD = 'YOUR_PASSWORD'

w = network.WLAN(network.STA_IF)
if not w.isconnected():
    w.active(0); time.sleep(0.8); w.active(1); time.sleep(1.5)
    w.connect('YOUR_CAMPUS_SSID')
    t = time.time()
    while not w.isconnected() and time.time() - t < 20:
        time.sleep(0.4)
ip = w.ifconfig()[0]
mac = ':'.join(['%02x' % b for b in w.config('mac')])
print('板子 IP =', ip)
print('板子 MAC =', mac)
print()

def attempt(user, pwd, label):
    ts = str(int(time.time() * 1000))
    r = S.http_get(PORTAL, 80, '/cgi-bin/get_challenge?callback=cb&username=' + user + '&ip=' + ip + '&_=' + ts)
    j = S._json_of(r)
    if not j or 'challenge' not in j:
        print('  %-14s challenge失败' % label)
        return None
    token = j['challenge']
    hmd5 = S.md5(pwd + token)
    info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (user, pwd, ip)
    info_enc = '{SRBX1}' + S.b64(S.xencode(info, token))
    chksum = S.sha1(token + user + token + hmd5 + token + '1' + token + ip + token + '200' + token + '1' + token + info_enc)
    url = ('/cgi-bin/srun_portal?callback=cb&action=login&username=' + user
           + '&password=' + S.quote('{MD5}' + hmd5) + '&ac_id=1&ip=' + ip
           + '&chksum=' + chksum + '&info=' + S.quote(info_enc)
           + '&n=200&type=1&os=Windows&name=Windows&double_stack=0&_=' + ts)
    r2 = S.http_get(PORTAL, 80, url)
    j2 = S._json_of(r2)
    if not j2:
        print('  %-14s 空响应' % label)
        return None
    print('  %-14s %s / %s' % (label, j2.get('error'), j2.get('error_msg') or ''))
    return j2

print('=== 板子自己认证 ===')
attempt(USER, PWD, USER)
time.sleep(1)
attempt(USER + '@mac', PWD, USER + '@mac')

print()
print('=== 认证后测试外网 ===')
s = S.socket.socket() if hasattr(S, 'socket') else None
import socket
try:
    a = socket.getaddrinfo('connect.rom.miui.com', 80)[0][4]
    sk = socket.socket(); sk.settimeout(6)
    sk.connect(a)
    sk.send(b'GET /generate_204 HTTP/1.0\r\nHost: connect.rom.miui.com\r\n\r\n')
    d = sk.recv(200)
    sk.close()
    print(' ', d.decode('utf-8','replace').split('\r\n')[0])
except Exception as e:
    print('  外网测试失败:', type(e).__name__, e)
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\board_login.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(LOGIN_CODE)
    d.put(tmp, "board_login.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.4); d._drain(0.4)
    print(d.exec("import gc;gc.collect()\nexec(open('board_login.py').read())", deadline=120).strip()[:1500])
finally:
    d.close()
