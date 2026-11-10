# -*- coding: utf-8 -*-
"""
真实链路测试：板子录音 -> 串口分块 -> 桥接收 -> whisper -> DeepSeek
桥必须是运行状态。本脚本不碰串口（桥独占），只观察桥日志。
做法：启动桥，桥带 --voice 参数时会让板子录一次音并发上来。
"""
import os
import subprocess
import sys

DEV = r"D:\数据文件\上课\信电导论\开发板"
LOG = os.path.join(DEV, "_bridge.log")

env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"

with open(LOG, "w", encoding="utf-8", errors="replace") as log:
    p = subprocess.Popen(
        [sys.executable, "-u", os.path.join(DEV, "serial_bridge.py"), "--voice"],
        stdout=log, stderr=subprocess.STDOUT, cwd=DEV, env=env)
    p.wait(timeout=180)

print("=" * 62)
print("桥日志")
print("=" * 62)
with open(LOG, "r", encoding="utf-8", errors="replace") as f:
    print(f.read())
