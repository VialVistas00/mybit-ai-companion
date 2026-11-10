# -*- coding: utf-8 -*-
# ============================================================================
#   飞机打外星人  PLANE vs ALIENS        MYBIT 信息科技实验板 (ESP32/MicroPython)
# ----------------------------------------------------------------------------
#   操作 : A 键 = 左移        B 键 = 右移      （按住不放持续移动）
#          飞机自动连射，不用按射击键
#
#   事件反馈 :
#     每次开火            -> 高频"啾"声
#     打中外星人          -> 短促击中音 + 机身闪一下方框 + 灯闪绿
#     外星人血量打光      -> 左右 RGB 亮绿灯 + 三段上扬击败音效 + 记 100 分
#     飞机被外星人击中    -> 左右 RGB 亮红灯 + 下坠受击音效 + 掉 1 条命 + 无敌闪烁
#     全场外星人清空      -> RGB 七色交替闪烁 + 胜利旋律
#
#   规则 : 飞机 3 条命；外星人 A_HP 点血（现为 1 血，一发就爆）；清空一盘进下一关
#
#   性能备忘（都是在这块板子上实测的）:
#     oled.print()        143 ms/次   <- 千万别在游戏循环里用
#     oled.fill_rect()    ~1.4 ms/次  <- 是原生 framebuf 的 40 倍慢
#     oled.show()         38 ms/帧
#     oled.blit()         0.76 ms/次
#     framebuf.fill_rect  0.02~0.35 ms，framebuf.blit 0.07 ms
#     music.pitch()       35 ms/次（固定开销）-> 改用 PWM 直驱蜂鸣器 6 ms/次
#   所以：全部绘制直接读写 oled 的显存 framebuf，再用自写的整页 I2C 刷屏。
# ============================================================================
from npython import *
import framebuf
import time
import gc

try:
    import urandom as rnd
except ImportError:
    import random as rnd

# 自测开关：>0 表示只跑 N 帧就退出并打印统计（调试用）。正常玩保持 0。
AUTO_FRAMES = 0

# ---------------- 屏幕 ----------------
SCR_W = 128
SCR_H = 64
HUD_H = 8
PLAY_Y = 10                 # 顶上一行状态字占 0~7

# ---------------- 飞机 ----------------
P_W = 9
P_H = 7
P_Y = 55
P_SPD = 85.0                # 像素/秒
P_NUDGE = 3                 # 点一下键的即刻位移，手感更跟手

# ---------------- 我方子弹 ----------------
B_SPD = 190.0
B_GAP = 160                 # 自动射击间隔 ms
B_MAX = 4

# ---------------- 外星人 ----------------
A_HP = 1                    # 外星人血量（1 = 一发入魂）
G_COLS = 5
G_ROWS = 2
A_W = 9
A_H = 7
G_DX = 24
G_DY = 12
G_X0 = 7
G_Y0 = 14
FORM_SPD = 5.5              # 编队基础横移速度 像素/秒
FORM_ACC = 0.8              # 每减少一个外星人加快多少
FORM_DROP = 3.0             # 撞到左右边界后整体下压多少像素

# ---------------- 敌方炸弹 ----------------
E_SPD = 42.0
E_GAP = 1200                # 投弹间隔 ms
E_MAX = 2

INVUL_MS = 1500             # 被击中后的无敌时间
FRAME_MS = 8                # 帧节流（刷屏本身 ~27ms，这里只防忙死）

# ============================ 显存 ============================
# 这块板的 0.96" OLED 显存是 SSD1306 的竖向排列格式 MONO_VLSB（一页 8 行、每列 1 字节）。
# 直接拿 oled.buffer 做一块原生 framebuf：所有绘制都走 C 实现，比 oled.xxx() 快 20~40 倍。
# 注意：格式必须和屏一致，用 HLSB 会刷出一屏乱点。
OLED_FMT = framebuf.MONO_VLSB
FB = framebuf.FrameBuffer(oled.buffer, SCR_W, SCR_H, OLED_FMT)

