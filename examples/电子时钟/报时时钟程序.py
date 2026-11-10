#定时报时时钟系统
from npython import *
from machine import RTC
#建一个时钟对像
rtc = RTC()
'''
#从网络中进行时钟校正
# 网络连接参数
ipserver="YOUR_WIFI_SSID" #热点名称
ippass="YOUR_WIFI_PASSWORD" #热点密码
#网络连接
ip=wifi.connect(ipserver,ippass)
# 校正系统主板时钟
import ntptime
ntptime.host = 'ntp1.aliyun.com'
ntptime.settime() # set the rtc datetime from the remote server
rtc.datetime()    # get the date and time in UTC
print("当前时间：", rtc.datetime())
'''
#或时间初值进行设定，而不从网络中设置
rtc.datetime((2023, 11, 14, 1,15, 59, 40, 0)) # （年，月，日，星期，时，分，秒，子秒)
print("当前时间：", rtc.datetime())
now=rtc.datetime()
oled.print(1,1,"当前时间：%02d:%02d:%02d" %(now[4],now[5],now[6]),1)
oled.print(1,2,"2秒内按住A键进入指针时钟",1)
time.sleep(2)
#----------------------
#指针时钟相关参数
import math
PI=3.14
#秒/分为60分度
dat=2*PI/60
#时为12分度
dath=2*PI/12
sita0=-PI/2
#秒针长20,分针长15,时针长10
#----------------------
if button.get_a():
    oled.fill(0)
    oled.print(1,1,"已进入指针时钟!",1)
    time.sleep(2)
    oled.fill(0)
    #绘制表面
    oled.circle(32,32,20,1)
    oled.display("12",32-7,-1)
    oled.display("3",32+20,32-7)
    oled.display("6",32-7,32+20)
    oled.display("9",32-27,32-7)
    oled.show()
    while True:
        time.sleep(0.5)
        now=rtc.datetime()
        oled.print(9,1,"%02d:%02d:%02d" %(now[4],now[5],now[6]),0)
        data1=aht20.read_temp()
        oled.print(9,2,"温度:%04d" % data1,0)
        data2=aht20.read_hum()
        oled.print(9,3,"湿度:%04d" % data2,0)
        data3=sound.read()
        oled.print(9,4,"音量:%04d" % data3,0)
        data4=light.read()/4.2
        oled.print(9,5,"亮度:%04d" % data4,0)
        #清除指针显示
        oled.fill_circle(32,32,20,0)
        oled.circle(32,32,20,1)
        #秒针显示
        sita=sita0+int(now[6])*dat
        x=int(20*math.cos(sita))+32
        y=int(20*math.sin(sita))+32
        print(x,y)
        oled.line(32,32,x,y,1)
        #分针显示
        sita=sita0+int(now[5])*dat+dat*int(now[6])/60
        x=int(15*math.cos(sita))+32
        y=int(15*math.sin(sita))+32
        print(x,y)
        oled.line(32,32,x,y,1)
        #时针显示 #超过12处理
        sita=sita0+(int(now[4])%12)*dat*5+dat*5*int(now[5])/60
        x=int(10*math.cos(sita))+32
        y=int(10*math.sin(sita))+32
        print(x,y)
        oled.line(32,32,x,y,1)
        oled.show()
        #温度报警
        if data1>30:
            rgb.write_left(255,0,0)
        else:
            rgb.write_left(0,255,0)
        #湿度报警
        if data2>60:
            rgb.write_right(255,0,0)
        else:
            rgb.write_right(0,255,0)
        #声音报警
        if data3>500:
            beep.time(500)
        else:
            pass
        #亮度报警
        if data4>100:
            led.off()
        else:
            led.on()
#下面程序为数字时钟的显示输出
while True:
    #取当前的时间数据列表（年，月，日，星期，时，分，秒，子秒)
    now=rtc.datetime()
    #半点报时
    if(now[5]==30 and now[6]==0):
        beep.time(1000)
    #整点报时
    if(now[5]==0 and now[6]==0):
        music.play(gequ[3])
    #显示时间与环境参数
    oled.print(1,1,"时间：%02d:%02d:%02d" %(now[4],now[5],now[6]),1)
    data1=aht20.read_temp()
    oled.print(1,2,"温度：%8.2f C" % data1,1)
    data2=aht20.read_hum()
    oled.print(1,3,"湿度：%8.2f %%" % data2,1)
    data3=sound.read()
    oled.print(1,4,"音量：%5d R" % data3,1)
    data4=light.read()/4.2
    oled.print(1,5,"亮度：%8.2f Lux" % data4,1)
    #温度报警
    if data1>30:
        rgb.write_left(255,0,0)
    else:
        rgb.write_left(0,255,0)
    #湿度报警
    if data2>60:
        rgb.write_right(255,0,0)
    else:
        rgb.write_right(0,255,0)
    #声音报警
    if data3>500:
        beep.time(500)
    else:
        pass
    #亮度报警
    if data4>100:
        led.off()
    else:
        led.on()
    time.sleep(0.2)