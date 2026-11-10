# -*- coding: utf-8 -*-
"""验证作业2：microdot 服务端库能否在这块板上真正跑起来"""
import os, time
from mybit import MyBit

ROOT = r"D:\数据文件\上课\信电导论"

d = MyBit("COM3")
try:
    print("[1] 上传 microdot.py")
    t0 = time.time()
    n = d.put(os.path.join(ROOT, r"作业2MICRODOT\microdot.py"), "microdot.py")
    print("    ", n, "bytes,", round(time.time() - t0, 1), "s")
    print("     板载:", d.ls())

    print("\n[2] 校验字节数")
    print("    ", d.exec(
        "import os;print('microdot.py', os.stat('microdot.py')[6], 'bytes')").strip())
    print("     本地:", os.path.getsize(os.path.join(ROOT, r"作业2MICRODOT\microdot.py")), "bytes")

    print("\n[3] 在板上真正 import 并建路由")
    print("    ", d.exec(
        "import gc;gc.collect()\n"
        "from microdot import Microdot, Response\n"
        "from temphtml import htmltemp1\n"
        "app=Microdot()\n"
        "@app.get('/ledon')\n"
        "def a(r): return '1'\n"
        "@app.get('/')\n"
        "def b(r): return htmltemp1[:60]\n"
        "print('Microdot 载入成功 (v=%s)' % getattr(__import__('microdot'),'__version__','?'))\n"
        "print('temphtml 可用, 首40字符:', repr(htmltemp1[:40]))\n"
        "print('剩余内存', gc.mem_free())", deadline=40).strip())

    print("\n[4] 尝试以 AP 模式起服务（不连外网，只验证端口能监听）")
    print("    ", d.exec(
        "from npython import wifi\n"
        "try:\n"
        "    wifi.enable_AP('MYBIT_TEST','YOUR_WIFI_PASSWORD',10)\n"
        "    print('AP 已建立')\n"
        "except Exception as e:\n"
        "    print('AP err', e)", deadline=25).strip())

    print("\n[5] 收尾：关 AP、删临时库、重启回时钟程序")
    print("    ", d.exec(
        "from npython import wifi\n"
        "import os\n"
        "try:\n"
        "    wifi.disable_AP()\n"
        "except Exception as e:\n"
        "    print(e)\n"
        "print('cleanup ok')", deadline=20).strip())
finally:
    d.close()
    print("\n[*] 端口已释放")
