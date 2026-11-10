# -*- coding: utf-8 -*-
"""
决定性实验：完全复刻成功请求的 os/name 参数，在板子上认证
对照：浏览器成功时 os=iPhone name=Smartphones/PDAs/Tablets
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

def login(os_name, name, tag):
    ts = str(int(time.time() * 1000))
    r = S.http_get(PORTAL, 80, '/cgi-bin/get_challenge?callback=cb&username=' + USER + '&ip=' + ip + '&_=' + ts)
    j = S._json_of(r)
    if not j or 'challenge' not in j:
        print('[%s] challenge 失败' % tag)
        return
    token = j['challenge']
    hmd5 = S.md5(PWD + token)
    info = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, ip)
    info_enc = '{SRBX1}' + S.b64(S.xencode(info, token))
    chksum = S.sha1(token + USER + token + hmd5 + token + '1' + token + ip
                    + token + '200' + token + '1' + token + info_enc)
    url = ('/cgi-bin/srun_portal?callback=cb&action=login&username=' + USER
           + '&password=' + S.quote('{MD5}' + hmd5)
           + '&os=' + S.quote(os_name)
           + '&name=' + S.quote(name)
           + '&nas_ip=&double_stack=0'
           + '&chksum=' + chksum + '&info=' + S.quote(info_enc)
           + '&ac_id=1&ip=' + ip + '&n=200&type=1'
           + '&captchaVal=&ap_id=&ap_ip=&mac=&_=' + ts)
    r = S.http_get(PORTAL, 80, url, maxlen=2000)
    j2 = S._json_of(r)
    if j2:
        print('[%s] error=%s res=%s msg=%s' % (tag, j2.get('error'), j2.get('res'), j2.get('error_msg')))
    else:
        print('[%s] 空 ' % tag, r[-150:])

print()
print('=== 对照测试 ===')
login('Windows 10', 'Windows', 'PC风格')
time.sleep(1.5)
login('iPhone', 'Smartphones/PDAs/Tablets', '手机风格')
time.sleep(1.5)
login('Android', 'Smartphones/PDAs/Tablets', '安卓风格')

print()
print('=== 登录后查外网 ===')
try:
    s = socket.socket(); s.settimeout(6)
    s.connect(socket.getaddrinfo('connect.rom.miui.com', 80)[0][4])
    s.send(b'GET /generate_204 HTTP/1.0\r\nHost: connect.rom.miui.com\r\n\r\n')
    d = s.recv(200)
    s.close()
    print(' ', d.decode('utf-8', 'replace').split('\r\n')[0])
except Exception as e:
    print('  外网失败:', type(e).__name__, e)
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\blogin4.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "blogin4.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.4); d._drain(0.4)
    print(d.exec("import gc;gc.collect()\nexec(open('blogin4.py').read())", deadline=180).strip()[:2000])
finally:
    d.close()