# ============================ 精灵数据 ============================
# '#' = 亮点，'.' = 空
PLANE_ROWS = (
    "....#....",
    "...#.#...",
    "..##.##..",
    ".#######.",
    "#########",
    "##.###.##",
    "..#...#..",
)

# 外星人：满血两帧动画 / 二血 / 一血（越打越破）
A1_ROWS = (
    "..#...#..",
    "...#.#...",
    "..#####..",
    ".##.#.##.",
    "#########",
    "#.#####.#",
    "#.#...#.#",
)
A2_ROWS = (
    ".#.....#.",
    "..#...#..",
    ".#######.",
    "##.###.##",
    "#########",
    ".#######.",
    "..#...#..",
)
A3_ROWS = (
    ".........",
    "..#...#..",
    "....#....",
    "..#.#.#..",
    "...#.#...",
    ".........",
    ".........",
)


def _mk_sprite(rows):
    """字符画 -> framebuf 位块（与屏幕同为 MONO_VLSB，blit 走快速通道），绘制时一次搞定。"""
    w = len(rows[0])
    h = len(rows)
    buf = bytearray(w * ((h + 7) // 8))
    fb = framebuf.FrameBuffer(buf, w, h, OLED_FMT)
    for y in range(h):
        row = rows[y]
        x = 0
        n = len(row)
        while x < n:
            if row[x] == '#':
                s = x
                while x < n and row[x] == '#':
                    x += 1
                fb.fill_rect(s, y, x - s, 1, 1)
            else:
                x += 1
    return fb


SP_PLANE = _mk_sprite(PLANE_ROWS)
SP_A1 = _mk_sprite(A1_ROWS)
SP_A2 = _mk_sprite(A2_ROWS)
SP_A3 = _mk_sprite(A3_ROWS)

# ============================ 刷屏 ============================
PAGES = len(oled.buffer) >> 7
_CMD = bytearray(4)
_PGD = bytearray(129)
_I2C = oled.i2c
_ADDR = oled.addr
_MV = memoryview(oled.buffer)


def _fast_show(p0=0):
    """官方 show() 逐 16 字节小包发 1024 字节要 38ms；整页发只要 ~27ms。"""
    for p in range(p0, PAGES):
        _CMD[0] = 0x00
        _CMD[1] = 0xB0 + p
        _CMD[2] = 0x00
        _CMD[3] = 0x10
        _I2C.writeto(_ADDR, _CMD)
        c = p << 7
        _PGD[0] = 0x40
        _PGD[1:] = _MV[c:c + 128]
        _I2C.writeto(_ADDR, _PGD)


def _init_show():
    """优先用快速刷屏，失败就退回官方 show()。"""
    try:
        _fast_show(0)
        return _fast_show
    except Exception:
        try:
            oled.show()
        except Exception:
            pass
        return oled.show


SHOW = _init_show()

# ============================ 绘图 ============================
def rfill(x, y, w, h, c=1):
    """带裁剪的 fill_rect，坐标越界也不会把驱动写崩。"""
    if x < 0:
        w += x
        x = 0
    if y < 0:
        h += y
        y = 0
    if x + w > SCR_W:
        w = SCR_W - x
    if y + h > SCR_H:
        h = SCR_H - y
    if w > 0 and h > 0:
        FB.fill_rect(int(x), int(y), int(w), int(h), c)


def text(s, x, y):
    FB.text(s, int(x), int(y), 1)


# ============================ 灯 ============================
GL_T = 0


def lights_off():
    try:
        rgb.write_left(0, 0, 0)
        rgb.write_right(0, 0, 0)
    except Exception:
        pass


def set_light(r, g, b, ms):
    """点亮左右 RGB，保持 ms 毫秒后自动熄灭（在帧循环里倒计时）。"""
    global GL_T
    try:
        rgb.write_left(r, g, b)
        rgb.write_right(r, g, b)
    except Exception:
        pass
    GL_T = ms


# ============================ 声音 ============================
# 实测：music.pitch(2600, 6) 一次要 35ms（固定开销约 30ms），每 0.16 秒响一次会把帧率拖死。
# 改成直接 PWM 驱动板载无源蜂鸣器：同样的 6ms 音只花 6ms，而且更响。
VOL = 320                    # PWM 占空比 0~1023，越大越响
_PWM = None
try:
    import machine
    _PWM = machine.PWM(beeppin)
    _PWM.duty(0)
except Exception:
    _PWM = None


def sfx(f, ms):
    global _PWM
    if _PWM is not None:
        try:
            _PWM.freq(int(f))
            _PWM.duty(VOL)
            time.sleep_ms(int(ms))
            _PWM.duty(0)
            return
        except Exception:
            _PWM = None
    try:
        music.pitch(int(f), int(ms))
    except Exception:
        pass


def sfx_big(f, ms, vol):
    """重音（击败 / 受击 / 胜利），音量单独给。"""
    global _PWM
    if _PWM is not None:
        try:
            _PWM.freq(int(f))
            _PWM.duty(vol)
            time.sleep_ms(int(ms))
            _PWM.duty(0)
            return
        except Exception:
            _PWM = None
    sfx(f, ms)


def sfx_shoot():
    sfx(2600, 5)


def sfx_dmg():
    sfx(1500, 5)


def sfx_kill():
    sfx_big(1100, 14, 520)
    sfx_big(1500, 14, 520)
    sfx_big(2050, 22, 520)


def sfx_hit():
    sfx_big(720, 32, 560)
    sfx_big(520, 32, 560)
    sfx_big(340, 42, 560)
    sfx_big(200, 52, 560)


def sfx_dead():
    sfx_big(600, 75, 560)
    sfx_big(470, 75, 560)
    sfx_big(350, 75, 560)
    sfx_big(240, 110, 560)
    sfx_big(150, 160, 560)


def sfx_start():
    sfx(700, 18)
    sfx(1000, 18)
    sfx(1400, 26)


# ============================ 通用 ============================
def any_key():
    return (button.get_a() == 1) or (button.get_b() == 1)


def wait_key():
    if AUTO_FRAMES > 0:
        return
    time.sleep_ms(200)
    while any_key():
        time.sleep_ms(20)
    while not any_key():
        time.sleep_ms(20)
    time.sleep_ms(140)


def title_screen():
    FB.fill(0)
    text("PLANE vs ALIEN", 4, 2)
    text("A = LEFT", 4, 16)
    text("B = RIGHT", 4, 26)
    text("AUTO  FIRE", 4, 36)
    text("PRESS A / B", 4, 48)
    FB.blit(SP_PLANE, 100, 18)
    FB.blit(SP_A1, 100, 34)
    SHOW(0)


def over_screen(score, wave):
    FB.fill(0)
    text("GAME  OVER", 16, 2)
    text("SCORE %d" % score, 8, 16)
    text("WAVE %d" % wave, 8, 26)
    text("A/B RESTART", 8, 40)
    SHOW(0)


def clear_screen(score, wave):
    FB.fill(0)
    text("WAVE CLEAR!", 16, 2)
    text("SCORE %d" % score, 8, 16)
    text("NEXT %d" % (wave + 1), 8, 28)
    text("A/B  NEXT", 8, 42)
    SHOW(0)


# ============================ 胜利 / 失败 演出 ============================
RAINBOW = ((255, 0, 0), (255, 140, 0), (255, 255, 0), (0, 255, 60),
           (0, 220, 255), (40, 80, 255), (190, 0, 255))
VICTORY_NOTES = (523, 659, 784, 1047, 880, 1047, 1319, 1568)


def victory_seq():
    """RGB 七色交替 + 胜利旋律：每换一个颜色响一个音，灯和音同步。"""
    global GL_T
    i = 0
    n = len(VICTORY_NOTES)
    while i < n * 2:
        c1 = RAINBOW[i % 7]
        c2 = RAINBOW[(i + 3) % 7]
        try:
            rgb.write_left(c1[0], c1[1], c1[2])
            rgb.write_right(c2[0], c2[1], c2[2])
        except Exception:
            pass
        sfx_big(VICTORY_NOTES[i % n], 75, 480)
        i += 1
    k = 0
    while k < 6:                     # 收尾六连闪
        c = RAINBOW[k % 7]
        try:
            rgb.write_left(c[0], c[1], c[2])
            rgb.write_right(c[0], c[1], c[2])
        except Exception:
            pass
        sfx_big(1568 if (k & 1) == 0 else 1047, 55, 480)
        k += 1
    lights_off()
    GL_T = 0


def lose_seq():
    """失败：红色左右交替 + 下坠音效。"""
    global GL_T
    try:
        rgb.write_left(255, 0, 0)
        rgb.write_right(0, 0, 0)
    except Exception:
        pass
    sfx_big(700, 85, 560)
    try:
        rgb.write_left(0, 0, 0)
        rgb.write_right(255, 0, 0)
    except Exception:
        pass
    sfx_big(560, 85, 560)
    try:
        rgb.write_left(255, 0, 0)
        rgb.write_right(255, 0, 0)
    except Exception:
        pass
    sfx_dead()
    lights_off()
    GL_T = 0


# ============================ 一局 ============================
SCORE = 0
LIVES = 3
WAVE = 1
FRAMES = 0


def run_wave():
    """跑一局。返回 0=过关  1=阵亡  2=自测帧数跑完。"""
    global SCORE, LIVES, FRAMES, GL_T

    # 外星人：[列, 行, 血量, 闪框剩余 ms]
    aliens = []
    for r in range(G_ROWS):
        for c in range(G_COLS):
            aliens.append([c, r, A_HP, 0])
    total = len(aliens)
    alive = total

    form_x = 0.0
    form_y = 0.0
    fdir = 1
    px = float((SCR_W - P_W) // 2)

    bullets = []
    bombs = []
    expl = []

    invul = 0
    fire_t = B_GAP
    bomb_t = 300
    over = 0
    ka_prev = 0
    kb_prev = 0
    hud_dirty = 1

    FB.fill(0)
    gc.collect()
    text("SC%05d L%d W%d" % (SCORE, LIVES, WAVE), 0, 1)
    hud_s = SCORE
    hud_l = LIVES
    hud_w = WAVE
    SHOW(0)

    GL_T = 0
    last = time.ticks_ms()

    while True:
        FRAMES += 1
        now = time.ticks_ms()
        dt = time.ticks_diff(now, last)
        last = now
        if dt < 0:
            dt = 0
        if dt > 120:            # 音效阻塞后不允许物理瞬移
            dt = 120

        # ---------------- 1. 输入 ----------------
        ka = 1 if button.get_a() else 0
        kb = 1 if button.get_b() else 0
        if ka:
            px -= P_SPD * dt / 1000.0
        if kb:
            px += P_SPD * dt / 1000.0
        if ka and not ka_prev:          # 点一下的即刻位移
            px -= P_NUDGE
        if kb and not kb_prev:
            px += P_NUDGE
        ka_prev = ka
        kb_prev = kb
        if px < 0:
            px = 0.0
        elif px > SCR_W - P_W:
            px = float(SCR_W - P_W)

        # ---------------- 2. 自动开火 ----------------
        fire_t += dt
        if fire_t >= B_GAP and len(bullets) < B_MAX:
            fire_t = 0
            bullets.append([int(px) + 4, float(P_Y - 3)])
            sfx_shoot()

        # ---------------- 3. 移动子弹 ----------------
        i = len(bullets) - 1
        while i >= 0:
            b = bullets[i]
            b[1] -= B_SPD * dt / 1000.0
            if b[1] < PLAY_Y:
                bullets.pop(i)
            i -= 1

        # ---------------- 4. 编队移动 ----------------
        spd = FORM_SPD + (total - alive) * FORM_ACC
        form_x += fdir * spd * dt / 1000.0
        if alive > 0:
            minx = 999
            maxx = -999
            for a in aliens:
                if a[2] <= 0:
                    continue
                ax = G_X0 + a[0] * G_DX + form_x
                if ax < minx:
                    minx = ax
                if ax + A_W - 1 > maxx:
                    maxx = ax + A_W - 1
            if maxx >= SCR_W - 1:
                form_x -= (maxx - (SCR_W - 1))
                fdir = -1
                form_y += FORM_DROP
            elif minx <= 0:
                form_x -= minx
                fdir = 1
                form_y += FORM_DROP

        # ---------------- 5. 敌方投弹 ----------------
        bomb_t += dt
        if bomb_t >= E_GAP and len(bombs) < E_MAX and alive > 0:
            bomb_t = 0
            pick = None
            for k in range(total):
                a = aliens[rnd.getrandbits(8) % total]
                if a[2] > 0:
                    pick = a
                    break
            if pick is not None:
                bombs.append([G_X0 + pick[0] * G_DX + form_x + 4,
                              G_Y0 + pick[1] * G_DY + form_y + A_H])

        # ---------------- 6. 移动敌弹 ----------------
        i = len(bombs) - 1
        while i >= 0:
            b = bombs[i]
            b[1] += E_SPD * dt / 1000.0
            if b[1] > SCR_H:
                bombs.pop(i)
            i -= 1

        # ---------------- 7. 我方子弹打外星人 ----------------
        i = len(bullets) - 1
        while i >= 0:
            b = bullets[i]
            bx = int(b[0])
            by = int(b[1])
            hit = 0
            for a in aliens:
                if a[2] <= 0:
                    continue
                ax = int(G_X0 + a[0] * G_DX + form_x)
                ay = int(G_Y0 + a[1] * G_DY + form_y)
                if bx >= ax and bx <= ax + A_W - 1 and by <= ay + A_H - 1 and by + 2 >= ay:
                    hit = 1
                    a[2] -= 1
                    a[3] = 70
                    if a[2] <= 0:
                        # ===== 击败外星人：绿灯 + 击败音效 =====
                        alive -= 1
                        SCORE += 100
                        expl.append([ax + 4, ay + 3, 0])
                        set_light(0, 255, 0, 170)
                        sfx_kill()
                    else:
                        set_light(0, 200, 0, 80)
                        sfx_dmg()
                    break
            if hit:
                bullets.pop(i)
            i -= 1

        if alive <= 0:
            break

        # ---------------- 8. 飞机被击中 ----------------
        if invul <= 0:
            prx = int(px)
            hitme = 0
            i = len(bombs) - 1
            while i >= 0:
                b = bombs[i]
                by = int(b[1])
                if by + 2 >= P_Y and by <= P_Y + P_H and b[0] >= prx - 1 and b[0] <= prx + P_W:
                    bombs.pop(i)
                    hitme = 1
                    break
                i -= 1
            if not hitme:
                for a in aliens:
                    if a[2] <= 0:
                        continue
                    ax = int(G_X0 + a[0] * G_DX + form_x)
                    ay = int(G_Y0 + a[1] * G_DY + form_y)
                    if ax < prx + P_W and prx < ax + A_W and ay < P_Y + P_H and P_Y < ay + A_H:
                        hitme = 1
                        break
            if hitme:
                # ===== 飞机被击中：红灯 + 受击音效 =====
                LIVES -= 1
                invul = INVUL_MS
                bombs = []
                set_light(255, 0, 0, 520)
                sfx_hit()
                if LIVES <= 0:
                    over = 1
                    break

        # ---------------- 9. 绘制 ----------------
        if invul > 0:
            invul -= dt

        # HUD 只在数值变化时重排字符串（MicroPython 里 % 格式化一次要 5ms，不能每帧做）
        if SCORE != hud_s or LIVES != hud_l or WAVE != hud_w:
            hud_s = SCORE
            hud_l = LIVES
            hud_w = WAVE
            rfill(0, 0, SCR_W, HUD_H, 0)
            text("SC%05d L%d W%d" % (SCORE, LIVES, WAVE), 0, 1)
            hud_dirty = 1

        rfill(0, PLAY_Y, SCR_W, SCR_H - PLAY_Y, 0)      # 清游戏区

        anim = (FRAMES >> 3) & 1
        for a in aliens:
            if a[2] <= 0:
                continue
            ax = int(G_X0 + a[0] * G_DX + form_x)
            ay = int(G_Y0 + a[1] * G_DY + form_y)
            if a[3] > 0:
                a[3] -= dt
                FB.rect(ax, ay, A_W, A_H, 1)            # 被打中：闪方框
            elif a[2] >= A_HP:
                FB.blit(SP_A1 if anim == 0 else SP_A2, ax, ay)
            elif a[2] >= 2:
                FB.blit(SP_A2, ax, ay)
            else:
                FB.blit(SP_A3, ax, ay)

        for b in bombs:                                 # 敌弹：小十字
            rfill(b[0], b[1], 3, 1, 1)
            rfill(b[0] + 1, b[1] + 1, 1, 2, 1)

        for b in bullets:                               # 我方子弹
            rfill(b[0], b[1], 1, 3, 1)

        i = len(expl) - 1
        while i >= 0:
            e = expl[i]
            e[2] += dt
            if e[2] > 220:
                expl.pop(i)
            else:
                r = 1 + e[2] // 55
                rfill(e[0] - r, e[1], 2 * r + 1, 1, 1)
                rfill(e[0], e[1] - r, 1, 2 * r + 1, 1)
            i -= 1

        if invul <= 0 or ((FRAMES >> 1) & 1):           # 无敌期闪烁
            FB.blit(SP_PLANE, int(px), P_Y)

        if GL_T > 0:
            GL_T -= dt
            if GL_T <= 0:
                lights_off()

        if hud_dirty:
            SHOW(0)
            hud_dirty = 0
        else:
            SHOW(1)                                     # 第 0 页没变，省一次传输

        # ---------------- 10. 帧节奏 / 自测 ------------------
        spend = time.ticks_diff(time.ticks_ms(), now)
        if spend < FRAME_MS:
            time.sleep_ms(FRAME_MS - spend)

        if FRAMES % 900 == 0:
            gc.collect()

        if AUTO_FRAMES:
            if FRAMES >= AUTO_FRAMES:
                over = 2
                break

    if over == 2:
        return 2
    if over == 1:
        return 1
    return 0


# ============================ 主流程 ============================
def main():
    global SCORE, LIVES, WAVE, FRAMES

    gc.collect()
    FRAMES = 0
    SCORE = 0
    LIVES = 3
    WAVE = 1
    t0 = time.ticks_ms()

    lights_off()
    led.on()
    sfx_start()
    title_screen()
    wait_key()

    while True:
        r = run_wave()
        if r == 2:
            el = time.ticks_diff(time.ticks_ms(), t0)
            print("SELFTEST DONE frames=%d ms=%d fps=%.1f score=%d wave=%d lives=%d"
                  % (FRAMES, el, FRAMES * 1000.0 / (el or 1), SCORE, WAVE, LIVES))
            lights_off()
            return
        if r == 0:
            # ===== 全场清空：七色交替 + 胜利音效 =====
            FB.fill(0)
            text("WAVE CLEAR!", 16, 4)
            text("SCORE %d" % SCORE, 12, 20)
            SHOW(0)
            victory_seq()
            clear_screen(SCORE, WAVE)
            wait_key()
            WAVE += 1
            LIVES = 3
        else:
            FB.fill(0)
            text("GAME OVER", 20, 6)
            SHOW(0)
            lose_seq()
            over_screen(SCORE, WAVE)
            wait_key()
            SCORE = 0
            LIVES = 3
            WAVE = 1
        led.on()
        lights_off()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        try:
            import sys
            sys.print_exception(e)
        except Exception:
            print('ERR', e)
        try:
            FB.fill(0)
            text("PROGRAM ERR", 12, 2)
            text(str(e)[:16], 0, 20)
            SHOW(0)
        except Exception:
            pass
