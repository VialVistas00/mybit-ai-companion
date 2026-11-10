# -*- coding: utf_8 -*-
# [Python/Mybit]
from npython import *           # 导入npython模块

#根据音量调节放大系数
plus=0 #初值0为低响度1为高响度
while True:
	data=sound.read() #获取音量值
	if data<100: #低噪声环境
		plus=0 #低响度
	else:
		if data>500: #高噪声环境
			plus=1 #高响度
	#输出控制
	if plus==0:
		pin0.write_analog(10)
	else:
		pin0.write_analog(1000)
	#切换周期设置
	time.sleep(10) #10秒切换
#结束