# -*- coding: utf_8 -*-
# ============================================================
#  贪 吃 蛇   SNAKE  for  MYBIT 信息科技实验板
#  硬件: ESP32 / MicroPython npython v1.06.x / 128x64 OLED
#  操作: A键 = 顺时针转向      B键 = 逆时针转向
#  音效: music.pitch() 直接驱动板载无源蜂鸣器
#        (beep.time() 阻塞 0.6~1.6s，游戏里不可用，故弃用)
# ============================================================
from npython import *
import time

try:
    import urandom as rnd
except ImportError:
    import random as rnd

# ---------------- 场地参数 ----------------
CELL = 4                      # 每格 4x4 像素
COLS = 32                     # 128 / 4
ROWS = 13                     # 64 - 12(分数行) = 52 -> 13
TOP  = 12                     # 游戏区起始 y
W    = COLS * CELL
H    = ROWS * CELL

SPEED_START = 175             # 每步毫秒
SPEED_MIN   = 85
ACCEL_EVERY = 4               # 每吃 4 个加速一次
ACCEL_STEP  = 12

# 方向: 0上 1右 2下 3左
DX = (0, 1, 0, -1)
DY = (-1, 0, 1, 0)

# ---------------- 音效 ----------------
def sfx(freq, ms):
    try:
        music.pitch(int(freq), int(ms))
    except Exception:
        pass

def sfx_eat():
    sfx(2400, 25)

def sfx_level():
    sfx(1300, 30)
    sfx(1700, 30)
    sfx(2100, 40)

def sfx_die():
    sfx(700, 80)
    sfx(520, 80)
    sfx(360, 110)
    sfx(220, 180)

def sfx_start():
    sfx(900, 30)
    sfx(1400, 30)
    sfx(1900, 45)

# ---------------- 输入 ----------------
_last_a = 0
_last_b = 0

def keys():
    """返回 (A上升沿, B上升沿)；兼容返回 True/False 或任意非零"""
    global _last_a, _last_b
    a = 1 if button.get_a() else 0
    b = 1 if button.get_b() else 0
    ka = 1 if (a == 1 and _last_a == 0) else 0
    kb = 1 if (b == 1 and _last_b == 0) else 0
    _last_a = a
    _last_b = b
    return ka, kb

def any_key():
    return (button.get_a() == 1) or (button.get_b() == 1)

# ---------------- 绘制 ----------------
def draw_cell(cx, cy, style):
    px = cx * CELL
    py = TOP + cy * CELL
    if style == 0:                                  # 头：满格
        oled.fill_rect(px, py, CELL, CELL, 1)
    elif style == 1:                                # 身：留缝
        oled.fill_rect(px + 1, py + 1, CELL - 2, CELL - 2, 1)
    elif style == 2:                                # 食物：实心
        oled.fill_rect(px, py, CELL, CELL, 1)
    else:                                           # 食物闪烁相：空心
        oled.rect(px, py, CELL, CELL, 1)
        oled.pixel(px + 1, py + 1, 1)
        oled.pixel(px + 2, py + 2, 1)

def draw_score(score, length, hi):
    oled.print(1, 1, "S:%d  L:%d  H:%d" % (score, length, hi), 1)

# ---------------- 逻辑 ----------------
def new_food(snake, snake_set):
    for _ in range(400):
        fx = rnd.getrandbits(8) % COLS
        fy = rnd.getrandbits(8) % ROWS
        if (fx, fy) not in snake_set:
            return fx, fy
    # 兜底：全表扫描
    for yy in range(ROWS):
        for xx in range(COLS):
            if (xx, yy) not in snake_set:
                return xx, yy
    return None

def reset_game():
    cx = COLS // 2
    cy = ROWS // 2
    snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
    snake_set = set(snake)
    return snake, snake_set, 1, 0, SPEED_START

# ---------------- 主程序 ----------------
hi_score = 0
sfx_start()
oled.fill(0)
oled.print(1, 1, " SNAKE ", 1)
oled.print(1, 2, "A=逆时针  B=顺时针", 1)
oled.print(1, 3, "按A/B开始", 1)
oled.show()
print("SNAKE READY A=%s B=%s" % (button.get_a(), button.get_b()))

# --- 按键诊断：电平每变化一次就写入 keylog.txt，屏幕上同步显示 ---
try:
    _log = open('/keylog.txt', 'w')
    _log.write('boot A=%s B=%s\n' % (button.get_a(), button.get_b()))
    _log.flush()
except Exception:
    _log = None

