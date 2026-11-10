# -*- coding: utf-8 -*-
"""MYBIT 曲库播放器 player.py
A 上一首 / B 下一首（切到即播）  长按A 播放暂停  长按B 循环开关  A+B 停止
网页管理：浏览器打开 OLED 第5行地址，可上传/删除/改名/调序/点播
曲库 /songs/*.mel   格式见 方案-曲库播放器.md
约束（实测）：music.play 只吃字符串元组；阻塞不可中断 -> 分段播；无 I2S 只能单音旋律
"""
import os
import time
import gc
from npython import oled, button, led, wifi, music
import web

SONG_DIR = '/songs'
WEB_PORT = 80
SEG_MS = 380
SEG_MAX = 8

S = {'files': [], 'idx': 0, 'name': '', 'bpm': 120, 'loop': 0,
     'toks': [], 'pos': 0, 'pticks': 0, 'total': 0,
     'playing': False, 'paused': False, 'loopall': 0,
     'need_load': True, 'ip': '', 'ap': False}


# ---------------- 曲库 ----------------
def ensure_dir():
    for p in (SONG_DIR, '/www'):
        try:
            os.listdir(p)
        except Exception:
            try:
                os.mkdir(p)
            except Exception:
                pass


def list_songs():
    try:
        names = os.listdir(SONG_DIR)
    except Exception:
        return []
    files = []
    for n in names:
        if n.lower().endswith('.mel'):
            files.append(n)
    files.sort()
    order = []
    try:
        fp = open(SONG_DIR + '/order.txt', 'r')
        txt = fp.read()
        fp.close()
        for line in txt.split('\n'):
            line = line.strip()
            if line and (line in files) and (line not in order):
                order.append(line)
    except Exception:
        pass
    for f in files:
        if f not in order:
            order.append(f)
    return order


def norm_token(tok):
    """c4:2 / c#5 / e / r:4 / 0:2 / bb3:8 -> (token, ticks)；非法 None"""
    t = tok.lower().strip()
    if not t:
        return None
    dur = 1
    if ':' in t:
        a, _, b = t.partition(':')
        if not b.isdigit():
            return None
        dur = int(b)
        if dur < 1:
            dur = 1
        if dur > 64:
            dur = 64
        t = a
    if t in ('r', '0', '-', '.'):
        return ('r:%d' % dur, dur)
    if not t:
        return None
    h = t[0]
    if h not in 'abcdefg':
        return None
    i = 1
    acc = ''
    if i < len(t) and (t[i] == '#' or t[i] == 'b'):
        acc = t[i]
        i += 1
    oc = ''
    while i < len(t) and t[i].isdigit():
        oc += t[i]
        i += 1
    if i != len(t):
        return None
    return (h + acc + oc + ':' + str(dur), dur)


def parse_mel(txt, fallback):
    name = fallback
    bpm = 120
    loop = 0
    toks = []
    for line in txt.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line[0] == '#':
            body = line[1:].strip()
            low = body.lower()
            if low.startswith('name:'):
                nm = body[5:].strip()
                if nm:
                    name = nm
            elif low.startswith('bpm:'):
                try:
                    bpm = int(float(body[4:].strip()))
                except Exception:
                    bpm = 120
            elif low.startswith('loop:'):
                v = body[5:].strip().lower()
                loop = 1 if v in ('1', 'on', 'yes', 'true') else 0
            continue
        for raw in line.replace(',', ' ').split():
            nt = norm_token(raw)
            if nt:
                toks.append(nt)
    if bpm < 30:
        bpm = 30
    if bpm > 400:
        bpm = 400
    total = 0
    for tk in toks:
        total += tk[1]
    return name, bpm, loop, toks, total


def load_current():
    files = S['files']
    S['pticks'] = 0
    S['pos'] = 0
    if not files:
        S['name'] = '-'
        S['toks'] = []
        S['total'] = 0
        S['playing'] = False
        S['need_load'] = False
        return
    if S['idx'] >= len(files):
        S['idx'] = 0
    if S['idx'] < 0:
        S['idx'] = len(files) - 1
    fname = files[S['idx']]
    try:
        fp = open(SONG_DIR + '/' + fname, 'r')
        txt = fp.read()
        fp.close()
    except Exception as e:
        print('load err', fname, e)
        S['toks'] = []
        S['name'] = fname
        S['total'] = 0
        S['need_load'] = False
        return
    name, bpm, loop, toks, total = parse_mel(txt, fname)
    S['name'] = name
    S['bpm'] = bpm
    S['loop'] = loop
    S['toks'] = toks
    S['total'] = total
    S['need_load'] = False
    try:
        music.set_tempo(bpm=bpm)
    except Exception:
        pass
    print('load', fname, 'notes', len(toks), 'bpm', bpm)


