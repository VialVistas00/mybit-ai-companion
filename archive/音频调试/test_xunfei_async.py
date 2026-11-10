# -*- coding: utf-8 -*-
"""验证 xunfei_iat 的异步模式：record 启动 -> iat 取结果"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import audio, time
AK = 'YOUR_XFYUN_APPID'
SK = 'YOUR_XFYUN_APISECRET'

audio.xunfei_iat_config(AK, SK)
time.sleep(0.3)

print('启动录制...')
r0 = audio.xunfei_iat_record(3)
print('record 返回:', repr(r0))

print('轮询 xunfei_iat() ...')
for i in range(20):
    time.sleep(1)
    try:
        r = audio.xunfei_iat()
    except Exception as e:
        print('  [%2ds] 异常 %s: %s' % (i + 1, type(e).__name__, str(e)[:60]))
        continue
    print('  [%2ds] 返回 %s: %r' % (i + 1, type(r).__name__, r if not isinstance(r, str) else r[:160]))
    if r:
        break
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\xf4.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "xf4.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.3)
    print(d.exec("exec(open('xf4.py').read())", deadline=150).strip()[:3000])
finally:
    d.close()
