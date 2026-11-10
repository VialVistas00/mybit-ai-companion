# -*- coding: utf-8 -*-
"""端到端验证：自动演示蛇的移动/渲染/撞墙判定/音效调用，不依赖按键"""
import sys
sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
from mybit import MyBit

d = MyBit("COM3")
try:
    d.ser.write(b"\x03\x03")
    import time as _t; _t.sleep(0.3); d._drain(0.3)

    print("=== 自动演示：蛇一路向右直到撞墙 ===")
    print(d.exec(
        "from npython import *\n"
        "import time\n"
        "CELL=4;COLS=32;ROWS=13;TOP=12\n"
        "def draw(cx,cy,st):\n"
        "    px=cx*CELL;py=TOP+cy*CELL\n"
        "    if st==0: oled.fill_rect(px,py,CELL,CELL,1)\n"
        "    elif st==1: oled.fill_rect(px+1,py+1,CELL-2,CELL-2,1)\n"
        "    else: oled.fill_rect(px,py,CELL,CELL,1)\n"
        "snake=[(14,6),(13,6),(12,6)]\n"
        "fx,fy=20,6\n"
        "oled.fill(0)\n"
        "oled.print(1,1,' AUTO DEMO ',1)\n"
        "steps=0\n"
        "t0=time.ticks_ms()\n"
        "dead=False\n"
        "while not dead:\n"
        "    hx=snake[0][0]+1; hy=snake[0][1]\n"
        "    if hx>=COLS: dead=True; break\n"
        "    snake.insert(0,(hx,hy)); snake.pop()\n"
        "    oled.fill_rect(0,TOP,128,52,0)\n"
        "    draw(fx,fy,2)\n"
        "    for i in range(len(snake)):\n"
        "        draw(snake[i][0],snake[i][1],0 if i==0 else 1)\n"
        "    oled.show()\n"
        "    steps+=1\n"
        "t1=time.ticks_ms()\n"
        "print('移动步数', steps, '总耗时', t1-t0, 'ms, 每帧', (t1-t0)//steps, 'ms')\n"
        "print('撞墙判定触发 -> GAME OVER')\n"
        "music.pitch(700,80); music.pitch(500,80); music.pitch(300,150)\n"
        "print('死亡音效 3 声已播放')", deadline=45).strip())

    print("\n=== 逻辑单元测试：食物生成 / 吃食 / 自撞 ===")
    print(d.exec(
        "import urandom as rnd\n"
        "COLS=32;ROWS=13\n"
        "def new_food(snake, ss):\n"
        "    for _ in range(400):\n"
        "        fx=rnd.getrandbits(8)%COLS; fy=rnd.getrandbits(8)%ROWS\n"
        "        if (fx,fy) not in ss: return fx,fy\n"
        "    return None\n"
        "# 1 食物不落在蛇身上\n"
        "snake=[(i,6) for i in range(30)]\n"
        "ss=set(snake)\n"
        "ok=True\n"
        "for _ in range(200):\n"
        "    p=new_food(snake,ss)\n"
        "    if p in ss: ok=False; break\n"
        "print('食物从不生成在蛇身上:', ok)\n"
        "# 2 撞自己判定\n"
        "def will_die(hx,hy,snake,ss,eat):\n"
        "    tail=snake[len(snake)-1]\n"
        "    if (hx,hy) in ss and not ((hx==tail[0] and hy==tail[1]) and eat==0):\n"
        "        return True\n"
        "    return False\n"
        "s=[(5,5),(5,6),(6,6),(6,5)]\n"
        "setx=set(s)\n"
        "print('撞身体(5,5):', will_die(5,5,s,setx,0), '(应 True)')\n"
        "print('撞尾巴(6,5)不吃:', will_die(6,5,s,setx,0), '(应 False, 尾巴会让位)')\n"
        "print('撞尾巴(6,5)吃食物:', will_die(6,5,s,setx,1), '(应 True)')\n"
        "print('空地(7,5):', will_die(7,5,s,setx,0), '(应 False)')\n"
        "# 3 转向不能 180\n"
        "def turn(d, cw):\n"
        "    nd = (d+1)%4 if cw else (d+3)%4\n"
        "    if nd == (d+2)%4: return d\n"
        "    return nd\n"
        "print('向右(1)顺时针->', turn(1,True), '(应 2=下)')\n"
        "print('向右(1)逆时针->', turn(1,False), '(应 0=上)')\n"
        "print('向上(0)逆时针->', turn(0,False), '(应 3=左)')\n", deadline=40).strip())
finally:
    d.close()
