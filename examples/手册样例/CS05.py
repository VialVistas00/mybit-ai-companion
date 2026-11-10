# -*- coding: utf_8 -*-
# [Python/Mybit]
from npython import *           # 导入npython模块

rgb.write_left(255,0,0) #左RGB亮红灯
time.sleep(30) #延时30秒
rgb.write_left(255,255,0) #左RGB亮黄灯
time.sleep(10) #延时10秒
rgb.write_left(0,255,0) #左RGB亮绿灯
time.sleep(30) #延时30秒
rgb.write_left(255,255,0) #左RGB亮黄灯
time.sleep(10) #延时30秒
rgb.write_left(0,0,0) #左RGB关闭