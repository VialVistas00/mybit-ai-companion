# -*- coding: utf-8 -*-
"""探测 audio 各接口的签名（用不同参数试探）"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import audio

def probe(name, calls):
    f = getattr(audio, name, None)
    if f is None:
        print('%-22s 不存在' % name)
        return
    print('--- %s ---' % name)
    for desc, fn in calls:
        try:
            r = fn()
            print('   %-28s -> OK %s' % (desc, repr(r)[:80]))
        except TypeError as e:
            print('   %-28s -> TypeError %s' % (desc, str(e)[:90]))
        except Exception as e:
            print('   %-28s -> %s: %s' % (desc, type(e).__name__, str(e)[:80]))

probe('recorder_init', [
    ('recorder_init()', lambda: audio.recorder_init()),
])

probe('record', [
    ('record()', lambda: audio.record()),
    ('record(1)', lambda: audio.record(1)),
    ('record(1000)', lambda: audio.record(1000)),
])

probe('player_init', [
    ('player_init()', lambda: audio.player_init()),
])

probe('xunfei_iat_config', [
    ('xunfei_iat_config()', lambda: audio.xunfei_iat_config()),
    ('xunfei_iat_config(1)', lambda: audio.xunfei_iat_config(1)),
])

probe('xunfei_tts_config', [
    ('xunfei_tts_config()', lambda: audio.xunfei_tts_config()),
])

probe('loudness', [
    ('loudness()', lambda: audio.loudness()),
])
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\audiosig.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "audiosig.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.3)
    print(d.exec("exec(open('audiosig.py').read())", deadline=90).strip()[:3000])
finally:
    d.close()
