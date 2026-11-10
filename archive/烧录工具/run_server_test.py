# -*- coding: utf-8 -*-
"""
端到端验证：板子录音 -> 我这边收 -> 识别 -> AI -> 回传板子
服务在后台线程里跑，主线程负责触发板子录音。
"""
import os
import subprocess
import sys
import time

DEV = r"D:\数据文件\上课\信电导论\开发板"
LOG = os.path.join(DEV, "_server.log")

# 确保没有旧进程占串口
for line in subprocess.run(
        ["powershell", "-NoProfile", "-c",
         "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
         "Where-Object {$_.CommandLine -match 'board_server|serial_bridge'} | "
         "ForEach-Object { $_.ProcessId }"],
        capture_output=True, text=True).stdout.split():
    try:
        subprocess.run(["taskkill", "/F", "/PID", line], capture_output=True)
    except Exception:
        pass
time.sleep(2)

# 启动服务
env = dict(os.environ)
env["PYTHONIOENCODING"] = "utf-8"
log = open(LOG, "w", encoding="utf-8", errors="replace")
srv = subprocess.Popen([sys.executable, "-u", os.path.join(DEV, "board_server.py")],
                       stdout=log, stderr=subprocess.STDOUT, cwd=DEV, env=env)
print("服务已启动 PID", srv.pid)
time.sleep(6)   # 等模型加载

# 触发板子录音：用独立串口不行（服务占着），
# 所以改成让板子自己按 —— 这里只提示用户
print()
print("=" * 60)
print(" 服务已就绪。现在请按板子上的 A 键说话")
print("=" * 60)
print()

t0 = time.time()
while time.time() - t0 < 70:
    time.sleep(2)
    if os.path.exists(LOG):
        txt = open(LOG, encoding="utf-8", errors="replace").read()
        if "已回传板子" in txt or "识别失败" in txt or "数据不完整" in txt:
            break
        if "MSG|" not in txt and time.time() - t0 > 20:
            pass

print(open(LOG, encoding="utf-8", errors="replace").read())
srv.terminate()