_watch = 0
_last = (0, 0)
while not any_key():
    time.sleep_ms(20)
    _watch += 1
    _av = 1 if button.get_a() else 0
    _bv = 1 if button.get_b() else 0
    if (_av, _bv) != _last:
        _last = (_av, _bv)
        if _log:
            _log.write('t=%d A=%d B=%d\n' % (_watch, _av, _bv))
            _log.flush()
        print("CHG A=%d B=%d" % (_av, _bv))
    if _watch % 50 == 0:
        oled.print(1, 4, "A:%d  B:%d" % (_av, _bv), 1)

if _log:
    try:
        _log.write('start\n')
        _log.close()
    except Exception:
        pass
time.sleep_ms(150)

while True:
    snake, snake_set, direction, score, speed = reset_game()
    fx, fy = new_food(snake, snake_set)
    dead = False
    blink = 0

    # ---- 开局重绘 ----
    oled.fill(0)
    draw_score(0, len(snake), hi_score)
    tx = 0
    while tx < COLS:
        draw_cell(tx, fy, 2)
        tx += 2
    for i in range(len(snake)):
        draw_cell(snake[i][0], snake[i][1], 0 if i == 0 else 1)
    oled.show()

    # ---- 一局 ----
    while not dead:
        step_start = time.ticks_ms()

        # 1) 处理输入（B=顺时针 A=逆时针，禁止 180 度掉头）
        ka, kb = keys()
        if kb:
            nd = (direction + 1) % 4
            if nd != (direction + 2) % 4:
                direction = nd
        if ka:
            nd = (direction + 3) % 4
            if nd != (direction + 2) % 4:
                direction = nd

        # 2) 前进一格
        hx = snake[0][0] + DX[direction]
        hy = snake[0][1] + DY[direction]

        # 撞墙
        if hx < 0 or hx >= COLS or hy < 0 or hy >= ROWS:
            dead = True
            break
        # 撞自己（尾巴那格这步会移走，不算撞）
        tail = snake[len(snake) - 1]
        eat = 1 if (hx == fx and hy == fy) else 0
        if (hx, hy) in snake_set and not ((hx == tail[0] and hy == tail[1]) and eat == 0):
            dead = True
            break

        # 3) 移动
        snake.insert(0, (hx, hy))
        snake_set.add((hx, hy))
        if eat:
            score += 1
            if score > hi_score:
                hi_score = score
            sfx_eat()
            rgb.write_left(0, 255, 0)
            rgb.write_right(0, 255, 0)
            fx, fy = new_food(snake, snake_set)
            if fx is None:
                dead = True
                break
            draw_score(score, len(snake), hi_score)
            if score % ACCEL_EVERY == 0:
                sfx_level()
                speed = speed - ACCEL_STEP
                if speed < SPEED_MIN:
                    speed = SPEED_MIN
        else:
            old = snake.pop()
            snake_set.discard(old)
            rgb.write_left(0, 60, 0)
            rgb.write_right(0, 60, 0)

        # 4) 渲染
        oled.fill_rect(0, TOP, W, H, 0)         # 只清游戏区
        draw_cell(fx, fy, 2 if (blink % 4) < 2 else 3)
        i = 0
        n = len(snake)
        while i < n:
            draw_cell(snake[i][0], snake[i][1], 0 if i == 0 else 1)
            i += 1
        oled.show()
        blink += 1

        # 5) 帧节奏 + 期间持续采样按键（响应更快）
        spend = time.ticks_ms() - step_start
        wait = speed - spend
        if wait > 0:
            t_end = time.ticks_ms() + wait
            while time.ticks_ms() < t_end:
                ka, kb = keys()
                if kb:
                    nd = (direction + 1) % 4
                    if nd != (direction + 2) % 4:
                        direction = nd
                if ka:
                    nd = (direction + 3) % 4
                    if nd != (direction + 2) % 4:
                        direction = nd
                time.sleep_ms(8)

    # ---- 结束 ----
    sfx_die()
    rgb.write_left(255, 0, 0)
    rgb.write_right(255, 0, 0)
    led.off()
    print("GAME OVER score=%d len=%d hi=%d" % (score, len(snake), hi_score))

    oled.fill(0)
    oled.print(1, 1, " GAME OVER ", 1)
    oled.print(1, 2, "得分: %d" % score, 1)
    oled.print(1, 3, "最高: %d" % hi_score, 1)
    oled.print(1, 4, "长度: %d" % len(snake), 1)
    oled.print(1, 5, "按A/B再来一局", 1)
    oled.show()

    time.sleep_ms(400)
    while any_key():
        time.sleep_ms(20)
    while not any_key():
        time.sleep_ms(20)
    time.sleep_ms(150)
