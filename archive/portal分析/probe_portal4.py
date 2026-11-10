# -*- coding: utf-8 -*-
"""验证 JSONP 通道 + 给 login 补 Referer/Cookie"""
import os, sys, time
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import network, time, socket
import srun_client as S

PORTAL = 'PORTAL_IP'
USER = 'YOUR_ACCOUNT'
PWD = 'YOUR_PASSWORD'

w = network.WLAN(network.STA_IF)
if not w.isconnected():
    w.connect('YOUR_CAMPUS_SSID'); t=time.time()
    while not w.isconnected() and time.time()-t<20: time.sleep(0.4)
ip = w.ifconfig()[0]
ts = str(int(time.time()*1000))
print('ip =', ip)
print()

print('=== 1) rad_user_info (验证 JSONP 通道) ===')
r = S.http_get(PORTAL, 80, '/cgi-bin/rad_user_info?callback=cb&_=' + ts)
print(r[:400])
print()

print('=== 2) get_challenge ===')
r2 = S.http_get(PORTAL, 80, '/cgi-bin/get_challenge?callback=cb&username=' + USER + '&ip=' + ip + '&_=' + ts)
print(r2[:300])
j = S._json_of(r2)
print()

if j and 'challenge' in j:
    token = j['challenge']
    hmd5 = S.md5(PWD + token)
    info_json = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, ip)
    info_enc = '{SRBX1}' + S.b64(S.xencode(info_json, token))
    chksum = S.md5(token + USER + token + hmd5 + token + '1' + token + ip + token + '200' + token + '1' + token + info_enc)

    def post_raw(path, body, extra_headers=''):
        s = socket.socket(); s.settimeout(10)
        s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
        req = ('POST ' + path + ' HTTP/1.1\r\nHost: ' + PORTAL
               + '\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: ' + str(len(body))
               + '\r\nConnection: close\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n'
               + 'Referer: http://' + PORTAL + '/srun_portal_pc?ac_id=1&theme=pro\r\n'
               + extra_headers + '\r\n' + body)
        s.send(req.encode())
        buf = b''
        while True:
            try: c = s.recv(400)
            except Exception: break
            if not c: break
            buf += c
        s.close()
        return buf.decode('utf-8', 'replace')

    def get_raw(path, extra_headers=''):
        s = socket.socket(); s.settimeout(10)
        s.connect(socket.getaddrinfo(PORTAL, 80)[0][4])
        req = ('GET ' + path + ' HTTP/1.1\r\nHost: ' + PORTAL
               + '\r\nConnection: close\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\n'
               + 'Referer: http://' + PORTAL + '/srun_portal_pc?ac_id=1&theme=pro\r\n'
               + extra_headers + '\r\n')
        s.send(req.encode())
        buf = b''
        while True:
            try: c = s.recv(400)
            except Exception: break
            if not c: break
            buf += c
        s.close()
        return buf.decode('utf-8', 'replace')

    print('=== 3) GET + Referer ===')
    u = ('/cgi-bin/srun_portal?callback=cb&action=login&username=' + USER
         + '&password=' + '{MD5}' + hmd5 + '&ac_id=1&ip=' + ip
         + '&chksum=' + chksum + '&info=' + S.quote(info_enc)
         + '&n=200&type=1&os=Windows&name=Windows&double_stack=0&_=' + ts)
    out = get_raw(u)
    parts = out.split('\r\n\r\n')
    print('  体:', (parts[1][:300] if len(parts) > 1 else '(无)'))
    print()

    print('=== 4) POST + Referer ===')
    form = ('action=login&username=' + USER + '&password=' + S.quote('{MD5}' + hmd5)
            + '&ac_id=1&ip=' + ip + '&chksum=' + chksum + '&info=' + S.quote(info_enc)
            + '&n=200&type=1&os=Windows&name=Windows&double_stack=0')
    out2 = post_raw('/cgi-bin/srun_portal', form)
    parts2 = out2.split('\r\n\r\n')
    print('  体:', (parts2[1][:300] if len(parts2) > 1 else '(无)'))
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\p4.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    print("[upload]", d.put(tmp, "portal_p4.py"), "bytes")

    d.ser.write(b"\x03\x03"); time.sleep(0.25); d._drain(0.3)
    d.ser.write(b"\x04"); time.sleep(1.6)
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.5)

    print(d.exec("exec(open('portal_p4.py').read())", deadline=200).strip()[:6000])
finally:
    d.close()
