# -*- coding: utf_8 -*-
from npython import *           # 导入npython模块
'''
实验说明：
1.硬件设备：信息科技实验板；
2.功能说明：获取网络时间进行校时，并设计一个数字电子时钟；
'''
#在下面开始写你自己的代码
from machine import RTC
#建一个时钟对像
rtc = RTC()
#或时间初值进行设定，而不从网络中设置
#rtc.datetime((2023, 11, 14, 1,15, 59, 40, 0)) # （年，月，日，星期，时，分，秒，子秒)
#print("当前时间：", rtc.datetime())
#从网络中进行时钟校正
# 网络连接参数
ipserver="YOUR_WIFI_SSID" #热点名称
ippass="YOUR_WIFI_PASSWORD" #热点密码
try:
	#网络连接
	ip=wifi.connect(ipserver,ippass)
	# 校正系统主板时钟
	import ntptime
	ntptime.host = "cn.ntp.org.cn" #中国国家时间服务器
	ntptime.settime() # set the rtc datetime from the remote server
	rtc.datetime()    # get the date and time in UTC
	print("当前时间：", rtc.datetime())
except:
	oled.print(1,5,"网络校准失败！",1)
while True:
	data=rtc.datetime()
	oled.print(1,1,"       数字电子时钟",1)
	oled.print(1,2,str(data[0])+"年"+str(data[1])+'月'+str(data[2])+'日',1)
	oled.print(1,3,"时间：%02d:%02d:%02d" %(data[4],data[5],data[6]),1)
	time.sleep(0.5)
