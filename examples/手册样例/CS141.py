# -*- coding: utf_8 -*-
# [Python/Mybit]
from npython import *           # 导入npython模块

#回调函数
def event(topic,msg):
	data=str(msg.decode('uft-8'))
	oled.print(1,4,data,1)
	if data == "LEDON":
		led.on()
	if data == "LEDOFF":
		led.off()

IP=wifi.connect("YOUR_WIFI_SSID","YOUR_WIFI_PASSWORD")
oled.print(1,1,str(IP),1)
mqtt.config("121.5.75.157",1883)
mqtt.connect()
oled.print(1,2,"MQTT连接成功",1)
while True:
	mqtt.subscribe("Weather/sensor",event)
	time.sleep(1)