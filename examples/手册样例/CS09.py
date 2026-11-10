# -*- coding: utf_8 -*-
# [Python/Mybit]
from npython import *           # 导入npython模块

x=0 #选数初值
oled.print(1,1,str(x),1) #显示选数值
#选数字0~9，A键为选数+1循环（0~9），B键选定退出
while True:
	if button.get_a()==1: #A键按下处理
		x=x+1 #选数加1
		if x>9: #超9回0
			x=0
		oled.print(1,1,str(x),1) #显示选数值
		time.sleep(1) #延时，去按键连续处理
	if button.get_b()==1: #B键按下处理
		break #退出选择
#根据选数获取摩尔斯编码
ms=[[1,1,1,1,1],[0,1,1,1,1],[0,0,1,1,1],[0,0,0,1,1],[0,0,0,0,1],
	[0,0,0,0,0],[1,0,0,0,0],[1,1,0,0,0],[1,1,1,0,0],[1,1,1,1,0]] 
a=ms[x]
#根据编码发出声音
for i in range(5):
	if a[i]==1:
		beep.time(1000)
	else:
		beep.time(500)
	time.sleep(1)
#结束