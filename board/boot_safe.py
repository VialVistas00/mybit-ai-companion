# This file is executed on every boot (including wake-boot from deepsleep)
# 原始厂商版本(2024-5-10)：上电时若 A 键被按住，会执行 os.remove("/main.py")
#   —— 本意是"应急清程序"，但正常游戏中按 A 也满足条件，一旦上电/复位发生在
#      按键瞬间，main.py 就被删掉，表现为"程序消失了、按键没反应"。
# 本版本：保留引脚检测，但不再删除任何文件。
try:
    import machine
    _b = machine.Pin(21, machine.Pin.IN)
    _v = _b.value()
    del _b
    if _v == 1:
        print('boot: A held - program kept')
except Exception:
    pass
