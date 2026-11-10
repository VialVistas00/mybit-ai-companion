# 附加项目

这两个是在做 AI 学伴过程中顺带完成的板子项目，跟主线无关，但都完整可玩。

| 项目 | 目录 | 一句话 |
|---|---|---|
| 飞机打外星人 | [飞机打外星人/](飞机打外星人/) | 竖版射击游戏，全程直写显存，25fps |
| 曲库播放器 | [曲库播放器/](曲库播放器/) | 板子放歌 + 网页管理曲库 |

两个项目共用同一块板子（MYBIT / ESP32 / npython v1.06.5），烧录方式见 [../docs/开发历程.md](../docs/开发历程.md)。

---

## 飞机打外星人

`plane_game.py`（烧录时改名成 `main.py`）

### 玩法

| 按键 | 作用 |
|---|---|
| A | 左移（按住持续移动） |
| B | 右移 |

飞机**自动连射**，不用按射击键。3 条命，外星人一发就爆，清空一关进下一关。

### 事件反馈

| 事件 | 反馈 |
|---|---|
| 每次开火 | 高频「啾」声 |
| 打中外星人 | 短促击中音 + 机身闪方框 + 灯闪绿 |
| 击杀 | 左右 RGB 亮绿 + 三段上扬音 + 记 100 分 |
| 被击中 | 左右 RGB 亮红 + 下坠受击音 + 掉 1 命 + 无敌闪烁 |
| 清场 | RGB 七色交替 + 胜利旋律 |

### 性能设计（关键）

作者在文件头注释里写明了实测数据，这是这个项目最值得看的地方：

```
oled.print()        143 ms/次   <- 千万别在游戏循环里用
oled.fill_rect()    ~1.4 ms/次  <- 是原生 framebuf 的 40 倍慢
oled.show()         38 ms/帧
oled.blit()         0.76 ms/次
framebuf.fill_rect  0.02~0.35 ms
framebuf.blit       0.07 ms
music.pitch()       35 ms/次（固定开销）
PWM 直驱蜂鸣器       6 ms/次
```

**所以整个游戏绕开了 `oled.*` 绘图 API**：全部直接读写 OLED 的显存 framebuf，再用自写的整页 I2C 刷屏。音效也从 `music.pitch()` 换成 PWM 直接驱动蜂鸣器，把 35ms 的开销压到 6ms。

这就是它能跑到 25fps 的原因。

---

## 曲库播放器

`player.py` + `web.py` + `songs/` + `www/`

### 先说结论：这块板放不了 MP3

方案文档里实测得很清楚：

| 能力 | 实测结果 |
|---|---|
| `music.play(元组)` | ✅ 只吃字符串元组，如 `('c4:2','e4:2','r:4')` |
| `music.play([('C4',4),...])` | ❌ **硬崩** `LoadProhibited`，板子自动重启 |
| `machine.I2S` | ❌ 不存在 |
| `machine.DAC` | ✅ 可写，但 Timer 最大 1kHz，喂不上采样率 |
| 存储 | 文件系统 2 MB，空闲 2,023,424 B |

**没有 I2S，Timer 也只能到 1kHz，所以软播 WAV 不可行。**

「外部歌曲」= 转成 `.mel` 音符谱文件，音色是经典方波电子琴。想听原曲音质只能加 DFPlayer 模块。

### 用法

| 操作 | 效果 |
|---|---|
| A | 上一首（切到即播） |
| B | 下一首 |
| 长按 A | 播放 / 暂停 |
| 长按 B | 循环开关 |
| A+B | 停止 |

OLED 第 5 行显示网页地址，浏览器打开后可**上传 / 删除 / 改名 / 调序 / 点播**。

### 曲库格式

`.mel` 文件就是一行音符序列：

```
c4:2 e4:2 g4:2 r:4
```

- 音名：`c4` / `c#5`，省略八度 `e` 表示继承前一个八度
- 休止：`r:4` 或 `0:4`
- 时长：`:n` = n tick，**bpm120 时 1 tick = 125 ms**

实测：`:1`→130ms、`:4`→504ms、`:8`→1006ms，bpm240 时全部减半。

### 内置曲库（29 首）

27 首是从固件内置 melody 里导出的：

```
baddy  ba_ding  birthday  blues  cai_yun_zhui_yue  chase
dadadadum  dong_fang_hong  entertainer  funeral  funk
ge_chang_zu_guo  jump_down  jump_up  mo_li_hua  nyan  ode
power_down  power_up  prelude  punchline  python  ringtone
tetris  wawawawaa  wedding  yi_meng_shan_xiao_diao
zou_jin_xin_shi_dai
```

外加 `order.txt` 控制播放顺序。最长的两首是 NYAN（106 音）和歌唱祖国（194 音）。

### 技术要点

**分段播放**：`music.play()` 是阻塞的，播完才返回，`music.stop()` 只能在两段之间调用。所以实现成把长曲切成 8 段（每段 380ms），段与段之间才有机会响应按键切歌。

**Web 服务用线程**：`_thread` 可用，Web 服务在独立线程跑，主线程专心按键 + 播放。

**上传流式写盘**：RAM 只有 82KB，上传文件不能整体读进内存，必须边收边写。

---

## 两个项目共同的坑

**出厂 `boot.py` 会删 main.py**

```python
_button_a = machine.Pin(21, machine.Pin.IN)
if _button_a.value() == 1:
    os.remove("/main.py")
```

飞机游戏要按 A 键左移，只要板子在这瞬间重启，程序就没了。**这个坑当时排查了很久**——现象是「按键完全没反应」，屏幕停在最后一帧，第一反应以为是按键坏了，写了一堆诊断代码往上打按键值才发现按键是好的，真正丢的是 `main.py`。

用 `../board/boot_safe.py` 替换掉它。

**固件不支持 f-string**，会 `SyntaxError`。用 `"%d" % x` 或 `"{}".format(x)`。

更多踩坑记录见 [../docs/问题与解决记录.md](../docs/问题与解决记录.md)。
