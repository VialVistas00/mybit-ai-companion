# -*- coding: utf-8 -*-
"""摸清 audio 录音模块的调用方式"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import audio
print('audio 全部接口:', [x for x in dir(audio) if not x.startswith('_')])
print()
print('=== 逐个方法的说明 ===')
for name in ['recorder_init', 'record', 'recorder_deinit', 'player_init', 'play', 'stop', 'loudness']:
    f = getattr(audio, name, None)
    if f is None:
        print('%-16s 不存在' % name)
        continue
    d = getattr(f, '__doc__', None)
    print('%-16s %s' % (name, (d or '(无文档)')[:200] if d else '(无文档)'))
    try:
        print('%-16s 可用参数? %s' % ('', getattr(f, '__dict__', None)))
    except Exception:
        pass
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\audiodoc.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "audiodoc.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.3)
    print(d.exec("exec(open('audiodoc.py').read())", deadline=60).strip()[:2500])
finally:
    d.close()
