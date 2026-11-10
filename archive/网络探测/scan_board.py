# -*- coding: utf-8 -*-
"""对比板子与电脑各自能看到什么 WiFi"""
import sys
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

d = MyBit("COM3")
try:
    print("[板子侧] 2.4G 全量扫描")
    print(d.exec(
        "import network\n"
        "w=network.WLAN(network.STA_IF)\n"
        "w.active(1)\n"
        "r=w.scan()\n"
        "print('共', len(r), '个')\n"
        "for s in sorted(r, key=lambda x:-x[3]):\n"
        "    try:\n"
        "        n=s[0].decode('utf-8','replace')\n"
        "    except Exception:\n"
        "        n=str(s[0])\n"
        "    print('%-28s ch%-3d rssi%-4d enc%d' % (n, s[2], s[3], s[4]))",
        deadline=30).strip())
finally:
    d.close()
