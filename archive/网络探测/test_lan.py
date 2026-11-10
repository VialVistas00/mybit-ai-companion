# -*- coding: utf-8 -*-
"""板子 -> 电脑 的 TCP 实测（绕过 ICMP 被拦）"""
import sys
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

PC_IP = "PC_IP"
d = MyBit("COM3")

CODE_SOCK = """import socket
s=socket.socket(); s.settimeout(6)
try:
    s.connect(('__PC__', 8080))
    print('TCP 连接成功')
    s.send(b'GET / HTTP/1.0\\r\\nHost: __PC__\\r\\n\\r\\n')
    buf=b''
    while len(buf) < 500:
        try:
            c=s.recv(200)
        except Exception:
            break
        if not c: break
        buf += c
    print('收到', len(buf), '字节')
    print(buf.decode('utf-8','replace')[:300])
except Exception as e:
    print('TCP 失败:', type(e).__name__, e)
s.close()""".replace("__PC__", PC_IP)

CODE_UQ = """try:
    import urequests
    r=urequests.get('http://__PC__:8080/')
    print('status', r.status_code)
    print('body', r.text[:150])
    r.close()
except Exception as e:
    print('urequests 失败:', type(e).__name__, e)""".replace("__PC__", PC_IP)

try:
    print("[1] 板子当前网络")
    print(d.exec(
        "import network\n"
        "w=network.WLAN(network.STA_IF)\n"
        "print('connected', w.isconnected())\n"
        "print('ifconfig', w.ifconfig())\n"
        "print('rssi', w.status('rssi'))", deadline=20).strip())

    print("\n[2] 板子 socket 直连电脑 8080")
    print(d.exec(CODE_SOCK, deadline=40).strip())

    print("\n[3] urequests 方式")
    print(d.exec(CODE_UQ, deadline=40).strip())
finally:
    d.close()
