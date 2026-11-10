# -*- coding: utf-8 -*-
"""把 SRun 客户端传到板子并执行 Portal 登录"""
import os, sys, time
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

DEV = r"D:\数据文件\上课\信电导论\开发板"
PORTAL = "PORTAL_IP"
PWD = "YOUR_PASSWORD"

LOGIN_CODE = """import network, time
import srun_client as S

w = network.WLAN(network.STA_IF)
if not w.isconnected():
    print('reconnect...')
    w.connect('YOUR_CAMPUS_SSID')
    t = time.time()
    while not w.isconnected() and time.time() - t < 20:
        time.sleep(0.4)
ip = w.ifconfig()[0]
print('板子 IP =', ip)

for user in ('YOUR_ACCOUNT', 'YOUR_STUDENT_ID'):
    print()
    print('===== 尝试用户名: ' + user + ' =====')
    try:
        r = S.login('__PORTAL__', user, '__PWD__', ip)
    except Exception as e:
        print('异常:', type(e).__name__, e)
        continue
    if r.get('stage') == 'challenge' and 'error' in r:
        print('challenge 失败:', r.get('error'), r.get('raw'))
        break
    res = r.get('result')
    print('challenge token:', str(r.get('token'))[:24] + '...')
    print('chksum:', r.get('chksum'))
    if res:
        print('error    :', res.get('error'))
        print('error_msg:', res.get('error_msg'))
        print('ecode    :', res.get('ecode'))
        print('suc_msg  :', res.get('suc_msg'))
        print('ploy_msg :', res.get('ploy_msg'))
        print('res      :', res.get('res'))
    else:
        print('原始响应:', r.get('raw'))
    if res and res.get('error') == 'ok':
        print('>>> 认证成功 <<<')
        break
    print('--- 等待 2 秒再试下一个 ---')
    time.sleep(2)
""".replace("__PORTAL__", PORTAL).replace("__PWD__", PWD)

d = MyBit("COM3")
try:
    print("[1] 上传 srun_client.py")
    n = d.put(os.path.join(DEV, "srun_client.py"), "srun_client.py")
    print("    ", n, "bytes")
    print("     板载:", d.ls())

    print("\n[2] 软重启清掉模块缓存，再确认可导入")
    d.ser.write(b"\x03\x03")
    time.sleep(0.25)
    d._drain(0.3)
    d.ser.write(b"\x04")
    time.sleep(1.6)
    d.ser.write(b"\x03\x03")
    time.sleep(0.3)
    d._drain(0.5)
    print("    ", d.exec("import srun_client;print('ok, md5(abc)=', srun_client.md5('abc'))",
                          deadline=25).strip())

    print("\n[3] 执行 Portal 登录")
    print(d.exec(LOGIN_CODE, deadline=180).strip())
finally:
    d.close()
