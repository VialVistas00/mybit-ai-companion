# -*- coding: utf-8 -*-
"""实测板载讯飞识别：录音3秒并识别，看返回什么"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import audio, time
AK = 'YOUR_XFYUN_APPID'
SK = 'YOUR_XFYUN_APISECRET'

print('配置讯飞...')
audio.xunfei_iat_config(AK, SK)
time.sleep(0.3)
print('开始录音识别 3 秒（现在对板子说话）...')
t0 = time.ticks_ms()
r = audio.xunfei_iat_record(3)
t1 = time.ticks_ms()
print('耗时', t1 - t0, 'ms')
print('返回类型:', type(r))
print('返回内容:', repr(r)[:300])
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\xf3.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "xf3.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.3)
    print(d.exec("exec(open('xf3.py').read())", deadline=120).strip()[:2000])
finally:
    d.close()
