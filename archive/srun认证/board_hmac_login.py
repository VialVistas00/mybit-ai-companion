# -*- coding: utf-8 -*-
"""在板子上用修正后的 HMAC-MD5 做认证"""
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import network, time, socket
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

# 1. challenge
r = S.http_get(PORTAL, 80, '/cgi-bin/get_challenge?callback=cb&username=' + USER + '&ip=' + ip + '&_=' + ts)
j = S._json_of(r)
if not j or 'challenge' not in j:
    print('challenge 失败')
else:
    token = j['challenge']
    print('token:', token[:24])

    # 2. 用 HMAC-MD5（修正后）
    hmd5 = S.hmac_md5_hex(token, PWD)
    print('hmd5(HMAC):', hmd5)

    info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, ip)
    info_enc = '{SRBX1}' + S.b64(S.xencode(info, token))
    chksum = S.sha1(token + USER + token + hmd5 + token + '1' + token + ip
                    + token + '200' + token + '1' + token + info_enc)

    url = ('/cgi-bin/srun_portal?callback=cb&action=login&username=' + USER
           + '&password=' + S.quote('{MD5}' + hmd5)
           + '&os=Windows+10&name=Windows&nas_ip=&double_stack=0'
           + '&chksum=' + chksum + '&info=' + S.quote(info_enc)
           + '&ac_id=1&ip=' + ip + '&n=200&type=1'
           + '&captchaVal=&ap_id=&ap_ip=&mac=&_=' + ts)
    r = S.http_get(PORTAL, 80, url, maxlen=2000)
    j2 = S._json_of(r)
    print()
    print('=== 登录结果 ===')
    if j2:
        for k in ('error', 'error_msg', 'res', 'suc_msg', 'access_token'):
            if k in j2:
                v = str(j2[k])
                print('  %-14s = %s' % (k, v[:70]))
    else:
        print('  ', r[-300:])

print()
print('=== 外网测试 ===')
try:
    s = socket.socket(); s.settimeout(6)
    s.connect(socket.getaddrinfo('connect.rom.miui.com', 80)[0][4])
    s.send(b'GET /generate_204 HTTP/1.0\r\nHost: connect.rom.miui.com\r\n\r\n')
    d = s.recv(200)
    s.close()
    txt = d.decode('utf-8', 'replace')
    print('  ', txt.split('\r\n')[0])
except Exception as e:
    print('  ', type(e).__name__, e)
'''

d = MyBit("COM3")
try:
    # 先上传修正后的 srun_client
    print("[1] 上传修正版 srun_client.py")
    n = d.put(r"D:\数据文件\上课\信电导论\开发板\srun_client.py", "srun_client.py")
    print("    ", n, "bytes")

    print("[2] 执行板子认证")
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\blogin5.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "blogin5.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.4); d._drain(0.4)
    # 需要软重启让新模块生效
    d.ser.write(b"\x04"); time.sleep(1.5)
    d.ser.write(b"\x03\x03"); time.sleep(0.4); d._drain(0.4)
    print(d.exec("import gc;gc.collect()\nexec(open('blogin5.py').read())", deadline=150).strip()[:2000])
finally:
    d.close()
