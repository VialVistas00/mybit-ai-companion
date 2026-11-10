# -*- coding: utf-8 -*-
"""完整热点列表 + 依次尝试连接（YOUR_SSID 优先，其次开放网络 HZCU）"""
import sys
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

d = MyBit("COM3")
try:
    print("[1] 板子可见热点全量（23 个）")
    print(d.exec(
        "import network,time\n"
        "w=network.WLAN(network.STA_IF)\n"
        "w.active(1); time.sleep(1)\n"
        "r=w.scan()\n"
        "for i,s in enumerate(sorted(r, key=lambda x:-x[3]),1):\n"
        "    try: n=s[0].decode('utf-8')\n"
        "    except Exception: n=str(s[0])\n"
        "    print('%02d %-26s ch%-3d rssi%-4d %s' % (i,n,s[2],s[3],'open' if s[4]==0 else 'wpa'))",
        deadline=35).strip())

    print("\n[2] 尝试连接 YOUR_SSID")
    print(d.exec(
        "import network,time\n"
        "w=network.WLAN(network.STA_IF)\n"
        "w.active(1)\n"
        "try:\n"
        "    w.connect('YOUR_SSID','YOUR_WIFI_PASSWORD')\n"
        "    t=time.time()\n"
        "    while not w.isconnected() and time.time()-t<12: time.sleep(0.3)\n"
        "    print('YOUR_SSID connected=', w.isconnected(), w.ifconfig() if w.isconnected() else '')\n"
        "except Exception as e:\n"
        "    print('YOUR_SSID err', e)\n"
        "if not w.isconnected():\n"
        "    try:\n"
        "        w.connect('HZCU')\n"
        "        t=time.time()\n"
        "        while not w.isconnected() and time.time()-t<12: time.sleep(0.3)\n"
        "        print('HZCU connected=', w.isconnected(), w.ifconfig() if w.isconnected() else '')\n"
        "    except Exception as e:\n"
        "        print('HZCU err', e)",
        deadline=60).strip())
finally:
    d.close()
