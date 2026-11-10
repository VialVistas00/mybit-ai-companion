# -*- coding: utf-8 -*-
"""在板子上模拟 main.py 的模块检测逻辑，确认能走到 audio 分支"""
import os
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''try:
    import microphone
    _MIC = "microphone"
except ImportError:
    try:
        import audio
        _MIC = "audio"
    except ImportError:
        _MIC = None

print('检测结果 _MIC =', _MIC)

if _MIC == "audio":
    print('-> 会走 audio 分支')
    import os, gc
    try:
        os.remove('t.wav')
    except Exception:
        pass
    gc.collect()
    audio.recorder_init()
    print('recorder_init 成功')
    audio.record('t.wav', 2)
    print('record 成功, 文件', os.stat('t.wav')[6], '字节')
    try:
        audio.recorder_deinit()
    except Exception:
        pass
    os.remove('t.wav')
    print('全部正常')
elif _MIC == "microphone":
    print('-> 会走 microphone 分支')
else:
    print('-> 两个都没有，会显示无录音模块')
'''

d = MyBit("COM3")
try:
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\mictest.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "mictest.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.3)
    print(d.exec("exec(open('mictest.py').read())", deadline=60).strip()[:2000])
finally:
    d.close()