def rescan():
    S['files'] = list_songs()
    if S['idx'] >= len(S['files']):
        S['idx'] = 0
    S['need_load'] = True


# ---------------- 播放 ----------------
def stop_play():
    S['playing'] = False
    S['paused'] = False
    try:
        music.stop()
    except Exception:
        pass
    try:
        led.off()
    except Exception:
        pass


def goto(idx, play=True):
    if not S['files']:
        return
    S['idx'] = idx % len(S['files'])
    S['need_load'] = True
    S['pos'] = 0
    S['pticks'] = 0
    S['paused'] = False
    S['playing'] = bool(play)
    try:
        if play:
            led.on()
        else:
            led.off()
    except Exception:
        pass


def play_chunk(limit_ms=4000):
    """播放一段。切段策略：优先在休止符处切（间隙藏在静音里），否则按 limit_ms 硬切。
    music.play 本身时序精度 99.7%（实测 164 tick / 9840ms 理论 / 9871ms 实际），
    所以段越长越连；段间只允许做按键扫描，绝不刷 OLED（单次刷新实测 1153ms）。"""
    if S['need_load']:
        load_current()
    toks = S['toks']
    if not toks:
        stop_play()
        return
    if S['pos'] >= len(toks):
        if S['loop']:
            S['pos'] = 0
            S['pticks'] = 0
        elif S['loopall']:
            goto(S['idx'] + 1, True)
            return
        else:
            stop_play()
            return
    tick_ms = 60000.0 / (S['bpm'] * 4.0)
    seg = []
    acc = 0.0
    st = 0
    i = S['pos']
    n = len(toks)
    while i < n:
        tk = toks[i]
        # 休止符开头切段：段间那点开销正好被休止吞掉，听不出来
        if seg and tk[0][0] == 'r' and acc >= limit_ms * 0.45:
            break
        m = tk[1] * tick_ms
        if seg and (acc + m > limit_ms or len(seg) >= 64):
            break
        seg.append(tk[0])
        acc += m
        st += tk[1]
        i += 1
        if acc >= limit_ms:
            break
    if not seg:
        stop_play()
        return
    S['pos'] = i
    S['pticks'] += st
    try:
        music.play(tuple(seg))
    except Exception as e:
        print('play err', e)
        stop_play()


