# -*- coding: utf-8 -*-
"""验证板子端协议：板子发 Q| -> 我们回 R| -> 板子打印收到的内容"""
import base64
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

BOARD_SIDE = r'''import sys, time
try:
    import ubinascii as b64
except ImportError:
    import binascii as b64

sys.stdout.write('Q|' + b64.b2a_base64('测试问题'.encode('utf-8')).strip().decode() + '\n')
t0 = time.ticks_ms()
got = '<无回复>'
while time.ticks_ms() - t0 < 8000:
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
print('RESULT|' + got)
'''

d = MyBit("COM3")
try:
    d.ser.write(b"\x03\x03")
    time.sleep(0.3)
    d._drain(0.4)
    d._raw_enter()
    d.ser.write(BOARD_SIDE.encode() + b"\x04")

    # 收集板子输出，找到 Q| 行
    buf = b""
    t0 = time.time()
    qline = None
    while time.time() - t0 < 10:
        chunk = d.ser.read(d.ser.in_waiting or 1)
        if chunk:
            buf += chunk
            for ln in buf.decode("utf-8", "ignore").replace("\r", "").split("\n"):
                pos = ln.find("Q|")
                if pos >= 0:
                    qline = ln[pos:]
                    break
        if qline:
            break

    if qline:
        q = base64.b64decode(qline[2:] + "===").decode("utf-8")
        print("[1] 板子提问 =", q)
        ans = "电脑端已收到问题并作答"
        d.ser.write(("R|" + base64.b64encode(ans.encode("utf-8")).decode() + "\n").encode())
        print("[2] 已回覆   =", ans)
        time.sleep(1.8)
        tail = d.ser.read(d.ser.in_waiting or 1)
        time.sleep(0.4)
        tail += d.ser.read(d.ser.in_waiting or 1)
        txt = tail.decode("utf-8", "ignore")
        print("[3] 板子输出 =", repr(txt)[:300])
        if "RESULT|" in txt:
            pos = txt.find("RESULT|")
            print("[4] 板子最终收到 =", txt[pos + 7:].split("\r")[0].split("\n")[0])
            print("\n*** 双向协议验证通过 ***")
        else:
            print("[!] 未见 RESULT| 标记")
    else:
        print("[!] 没收到 Q| ，原始:", repr(buf.decode("utf-8", "ignore"))[:300])

    d._raw_exit()
    d.ser.write(b"\x04")
    time.sleep(1.0)
    d._drain(0.5)
finally:
    d.close()
