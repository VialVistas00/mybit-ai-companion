# -*- coding: utf_8 -*-
# [Python/Mybit]
from npython import *           # 导入npython模块

mystr="" #初始字符串
oled.print(1,1,str(mystr),1) #显示初始串
#选数字0~9，A键为选数+1循环（0~9），B键选定退出
while True:
	if button.get_a()==1 and button.get_b()==1: #A键、B键同时按下处理
		break #退出输入
	elif button.get_a()==1: #A键按下处理
		mystr=mystr+"1"
	elif button.get_b()==1: #B键按下处理
		mystr=mystr+"0"
	else:
		pass
	time.sleep(0.5) #延时用于防止按过多
#根据输入计算十进制值
myvalue=0 #初值
for i in range(len(mystr)): #字串长度进行计算
	if mystr[i]=="1": #是1处理
		myvalue=myvalue*2+1
	else:
		myvalue=myvalue*2+0
#显示计算结果
oled.print(1,2,str(myvalue),1) #显示转换结果
#结束