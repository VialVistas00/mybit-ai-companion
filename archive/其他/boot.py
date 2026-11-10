# boot.py —— 上电保护（改造版 @ 2026-11-10）
# 原版逻辑：上电瞬间 A 键为高电平就删除 main.py  —— 与“A 键 = 上一首”冲突，
# 插电时手按着 A 就会把播放器删掉。现将触发条件改为：按住 A >= 3 秒 才进入救援模式，
# 且不再直接删除，而是把 main.py 改名成 main.bak 保留。
import os
import machine
import time

_b = machine.Pin(21, machine.Pin.IN)
try:
    if _b.value() == 1:
        _t0 = time.ticks_ms()
        _held = False
        while _b.value() == 1:
            if time.ticks_diff(time.ticks_ms(), _t0) > 3000:
                _held = True
                break
            time.sleep_ms(50)
        if _held:
            try:
                os.rename('/main.py', '/main.bak')
            except Exception:
                try:
                    os.remove('/main.py')
                except Exception:
                    pass
except Exception:
    pass
del _b
#end
