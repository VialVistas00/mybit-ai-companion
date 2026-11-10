# -*- coding: utf-8 -*-
"""
板子自己发起认证，并精确打印每个阶段的响应
关键：认证必须用板子自己的 IP 和 MAC
"""
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import network, time, json
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
print('板子 IP:', ip)

ts = str(int(time.time() * 1000))

# 1. 本机在 Portal 侧的 IP
r = S.http_get(PORTAL, 80, '/cgi-bin/rad_user_info?callback=cb&_=' + ts)
j = S._json_of(r)
print('[1] rad_user_info:', (j or {}).get('error'), '| client_ip:', (j or {}).get('client_ip'))
real_ip = (j or {}).get('client_ip') or ip
print('    实际使用的 IP:', real_ip)

# 2. captcha
r = S.http_get(PORTAL, 80, '/v2/srun_portal_captcha_image_info?user_name=' + USER + '&ip=' + real_ip + '&_=' + ts)
print('[2] captcha:', r.split(chr(13)+chr(10)+chr(13)+chr(10))[-1][:100])

# 3. challenge
r = S.http_get(PORTAL, 80, '/cgi-bin/get_challenge?callback=cb&username=' + USER + '&ip=' + real_ip + '&_=' + ts)
j = S._json_of(r)
print('[3] challenge:', (j or {}).get('error'), '| token:', ((j or {}).get('challenge') or '')[:20])
if not j or 'challenge' not in j:
    print('    FAIL')
else:
    token = j['challenge']
    hmd5 = S.md5(PWD + token)
    info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, real_ip)
    info_enc = '{SRBX1}' + S.b64(S.xencode(info, token))
    chksum = S.sha1(token + USER + token + hmd5 + token + '1' + token + real_ip
                    + token + '200' + token + '1' + token + info_enc)
    print('[4] hmd5:', hmd5)
    print('    info 长度:', len(info_enc))
    print('    chksum:', chksum)
    url = ('/cgi-bin/srun_portal?callback=cb&action=login&username=' + USER
           + '&password=' + S.quote('{MD5}' + hmd5)
           + '&os=Windows+10&name=Windows&nas_ip=&double_stack=0'
           + '&chksum=' + chksum + '&info=' + S.quote(info_enc)
           + '&ac_id=1&ip=' + real_ip + '&n=200&type=1'
           + '&captchaVal=&ap_id=&ap_ip=&mac=&_=' + ts)
    r = S.http_get(PORTAL, 80, url, maxlen=2000)
    j2 = S._json_of(r)
    print('[5] 登录结果:')
    if j2:
        for k in ('error', 'error_msg', 'res', 'suc_msg', 'ploy_msg'):
            if k in j2:
                print('    %-10s = %s' % (k, j2[k]))
    else:
        print('    ', r[-300:])
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\blogin2.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "blogin2.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.4); d._drain(0.4)
    print(d.exec("import gc;gc.collect()\nexec(open('blogin2.py').read())", deadline=120).strip()[:2000])
finally:
    d.close()
