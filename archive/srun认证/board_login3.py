# -*- coding: utf-8 -*-
"""
在板子上做「完整浏览器流程」：
  1. GET 认证页（拿 cookie）
  2. rad_user_info
  3. captcha
  4. challenge（带 cookie + referer）
  5. 登录（带 cookie + referer）
用带 cookie 的 http_get 实现
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
print('板子 IP:', ip)

COOKIES = {}

def req(path, extra_headers='', maxlen=3000, timeout=12):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((PORTAL, 80))
        h = 'GET ' + path + ' HTTP/1.1\r\nHost: ' + PORTAL + '\r\n'
        h += 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n'
        h += 'Accept: */*\r\n'
        h += 'Referer: http://' + PORTAL + '/srun_portal_pc?ac_id=1&theme=pro\r\n'
        if COOKIES:
            h += 'Cookie: ' + '; '.join([k + '=' + v for k, v in COOKIES.items()]) + '\r\n'
        h += extra_headers + '\r\n'
        s.send(h.encode())
        buf = b''
        while len(buf) < maxlen:
            try:
                c = s.recv(500)
            except Exception:
                break
            if not c:
                break
            buf += c
        s.close()
        txt = buf.decode('utf-8', 'replace')
        # 解析 Set-Cookie
        for line in txt.split('\r\n'):
            if line.lower().startswith('set-cookie:'):
                kv = line.split(':', 1)[1].strip().split(';')[0]
                if '=' in kv:
                    k, v = kv.split('=', 1)
                    COOKIES[k.strip()] = v.strip()
        return txt
    except Exception as e:
        try:
            s.close()
        except Exception:
            pass
        return 'ERR ' + type(e).__name__ + ' ' + str(e)

def body(t):
    return t.split('\r\n\r\n', 1)[-1] if '\r\n\r\n' in t else t

print()
print('=== 1. 打开认证页建立会话 ===')
r = req('/srun_portal_pc?ac_id=1&theme=pro', maxlen=8000)
print('  状态:', r.split('\r\n')[0])
print('  cookie:', list(COOKIES.keys()))

ts = str(int(time.time() * 1000))

print()
print('=== 2. rad_user_info ===')
r = req('/cgi-bin/rad_user_info?callback=cb&ip=' + ip + '&_=' + ts)
j = S._json_of(r)
print('  ', (j or {}).get('error'), '| ip:', (j or {}).get('client_ip'))

print()
print('=== 3. captcha ===')
r = req('/v2/srun_portal_captcha_image_info?user_name=' + USER + '&ip=' + ip + '&_=' + ts)
print('  ', body(r)[:100])

print()
print('=== 4. challenge（带 cookie）===')
r = req('/cgi-bin/get_challenge?callback=cb&username=' + USER + '&ip=' + ip + '&_=' + ts)
j = S._json_of(r)
print('  ', (j or {}).get('error'), '| token:', ((j or {}).get('challenge') or '')[:20])

if j and 'challenge' in j:
    token = j['challenge']
    hmd5 = S.md5(PWD + token)
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
    print()
    print('=== 5. 登录（带 cookie）===')
    r = req(url, 'X-Requested-With: XMLHttpRequest\r\n', maxlen=2000)
    j2 = S._json_of(r)
    if j2:
        print('  error:', j2.get('error'), '| msg:', j2.get('error_msg'))
    else:
        print('  ', body(r)[:300])
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\blogin3.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "blogin3.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.4); d._drain(0.4)
    print(d.exec("import gc;gc.collect()\nexec(open('blogin3.py').read())", deadline=150).strip()[:2500])
finally:
    d.close()
