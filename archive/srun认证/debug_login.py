# -*- coding: utf-8 -*-
"""SRun 登录调试：对比不同请求写法，找出能返回 JSON 的那种"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

DBG = r'''import network, time
import srun_client as S

PORTAL = 'PORTAL_IP'
USER = 'YOUR_ACCOUNT'
PWD = 'YOUR_PASSWORD'
AC = '1'
N = '200'
TY = '1'

w = network.WLAN(network.STA_IF)
if not w.isconnected():
    w.connect('YOUR_CAMPUS_SSID'); t = time.time()
    while not w.isconnected() and time.time() - t < 20: time.sleep(0.4)
ip = w.ifconfig()[0]
print('ip =', ip)

ts = str(int(time.time() * 1000))
r = S.http_get(PORTAL, 80, '/cgi-bin/get_challenge?callback=cb&username=' + USER + '&ip=' + ip + '&_=' + ts)
j = S._json_of(r)
if not j:
    print('challenge 失败:', r[:300])
else:
    token = j['challenge']
    print('token =', token[:20] + '...')
    hmd5 = S.md5(PWD + token)
    info_json = '{"username":"%s","password":"%s","ip":"%s","acid":"%s","enc_ver":"srun_bx1"}' % (USER, PWD, ip, AC)
    info_enc = '{SRBX1}' + S.b64(S.xencode(info_json, token))
    chksum = S.md5(token + USER + token + hmd5 + token + AC + token + ip + token + N + token + TY + token + info_enc)
    print('hmd5   =', hmd5)
    print('chksum =', chksum)

    def show(title, resp):
        parts = resp.split('\r\n\r\n')
        body = parts[1] if len(parts) > 1 else ''
        print('  ' + title + ': 总长' + str(len(resp)) + ' 体长' + str(len(body)))
        if body:
            print('    ' + body[:220])

    print()
    print('=== 1) GET, info 原样 ===')
    u1 = ('/cgi-bin/srun_portal?callback=cb&action=login&username=' + USER
          + '&password=' + '{MD5}' + hmd5 + '&ac_id=' + AC + '&ip=' + ip
          + '&chksum=' + chksum + '&info=' + info_enc
          + '&n=' + N + '&type=' + TY + '&os=Windows&name=Windows&double_stack=0&_=' + ts)
    show('GET-plain', S.http_get(PORTAL, 80, u1))

    print()
    print('=== 2) GET, info URL 编码 ===')
    u2 = ('/cgi-bin/srun_portal?callback=cb&action=login&username=' + USER
          + '&password=' + S.quote('{MD5}' + hmd5) + '&ac_id=' + AC + '&ip=' + ip
          + '&chksum=' + chksum + '&info=' + S.quote(info_enc)
          + '&n=' + N + '&type=' + TY + '&os=Windows&name=Windows&double_stack=0&_=' + ts)
    show('GET-encoded', S.http_get(PORTAL, 80, u2))

    print()
    print('=== 3) GET, 不带 callback ===')
    u3 = u2.replace('callback=cb&', '')
    show('GET-nocb', S.http_get(PORTAL, 80, u3))

    print()
    print('=== 4) POST form ===')
    import socket
    form = ('action=login&username=' + USER
            + '&password=' + S.quote('{MD5}' + hmd5) + '&ac_id=' + AC + '&ip=' + ip
            + '&chksum=' + chksum + '&info=' + S.quote(info_enc)
            + '&n=200&type=1&os=Windows&name=Windows&double_stack=0')
    s = socket.socket(); s.settimeout(10)
    try:
        s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
        req = ('POST /cgi-bin/srun_portal HTTP/1.1\r\nHost: ' + PORTAL
               + '\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: '
               + str(len(form)) + '\r\nConnection: close\r\nUser-Agent: Mozilla/5.0\r\n\r\n' + form)
        s.send(req.encode())
        buf = b''
        while True:
            try: c = s.recv(400)
            except Exception: break
            if not c: break
            buf += c
        show('POST', buf.decode('utf-8', 'replace'))
    except Exception as e:
        print('  POST 异常', e)
    s.close()
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\dbg.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(DBG)
    n = d.put(tmp, "login_dbg.py")
    print("[upload]", n, "bytes")

    d.ser.write(b"\x03\x03"); time.sleep(0.25); d._drain(0.3)
    d.ser.write(b"\x04"); time.sleep(1.6)
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.5)

    print(d.exec("exec(open('login_dbg.py').read())", deadline=200).strip())
finally:
    d.close()
