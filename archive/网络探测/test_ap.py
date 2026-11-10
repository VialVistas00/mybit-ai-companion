# -*- coding: utf-8 -*-
"""测试板子做 AP：电脑连上后即可与板子互通（绕过 5G 限制）"""
import os, sys, time
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

d = MyBit("COM3")
try:
    print("[1] 建立 AP: MYBIT_SNAKE / 密码 YOUR_WIFI_PASSWORD")
    print(d.exec(
        "from npython import wifi, oled\n"
        "import network, time\n"
        "try:\n"
        "    wifi.disable_AP()\n"
        "except Exception:\n"
        "    pass\n"
        "time.sleep(0.5)\n"
        "wifi.enable_AP('MYBIT_SNAKE', 'YOUR_WIFI_PASSWORD', 10)\n"
        "time.sleep(1.5)\n"
        "ap = network.WLAN(network.AP_IF)\n"
        "print('AP active:', ap.active())\n"
        "print('AP ifconfig:', ap.ifconfig())\n"
        "print('AP config ssid:', ap.config('essid'))\n"
        "oled.fill(0)\n"
        "oled.print(1,1,'AP MODE',1)\n"
        "oled.print(1,2,'SSID: MYBIT_SNAKE',1)\n"
        "oled.print(1,3,'PWD: YOUR_WIFI_PASSWORD',1)\n"
        "ip = ap.ifconfig()[0]\n"
        "oled.print(1,4,'IP: ' + str(ip),1)\n"
        "oled.print(1,5,'port 5000 ready',1)\n"
        "oled.show()\n"
        "print('板子 AP 已就绪, 访问地址 http://' + str(ip) + ':5000/')",
        deadline=45).strip())

    print("\n[2] 在板子上起一个应答服务，供电脑侧验证连通")
    print(d.exec(
        "import socket\n"
        "s = socket.socket()\n"
        "s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
        "s.bind(('0.0.0.0', 5000))\n"
        "s.listen(5)\n"
        "s.settimeout(30)\n"
        "print('listening on 0.0.0.0:5000')\n"
        "try:\n"
        "    c, a = s.accept()\n"
        "    print('连接来自', a)\n"
        "    c.send(b'HTTP/1.1 200 OK\\r\\nContent-Type: text/plain\\r\\n\\r\\nMYBIT OK\\r\\n')\n"
        "    c.close()\n"
        "    print('已应答')\n"
        "except Exception as e:\n"
        "    print('等待超时/异常:', e)\n"
        "s.close()", deadline=45).strip())
finally:
    d.close()