def fmt_time(ticks, bpm):
    sec = int(ticks * (60000.0 / (bpm * 4.0)) / 1000.0)
    return '%d:%02d' % (sec // 60, sec % 60)


# ---------------- 按键 ----------------
K = {'ap': 0, 'at': 0, 'al': False, 'bp': 0, 'bt': 0, 'bl': False, 'both': False}


def keys_tick():
    a = 1 if button.get_a() == 1 else 0
    b = 1 if button.get_b() == 1 else 0
    now = time.ticks_ms()

    if a and b and not K['both']:
        K['both'] = True
        K['ap'] = 1
        K['bp'] = 1
        K['al'] = True
        K['bl'] = True
        stop_play()
    if not (a and b):
        K['both'] = False

    if a and not K['ap']:
        K['at'] = now
        K['al'] = False
    elif a and (not K['al']) and time.ticks_diff(now, K['at']) > 700:
        K['al'] = True
        if S['files']:
            if S['playing'] and not S['paused']:
                S['paused'] = True
                led.off()
            elif S['paused']:
                S['paused'] = False
                led.on()
            else:
                goto(S['idx'], True)
    elif (not a) and K['ap']:
        if not K['al'] and S['files']:
            goto(S['idx'] - 1, True)
    K['ap'] = a

    if b and not K['bp']:
        K['bt'] = now
        K['bl'] = False
    elif b and (not K['bl']) and time.ticks_diff(now, K['bt']) > 700:
        K['bl'] = True
        S['loopall'] = 0 if S['loopall'] else 1
    elif (not b) and K['bp']:
        if not K['bl'] and S['files']:
            goto(S['idx'] + 1, True)
    K['bp'] = b


# ---------------- 显示 ----------------
_ui_t = 0


def ui_force():
    global _ui_t
    _ui_t = 0


def ui_tick():
    global _ui_t
    now = time.ticks_ms()
    if _ui_t and time.ticks_diff(now, _ui_t) < 250:
        return
    _ui_t = now
    n = len(S['files'])
    idx = (S['idx'] + 1) if n else 0
    if S['playing']:
        state = '暂停' if S['paused'] else '播放'
    else:
        state = '停止'
    name = S['name'] or '-'
    if len(name) > 10:
        name = name[:10]
    t4 = 'AP MYBIT-SONG' if S['ap'] else ('WIFI已连' if S['ip'] else '无网络')
    t5 = ('IP ' + S['ip']) if S['ip'] else 'USB-SERIAL'
    try:
        oled.print(1, 1, '%d/%d %s' % (idx, n, name), 1)
        oled.print(1, 2, '%s %s/%s' % (state, fmt_time(S['pticks'], S['bpm']),
                                       fmt_time(S['total'], S['bpm'])), 1)
        oled.print(1, 3, 'bpm%d 循环:%s' % (S['bpm'], '开' if S['loopall'] else '关'), 1)
        oled.print(1, 4, t4, 1)
        oled.print(1, 5, t5, 1)
        oled.show()
    except Exception as e:
        print('oled err', e)


def boot_ui(l1, l2):
    try:
        oled.fill(0)
        oled.print(1, 1, ' MYBIT 曲库播放器', 1)
        if l1:
            oled.print(1, 2, l1, 1)
        if l2:
            oled.print(1, 3, l2, 1)
        oled.show()
    except Exception:
        pass


# ---------------- 网络 ----------------
def net_up():
    ssid = None
    pw = ''
    try:
        fp = open('/wifi.txt', 'r')
        lines = fp.read().split('\n')
        fp.close()
        ssid = lines[0].strip()
        if len(lines) > 1:
            pw = lines[1].strip()
    except Exception:
        pass
    if ssid:
        boot_ui('连接 ' + ssid[:10], '请稍候...')
        try:
            ip = wifi.connect(ssid, pw)
            ip = str(ip) if ip else ''
            if ip and ip != '0.0.0.0':
                S['ip'] = ip
                S['ap'] = False
                print('STA ip', ip)
                return
        except Exception as e:
            print('sta err', e)
    try:
        wifi.enable_AP('MYBIT-SONG', 'YOUR_WIFI_PASSWORD')
        S['ap'] = True
        ip = 'BOARD_AP_IP'
        try:
            import network
            ip = network.WLAN(network.AP_IF).ifconfig()[0]
        except Exception:
            pass
        S['ip'] = ip
        print('AP up')
    except Exception as e:
        print('ap err', e)


# ---------------- 主循环 ----------------
def main():
    gc.collect()
    ensure_dir()
    boot_ui('启动中...', '')
    rescan()
    boot_ui('曲库 %d 首' % len(S['files']), '网络初始化...')
    try:
        net_up()
    except Exception as e:
        print('net err', e)
    w = web.Web(WEB_PORT, S, {'goto': goto, 'stop': stop_play,
                              'rescan': rescan, 'parse': parse_mel})
    print('WEB', S['ip'], WEB_PORT, 'songs', len(S['files']))
    # 开机自动播放列表第一首
    goto(0, True)
    ui_force()
    last = time.ticks_ms()
    last_st = None
    while True:
        keys_tick()
        if S['playing'] and not S['paused']:
            # 播放中：只在状态真变了才刷屏，其余时间一次都不碰 OLED
            st = (S['idx'], S['paused'], S['loopall'])
            if st != last_st:
                last_st = st
                ui_tick()
            play_chunk(4000 if w.cli is None else 600)
            w.tick(2 if w.cli is None else 10)
        else:
            last_st = None
            w.tick(15, 0.02)
            time.sleep_ms(4)
            ui_tick()
        if time.ticks_diff(time.ticks_ms(), last) > 15000:
            last = time.ticks_ms()
            gc.collect()


if __name__ == '__main__':
    main()
