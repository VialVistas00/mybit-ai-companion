from npython import wifi,oled,time,led,rgb,beep
# 导入Microdot
from microdot import Microdot,Response
import uio
# 使用uio.StringIO类创建一个文本流对象
#s = uio.StringIO(text)
global ledflag,rgbflag1,rgbflag2,data1,data2,data3,data4,musicflag
ledflag=0;rgbflag1=0;rgbflag2=0;musicflag=0
data1=0;data2=0;data3=0;data4=0
# 网络连接参数
ipserver="111" #热点名称
ippass="99999999" #热点密码
#网络连接
ip=wifi.connect(ipserver,ippass)
oled.print(1,1,ip,1)
time.sleep(2)

# 实例化这个类
app = Microdot()
#----------------
from temphtml import htmltemp1
htmltemp2="</body></html>"
showmode=""
msg=Response()
msg.body=uio.StringIO(showmode)
msg.headers['Content-Type'] = 'text/html; charset=UTF-8'

@app.route('/')
def index1(request):
    global data1,data2,data3,data4
    showmode=htmltemp1+"<h1>温度：%s,湿度：%s</h1><br><h1>光线：%s,声音：%s</h1>" % (data1,data2,data3,data4)+htmltemp2
    msg.body=uio.StringIO(showmode)
    return msg

#网页响应程序------
#接收来自网页的按钮操作
@app.get('/ledon')
def index2(request):
    global ledflag
    ledflag=1
    led.on()
    return "1"
@app.get('/ledoff')
def index2(request):
    global ledflag
    ledflag=0
    led.off()
    return "0"
@app.get('/rgbon')
def index3(request):
    global rgbflag1
    rgbflag1=1
    rgb.write_left(255,0,0)
    return "3"
@app.get('/rgboff')
def index3(request):
    global rgbflag1
    rgbflag1=0
    rgb.write_left(0,0,0)
    return "2"
@app.get('/musicon')
def index4(request):
    global rgbflag2
    rgbflag2=1
    rgb.write_right(0,255,0)
    return "5"
@app.get('/musicoff')
def index4(request):
    global rgbflag2
    rgbflag2=0
    rgb.write_right(0,0,0)
    return "4"


#客户端响应程序------
#接收来自客户端的数据
@app.route('/input', methods=['GET', 'POST'])
def index5(req):
    global data1,data2,data3,data4
    if req.method == 'POST':
        pass
        #name = req.form.get('name')
    else:
        data1=req.args.get('tempval')
        data2=req.args.get('humval')
        data3=req.args.get('lightval')
        data4=req.args.get('soundval')
    print(data1,data2,data3,data4)
    return "ok"
@app.route('/inputs', methods=['GET', 'POST'])
def index5(req):
    global ledflag,rgbflag1,rgbflag2,musicflag
    #ledflag=1;rgbflag1=0;rgbflag2=1 #test
    print(ledflag,rgbflag1,rgbflag2,musicflag)
    return "P%d%d%d%d" %(ledflag,rgbflag1,rgbflag2,musicflag)

while True:
    try:
        app.run()
        print("get a right done!")
    except Exception as e:
        #print(e)
        pass

#端口5000
#app.run(host='0.0.0.0', port=5000, debug=False, ssl=None)