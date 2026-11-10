# -*- coding: utf-8 -*-
"""模拟板子向桥发一条文本提问，验证 电脑端协议 + AI 回复"""
import base64
import time

import serial

ser = serial.Serial("COM3", 115200, timeout=0.2)
time.sleep(0.3)
ser.reset_input_buffer()

q = "用一句话说说物联网是什么"
line = "Q|" + base64.b64encode(q.encode("utf-8")).decode() + "\n"
print("发送:", line.strip()[:60])
ser.write(line.encode())

print("等待回答...")
t0 = time.time()
buf = b""
while time.time() - t0 < 90:
    c = ser.readline()
    if not c:
        continue
    txt = c.decode("utf-8", "ignore").strip()
    if not txt:
        continue
    if txt.startswith("R|"):
        ans = base64.b64decode(txt[2:] + "===").decode("utf-8", "ignore")
        print("\n[回答]", ans)
        break
    elif txt.startswith("E|"):
        err = base64.b64decode(txt[2:] + "===").decode("utf-8", "ignore")
        print("\n[错误]", err)
        break
    else:
        print("  (板子其他输出)", txt[:80])
ser.close()
