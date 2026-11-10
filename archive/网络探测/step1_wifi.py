# -*- coding: utf-8 -*-
"""让板子连接 YOUR_SSID 热点，取 IP / 网关 / 信号，并做 NTP 校时"""
import sys, time
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

SSID = "YOUR_SSID"
PWD = "YOUR_WIFI_PASSWORD"

d = MyBit("COM3")
try:
    print("[1] 扫描确认热点在范围内")
    print("    ", d.exec(
        "import network\n"
        "w=network.WLAN(network.STA_IF)\n"
        "w.active(1)\n"
        "r=[s for s in w.scan() if b'YOUR_SSID' in s[0]]\n"
        "print([(s[0].decode(),'ch%d'%s[2],s[3],'enc%d'%s[4]) for s in r])",
        deadline=25).strip())

    print("\n[2] 连接 %s" % SSID)
    out = d.exec(
        "import network,time\n"
        "w=network.WLAN(network.STA_IF)\n"
        "w.active(1)\n"
        "w.connect('%s','%s')\n"
        "t=time.time()\n"
        "while not w.isconnected() and time.time()-t<15:\n"
        "    time.sleep(0.3)\n"
        "print('connected', w.isconnected())\n"
        "print('ifconfig', w.ifconfig())\n"
        "print('status', w.status())\n"
        "print('rssi', w.status('rssi'))" % (SSID, PWD), deadline=45)
    print(out.strip())

    print("\n[3] NTP 校时（cn.ntp.org.cn / ntp.aliyun.com）")
    print("    ", d.exec(
        "from machine import RTC\n"
        "import ntptime, time\n"
        "rtc=RTC()\n"
        "ok=False\n"
        "for host in ('cn.ntp.org.cn','ntp.aliyun.com','ntp1.aliyun.com'):\n"
        "    try:\n"
        "        ntptime.host=host\n"
        "        ntptime.settime()\n"
        "        print('NTP ok via', host)\n"
        "        ok=True\n"
        "        break\n"
        "    except Exception as e:\n"
        "        print('fail', host, e)\n"
        "print('RTC now', rtc.datetime())", deadline=60).strip())
finally:
    d.close()
