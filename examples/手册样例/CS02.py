# -*- coding: utf_8 -*-
# [Python/Mybit]
from npython import *           # 导入npython模块

time.sleep(2) #延时2秒
data=button.get_a() #获取A键值
oled.print(1,1,str(data),1) #第一行上显示获得的值，带清行
data=button.get_b() #获取B键值
oled.print(1,2,str(data),0) #第二行上显示获得的值，不带清行