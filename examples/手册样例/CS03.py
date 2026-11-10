# -*- coding: utf_8 -*-
# [Python/Mybit]
from npython import *           # 导入npython模块

time.sleep(2) #延时2秒
data=light.read() #获取光线值
oled.print(1,1,str(data),1) #第一行上显示获得的值，带清行
data=sound.read() #获取声音值
oled.print(1,2,str(data),1) #第二行上显示获得的值，带清行
data=aht20.read_temp() #获取温度值
oled.print(1,3,str(data),1) #第行上显示获得的值，带清行
data=aht20.read_hum() #获取湿度值
oled.print(1,4,str(data),1) #第四行上显示获得的值，带清行