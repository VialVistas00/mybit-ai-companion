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
	#获取环境数据
	light1=light.read()
	temp1=aht20.read_temp()
	hum1=aht20.read_hum()
	try:
		data=urequests.get('http://'+str(url)+'/input?id=1&tempval='
			+str(temp1)+'&lightval='+str(light1)+'&humval='+str(hum1))
		oled.print(1,2,"上传成功",1)
	except Exception as e:
		oled.print(1,2,"上传失败",1)
		continue
	time.sleep(1)
	#获取控制数据
	try:
		val=urequests.get('http://'+str(url)+'/inputs')
	except Exception as e:
		oled.print(1,3,"控制失败",1)
		continue
	if val.content ==b'turn':
		oled.print(1,3,'开灯',1)
		led.on()
	if val.content ==b'off':
		oled.print(1,3,'关灯',1)
		led.off()
	time.sleep(1)