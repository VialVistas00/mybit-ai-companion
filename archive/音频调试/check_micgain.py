# -*- coding: utf-8 -*-
"""检查板子麦克风的原始信号强度，判断是硬件弱还是设置问题"""
import sys
import time

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

CODE = r'''import audio, gc, os
# 先用 sound.read() 这个已知可用的模拟量看看
from npython import sound
print('sound.read() 环境音量 =', sound.read())
# loudness 接口
try:
    print('audio.loudness() =', audio.loudness())
except Exception as e:
    print('loudness 异常', e)

# 看看 recorder 是否有增益/参数可设
print('recorder 相关方法:', [x for x in dir(audio) if 'record' in x.lower()])
print('set_volume 可用?', hasattr(audio, 'set_volume'))
try:
    audio.set_volume(100)
    print('set_volume(100) OK')
except Exception as e:
    print('set_volume 异常', type(e).__name__, e)

# 录 2 秒并统计真实信号幅度（用极小内存，边读边算）
try:
    os.remove('q.wav')
except Exception:
    pass
gc.collect()
audio.recorder_init()
audio.record('q.wav', 2)
try:
    audio.recorder_deinit()
except Exception:
    pass

f = open('q.wav', 'rb')
f.seek(44)
mx = 0
mn = 0
tot = 0
cnt = 0
skip = 0
while True:
    b = f.read(400)
    if not b:
        break
    n = len(b) // 2
    for i in range(n):
        v = b[i * 2] | (b[i * 2 + 1] << 8)
        if v > 32767:
            v -= 65536
        if skip < 200:
            skip += 1
            continue
        if v > mx:
            mx = v
        if v < mn:
            mn = v
        tot += v
        cnt += 1
f.close()
print('样本数', cnt, '最大', mx, '最小', mn, '均值', tot // max(1, cnt))
print('峰峰值', mx - mn)
os.remove('q.wav')
'''

d = MyBit("COM3")
try:
    d.exec("import gc;gc.collect()", deadline=15)
    tmp = r"D:\数据文件\上课\信电导论\开发板\_scratch\gain.py"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(CODE)
    d.put(tmp, "gain.py")
    d.ser.write(b"\x03\x03"); time.sleep(0.3); d._drain(0.3)
    print(d.exec("import gc;gc.collect()\nexec(open('gain.py').read())", deadline=90).strip()[:1500])
finally:
    d.close()
