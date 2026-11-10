# -*- coding: utf-8 -*-
"""
用 YOUR_ACCOUNT / YOUR_PASSWORD 在板子上认证
先上传最新 srun_client（含 HMAC）
"""
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import network, time, socket
import srun_client as S

PORTAL = 'PORTAL_IP'
USER = 'YOUR_ACCOUNT'
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
print('板子 IP :', ip)
print('板子 MAC:', mac)
print('账号    :', USER)
print()

ts = str(int(time.time() * 1000))

# 1. 本机状态
r = S.http_get(PORTAL, 80, '/cgi-bin/rad_user_info?callback=cb&ip=' + ip + '&_=' + ts)
j = S._json_of(r)
print('[1] 当前状态 error =', (j or {}).get('error'))

# 2. challenge
r = S.http_get(PORTAL, 80, '/cgi-bin/get_challenge?callback=cb&username=' + USER + '&ip=' + ip + '&_=' + ts)
j = S._json_of(r)
print('[2] challenge error =', (j or {}).get('error'))

if not (j and 'challenge' in j):
    print('    FAIL:', r[:200])
else:
    token = j['challenge']
    print('    token =', token[:24])

    hmd5 = S.hmac_md5_hex(token, PWD)
    info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, ip)
    info_enc = '{SRBX1}' + S.b64(S.xencode(info, token))
    chksum = S.sha1(token + USER + token + hmd5 + token + '1' + token + ip
                    + token + '200' + token + '1' + token + info_enc)
    print('[3] hmd5   =', hmd5)
    print('    chksum =', chksum)
    print()

    url = ('/cgi-bin/srun_portal?callback=cb&action=login&username=' + USER
           + '&password=' + S.quote('{MD5}' + hmd5)
           + '&os=Windows+10&name=Windows&nas_ip=&double_stack=0'
           + '&chksum=' + chksum + '&info=' + S.quote(info_enc)
           + '&ac_id=1&ip=' + ip + '&n=200&type=1'
           + '&captchaVal=&ap_id=&ap_ip=&mac=&_=' + ts)
    r = S.http_get(PORTAL, 80, url, maxlen=2500)
    j2 = S._json_of(r)

    print('[4] === 认证结果 ===')
    if j2:
        for k in ('error', 'error_msg', 'res', 'suc_msg', 'access_token'):
            if k in j2:
                v = str(j2[k])
                print('    %-14s = %s' % (k, v[:70]))
    else:
        print('    ', r[-300:])

print()
print('[5] 外网测试')
try:
    s = socket.socket(); s.settimeout(6)
    s.connect(socket.getaddrinfo('connect.rom.miui.com', 80)[0][4])
    s.send(b'GET /generate_204 HTTP/1.0\r\nHost: connect.rom.miui.com\r\n\r\n')
    d = s.recv(200)
    s.close()
    print('    ', d.decode('utf-8', 'replace').split(chr(13))[0])
except Exception as e:
    print('    ', type(e).__name__, e)
'''

d = MyBit("COM3")
try:
    print("[0] 更新 srun_client")
    n = d.put(r"D:\数据文件\上课\信电导论\开发板\srun_client.py", "srun_client.py")
    print("    ", n, "bytes")

    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\blogin7.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "blogin7.py")

    d.ser.write(b"\x03\x03"); time.sleep(0.4); d._drain(0.4)
    d.ser.write(b"\x04"); time.sleep(1.5)
    d.ser.write(b"\x03\x03"); time.sleep(0.4); d._drain(0.4)
    print(d.exec("import gc;gc.collect()\nexec(open('blogin7.py').read())", deadline=180).strip()[:2500])
finally:
    d.close()
