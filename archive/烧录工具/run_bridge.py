# -*- coding: utf-8 -*-
"""完整端到端自测：桥 + 板子 + DeepSeek，一个进程操作串口"""
import os
import subprocess
import sys

DEV = r"D:\数据文件\上课\信电导论\开发板"
LOG = os.path.join(DEV, "_bridge.log")

env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"

with open(LOG, "w", encoding="utf-8", errors="replace") as log:
    p = subprocess.Popen(
        [sys.executable, "-u", os.path.join(DEV, "serial_bridge.py"), "--selftest"],
        stdout=log, stderr=subprocess.STDOUT, cwd=DEV, env=env)
    p.wait(timeout=150)

print("=" * 62)
print("桥日志")
print("=" * 62)
with open(LOG, "r", encoding="utf-8", errors="replace") as f:
    print(f.read())
