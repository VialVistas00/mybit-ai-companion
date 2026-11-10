# -*- coding: utf-8 -*-
"""测试板子固件内置的讯飞识别接口 audio.xunfei_iat_record"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import audio
print('讯飞接口:', [x for x in dir(audio) if 'xunfei' in x])
print()

def t(desc, fn):
    try:
        r = fn()
        print('  %-46s -> OK %s' % (desc, repr(r)[:100]))
        return r
    except TypeError as e:
        print('  %-46s -> TypeError %s' % (desc, str(e)[:100]))
    except Exception as e:
        print('  %-46s -> %s: %s' % (desc, type(e).__name__, str(e)[:90]))
    return None

AK = 'YOUR_XFYUN_APPID'
SK = 'YOUR_XFYUN_APISECRET'

t('xunfei_iat_config()', lambda: audio.xunfei_iat_config())
t('xunfei_iat_config(AK,SK)', lambda: audio.xunfei_iat_config(AK, SK))
t('xunfei_iat_config(AK,SK,16000)', lambda: audio.xunfei_iat_config(AK, SK, 16000))

print()
print('--- xunfei_iat_record 参数探测 ---')
t('xunfei_iat_record()', lambda: audio.xunfei_iat_record())
t('xunfei_iat_record(3)', lambda: audio.xunfei_iat_record(3))

print()
print('--- xunfei_iat 参数探测 ---')
t('xunfei_iat()', lambda: audio.xunfei_iat())
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\xf2.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "xf2.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.3)
    print(d.exec("exec(open('xf2.py').read())", deadline=90).strip()[:3000])
finally:
    d.close()
