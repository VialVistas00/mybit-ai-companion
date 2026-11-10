# -*- coding: utf-8 -*-
"""
让板子自己完成认证，并把每一步的响应完整打印
关键：使用板子自己的 IP 和 MAC，不经过电脑
"""
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
mac_raw = w.config('mac')
mac = ':'.join(['%02x' % b for b in mac_raw])
mac_dash = '-'.join(['%02X' % b for b in mac_raw])
print('板子 IP :', ip)
print('板子 MAC:', mac)
print()

ts = str(int(time.time() * 1000))

# 1. 查本机在 Portal 眼中的身份
r = S.http_get(PORTAL, 80, '/cgi-bin/rad_user_info?callback=cb&ip=' + ip + '&_=' + ts)
j = S._json_of(r)
print('[1] rad_user_info error =', (j or {}).get('error'))
print('    client_ip =', (j or {}).get('client_ip'))

# 2. captcha
r = S.http_get(PORTAL, 80, '/v2/srun_portal_captcha_image_info?user_name=' + USER + '&ip=' + ip + '&_=' + ts)
print('[2] captcha:', r.split(chr(13)+chr(10)+chr(13)+chr(10))[-1][:80])

# 3. challenge
r = S.http_get(PORTAL, 80, '/cgi-bin/get_challenge?callback=cb&username=' + USER + '&ip=' + ip + '&_=' + ts)
j = S._json_of(r)
print('[3] challenge error =', (j or {}).get('error'))
if j and 'challenge' in j:
    token = j['challenge']
    print('    token =', token[:24], '...')

    hmd5 = S.hmac_md5_hex(token, PWD)
    info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, ip)
    info_enc = '{SRBX1}' + S.b64(S.xencode(info, token))
    chksum = S.sha1(token + USER + token + hmd5 + token + '1' + token + ip
                    + token + '200' + token + '1' + token + info_enc)
    print('[4] hmd5   =', hmd5)
    print('    info   =', info_enc[:50], '... (len', len(info_enc), ')')
    print('    chksum =', chksum)

    print()
    print('[5] 尝试认证（多组参数）')

    # 5a. 标准
    url = ('/cgi-bin/srun_portal?callback=cb&action=login&username=' + USER
           + '&password=' + S.quote('{MD5}' + hmd5)
           + '&os=Windows+10&name=Windows&nas_ip=&double_stack=0'
           + '&chksum=' + chksum + '&info=' + S.quote(info_enc)
           + '&ac_id=1&ip=' + ip + '&n=200&type=1'
           + '&captchaVal=&ap_id=&ap_ip=&mac=&_=' + ts)
    r = S.http_get(PORTAL, 80, url, maxlen=2000)
    j2 = S._json_of(r)
    if j2:
        print('    标准参数    -> error =', j2.get('error'), '| msg =', j2.get('error_msg'))
    else:
        print('    标准参数    -> 空:', r[-120:])

    time.sleep(1)

    # 5b. 带 mac
    url2 = ('/cgi-bin/srun_portal?callback=cb&action=login&username=' + USER
            + '&password=' + S.quote('{MD5}' + hmd5)
            + '&os=Windows+10&name=Windows&nas_ip=&double_stack=0'
            + '&chksum=' + chksum + '&info=' + S.quote(info_enc)
            + '&ac_id=1&ip=' + ip + '&n=200&type=1'
            + '&captchaVal=&ap_id=&ap_ip=&mac=' + S.quote(mac) + '&_=' + ts)
    r = S.http_get(PORTAL, 80, url2, maxlen=2000)
    j2 = S._json_of(r)
    if j2:
        print('    带mac       -> error =', j2.get('error'), '| msg =', j2.get('error_msg'))

    time.sleep(1)

    # 5c. 板子 MAC 作为 username（MAC 认证）
    ts2 = str(int(time.time() * 1000))
    r = S.http_get(PORTAL, 80, '/cgi-bin/get_challenge?callback=cb&username=' + S.quote(mac) + '&ip=' + ip + '&_=' + ts2)
    jm = S._json_of(r)
    if jm and 'challenge' in jm:
        tok_m = jm['challenge']
        info_m = '{"username":"%s","password":"","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (mac, ip)
        info_m_enc = '{SRBX1}' + S.b64(S.xencode(info_m, tok_m))
        hm = S.hmac_md5_hex(tok_m, '')
        ck = S.sha1(tok_m + mac + tok_m + hm + tok_m + '1' + tok_m + ip + tok_m + '200' + tok_m + '1' + tok_m + info_m_enc)
        u3 = ('/cgi-bin/srun_portal?callback=cb&action=login&username=' + S.quote(mac)
              + '&password=' + S.quote('{MD5}' + hm) + '&os=Windows+10&name=Windows'
              + '&nas_ip=&double_stack=0&chksum=' + ck + '&info=' + S.quote(info_m_enc)
              + '&ac_id=1&ip=' + ip + '&n=200&type=5&_=' + ts2)
        r = S.http_get(PORTAL, 80, u3, maxlen=2000)
        j3 = S._json_of(r)
        if j3:
            print('    MAC作为账号 -> error =', j3.get('error'), '| msg =', j3.get('error_msg'))
        else:
            print('    MAC作为账号 -> 空')

print()
print('[6] 认证后互联网测试')
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
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\blogin6.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "blogin6.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.4); d._drain(0.4)
    print(d.exec("import gc;gc.collect()\nexec(open('blogin6.py').read())", deadline=180).strip()[:2500])
finally:
    d.close()
