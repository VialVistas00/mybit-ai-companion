# -*- coding: utf-8 -*-
"""延长等待后重复扫描，确认热点是否已广播"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import network, time
w = network.WLAN(network.STA_IF)
w.active(0)
time.sleep(0.5)
w.active(1)
time.sleep(2.0)

found = False
for attempt in range(4):
    r = w.scan()
    print('--- 第', attempt + 1, '次扫描, 共', len(r), '个 ---')
    for s in sorted(r, key=lambda x: -x[3])[:15]:
        try:
            name = s[0].decode('utf-8', 'replace')
        except Exception:
            name = str(s[0])
        mark = '  <<<' if 'MYBIT' in name else ''
        print('  %-26s ch%-3d rssi%-4d %s%s' % (name, s[2], s[3], 'open' if s[4] == 0 else 'wpa', mark))
        if 'MYBIT' in name:
            found = True
    if found:
        print('*** 已找到 MYBIT_HOTSPOT ***')
        break
    print('    (未找到，3秒后重试)')
    time.sleep(3)
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\scan2.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "scan2.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.25); d._drain(0.3)
    d.ser.write(b"\x04"); time.sleep(1.6)
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.5)
    print(d.exec("exec(open('scan2.py').read())", deadline=150).strip()[:3000])
finally:
    d.close()
