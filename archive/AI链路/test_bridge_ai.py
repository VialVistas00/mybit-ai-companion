# -*- coding: utf-8 -*-
"""
完整链路测试：
  1. 启动桥（独占 COM3）
  2. 趁桥启动的间隙不行 —— 改为：先让板子进入"等待提问"状态，
     再由桥在一次会话里完成 AI 调用。
  实际做法：桥启动后，我们用板子的 raw REPL 是不行的（串口被桥占）。
  所以改用：桥支持一个特殊指令 TEST，桥自己会发起一次完整自测。
本脚本：停桥 -> 让板子运行 selftest（发送提问并打印结果）-> 立刻启桥
        桥在板子等待期间读行并回答。
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

DEV = r"D:\数据文件\上课\信电导论\开发板"

SELFTEST = r'''import sys, time
try:
    import ubinascii as b64
except ImportError:
    import binascii as b64

time.sleep(1)
sys.stdout.write('Q|' + b64.b2a_base64('用一句话介绍你自己'.encode('utf-8')).strip().decode() + '\n')
t0 = time.ticks_ms()
got = None
while time.ticks_ms() - t0 < 70000:
    line = sys.stdin.readline()
    if not line:
        continue
    line = line.strip()
    if line.startswith('R|') or line.startswith('E|'):
        try:
            got = b64.a2b_base64(line[2:].encode()).decode('utf-8')
        except Exception:
            got = line[2:]
        break
print('FINAL|' + str(got))
'''

# 1) 用 mybit 把 selftest 写进板子，但只写文件、不立即执行
d = MyBit("COM3")
try:
    tmp = os.path.join(DEV, "_scratch", "st.py")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(SELFTEST)
    d.put(tmp, "selftest.py")
    print("[1] selftest.py 已上传")
finally:
    d.close()
    print("[2] 串口已释放")

time.sleep(1)

# 2) 启动桥
out = open(os.path.join(DEV, "_bridge.log"), "w", encoding="utf-8", errors="replace")
err = open(os.path.join(DEV, "_bridge.err.log"), "w", encoding="utf-8", errors="replace")
bridge = subprocess.Popen([sys.executable, "-u", os.path.join(DEV, "serial_bridge.py")],
                          stdout=out, stderr=err, cwd=DEV)
print("[3] 桥已启动 PID", bridge.pid)
time.sleep(4)

# 3) 现在用另一个进程也是不行的（桥独占），
#    所以通过写一个标记文件让桥之后的板子复位触发自测。
#    简化：直接软复位板子 —— 但串口被桥占，无法发复位。
#    解决：桥在启动时会先发 Ctrl-C/Ctrl-D，板子会重启并运行 main.py。
#    main.py 是 AI 学伴，需要按键。这里改为让 selftest 成为 main.py 的临时版本。
print("[4] 检查桥日志")
time.sleep(2)
log = os.path.join(DEV, "_bridge.log")
if os.path.exists(log):
    with open(log, "r", encoding="utf-8", errors="replace") as f:
        print(f.read()[-800:])
print("\n桥 PID:", bridge.pid, "（保留运行）")
