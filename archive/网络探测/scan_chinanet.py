# -*- coding: utf-8 -*-
"""扫描板子能看到的 ChinaNet / 2.4G 热点"""
import sys
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

d = MyBit("COM3")
try:
    print(d.exec(
        "import network,time\n"
        "w=network.WLAN(network.STA_IF)\n"
        "w.active(0); time.sleep(0.8); w.active(1); time.sleep(2)\n"
        "r=w.scan()\n"
        "print('可见热点总数', len(r))\n"
        "print('--- 含 ChinaNet / Q4Nz 的 ---')\n"
        "hit=0\n"
        "for s in r:\n"
        "    try: n=s[0].decode('utf-8','replace')\n"
        "    except Exception: n=str(s[0])\n"
        "    if 'ChinaNet' in n or 'Q4Nz' in n or 'Q4N' in n.upper():\n"
        "        print('  %-24s ch%-3d rssi%-4d enc%d' % (n, s[2], s[3], s[4]))\n"
        "        hit+=1\n"
        "print('命中', hit, '个')\n"
        "print('--- 全部列表（按信号强度）---')\n"
        "for s in sorted(r, key=lambda x:-x[3])[:20]:\n"
        "    try: n=s[0].decode('utf-8','replace')\n"
        "    except Exception: n=str(s[0])\n"
        "    print('  %-26s ch%-3d rssi%-4d %s' % (n, s[2], s[3], 'open' if s[4]==0 else 'wpa'))",
        deadline=45).strip())
finally:
    d.close()
