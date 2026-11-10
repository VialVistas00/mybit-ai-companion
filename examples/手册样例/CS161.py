# -*- coding: utf_8 -*-
# [Python/Mybit]
from npython import *           # 导入npython模块
import urequests

IP=wifi.connect("YOUR_WIFI_SSID","YOUR_WIFI_PASSWORD")
oled.print(1,1,str(IP),1)
SERVOS_SIP="192.168.0.44"  #服务端IP
PORT="8080"                #服务端端口
url=str(SERVOS_SIP)+':'+str(PORT)

while True:
	#获取控制数据
	val=urequests.get('http://'+str(url)+'/inputs')
	if val.content ==b'turn':
		oled.print(1,2,'开灯',1)
		led.on()
	if val.content ==b'off':
		oled.print(1,2,'关灯',1)
		led.off()
	time.sleep(1)