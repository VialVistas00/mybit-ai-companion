# -*- coding: utf_8 -*-
# [Python/Mybit]
from npython import *           # 导入npython模块

while True:
	data=light.read() #获取光线值
	if data<200: #如果光线值小于200
		led.on() #打开LED灯
	if data>1000: #如果光线值大于1000
		led.off() #关闭LED灯