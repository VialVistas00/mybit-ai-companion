# -*- coding: utf_8 -*-
# [Python/Mybit]
from npython import *           # 导入npython模块

data=light.read() #获取光线值
if data<200: #如果光线值小于200
	led.on() #打开LED灯
else:
	led.off() #关闭LED灯
#程控微型风扇接pin0，程控加热模块接pin1
data=aht20.read_temp() #获取温度值
if data<20: #如果温度值小于20
	pin1.write_digital(1) #打开程控加热模块
else:
	pin1.write_digital(0) #关闭程控加热模块
if data>30: #如果温度值大于30
	pin0.write_digital(1) #打开程控微型风扇
else:
	pin0.write_digital(0) #关闭程控微型风扇