# -*- coding: utf-8 -*-
"""板子连接 YOUR_CAMPUS_SSID（开放 SSID），探测网络与 Portal 认证方式"""
import sys
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

d = MyBit("COM3")
try:
    print("[1] 连接 YOUR_CAMPUS_SSID（开放网络，先不带密码）")
    print(d.exec(
        "import network, time\n"
        "w=network.WLAN(network.STA_IF)\n"
        "w.active(0); time.sleep(0.8); w.active(1); time.sleep(1.5)\n"
        "w.connect('YOUR_CAMPUS_SSID')\n"
        "t=time.time()\n"
        "while not w.isconnected() and time.time()-t<15:\n"
        "    time.sleep(0.3)\n"
        "print('connected =', w.isconnected())\n"
        "print('status    =', w.status())\n"
        "if w.isconnected():\n"
        "    print('ifconfig  =', w.ifconfig())\n"
        "    print('rssi      =', w.status('rssi'))",
        deadline=45).strip())

    print("\n[2] 连通性探测：网关 / DNS / 外网")
    print(d.exec(
        "import socket, time\n"
        "w=network.WLAN(network.STA_IF)\n"
        "cfg = w.ifconfig()\n"
        "gw = cfg[2]\n"
        "print('网关', gw)\n"
        "tests = [('网关', gw, 80), ('网关ICMP代理', gw, 53), ('114DNS', '114.114.114.114', 53)]\n"
        "for name, host, port in tests:\n"
        "    s=socket.socket(); s.settimeout(4)\n"
        "    try:\n"
        "        s.connect((host, port)); print('  %-12s %s:%d 通' % (name, host, port))\n"
        "    except Exception as e:\n"
        "        print('  %-12s %s:%d 不通 (%s)' % (name, host, port, e))\n"
        "    s.close()\n"
        "try:\n"
        "    print('DNS 解析 www.baidu.com ->', socket.getaddrinfo('www.baidu.com', 80)[0][4])\n"
        "except Exception as e:\n"
        "    print('DNS 解析失败:', e)",
        deadline=45).strip())

    print("\n[3] 抓 Portal：访问一个 http 站点，看是否被劫持重定向")
    print(d.exec(
        "import socket\n"
        "w=network.WLAN(network.STA_IF)\n"
        "try:\n"
        "    addr = socket.getaddrinfo('connect.rom.miui.com', 80)[0][4]\n"
        "except Exception as e:\n"
        "    print('域名解析失败', e); addr=None\n"
        "if addr:\n"
        "    s=socket.socket(); s.settimeout(6)\n"
        "    try:\n"
        "        s.connect(addr)\n"
        "        s.send(b'GET /generate_204 HTTP/1.1\\r\\nHost: connect.rom.miui.com\\r\\nUser-Agent: test\\r\\nConnection: close\\r\\n\\r\\n')\n"
        "        buf=b''\n"
        "        while len(buf) < 900:\n"
        "            try:\n"
        "                c=s.recv(256)\n"
        "            except Exception:\n"
        "                break\n"
        "            if not c: break\n"
        "            buf += c\n"
        "        print('响应头:')\n"
        "        print(buf.decode('utf-8','replace')[:800])\n"
        "    except Exception as e:\n"
        "        print('请求失败', e)\n"
        "    s.close()", deadline=60).strip())
finally:
    d.close()
