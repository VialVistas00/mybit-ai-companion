# -*- coding: utf_8 -*-
# [Python/Mybit]
from npython import *           # 导入npython模块

ssid="myap"
spass="YOUR_WIFI_PASSWORD"
wifi.enable_AP(ssid,spass,10)
oled.print(1,1,str(ssid),1)
oled.print(1,2,str(spass),1)
time.sleep(60)
wifi.disable_AP()