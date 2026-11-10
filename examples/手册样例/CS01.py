# -*- coding: utf_8 -*-
# [Python/Mybit]
from npython import *           # 导入npython模块

oled.print(1,1,"123456",1) #第一行上显示“123456”，带清行
oled.print(1,2,"中国",0) #第二行上显示"中国"，不带清行
oled.print(1,3,"China",0) #第三行上显示"China"，不带清行
oled.line(10,10,120,50,1) #画一条直线
oled.circle(32,32,10,1) #画一个空心圆
oled.fill_rect(50,20,60,40,1) #画一个实心矩形
oled.show() #绘图输出