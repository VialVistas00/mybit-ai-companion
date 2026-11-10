# -*- coding: utf_8 -*-
# [Python/Mybit]
from npython import *           # 导入npython模块

led.on() #打开LED灯
time.sleep(2) #延时2秒
led.off() #关闭LED灯
#程控微型风扇接pin0，程控加热模块接pin1
pin0.write_digital(1) #打开程控微型风扇
time.sleep(2) #延时2秒
pin0.write_digital(0) #关闭程控微型风扇
pin1.write_digital(1) #打开程控加热模块
time.sleep(2) #延时2秒
pin1.write_digital(0) #关闭程控加热模块