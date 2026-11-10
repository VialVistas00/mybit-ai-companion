# MYBIT AI 学伴

给**信息科技实验板（MYBIT / ESP32）** 加一个 AI 大脑：按一下按钮说话，板子录音，电脑识别 + 调大模型，回答显示在 OLED 上。

板子本身算力有限、也上不了外网，所以把重活放在电脑端，板子只做「录音 / 发送 / 显示 / 播报」。

```
┌──────────────┐   USB 串口(COM3)   ┌──────────────────┐   互联网   ┌────────────┐
│ MYBIT 板子    │ ─────────────────▶ │ 电脑              │ ─────────▶ │ DeepSeek   │
│ 录音/显示/播报 │ ◀───────────────── │ faster-whisper   │ ◀───────── │ 或其它 LLM  │
└──────────────┘   REP| base64      └──────────────────┘            └────────────┘
                                     本地语音识别（离线）
```

## 这套东西能做什么

按板子上的 **A 键**，说一句话，板子会：

1. 录 3 秒音频（8kHz / 16bit / 单声道）
2. 通过串口把音频发到电脑
3. 电脑用本地 whisper 转成文字（**不需要联网、不需要 API Key**）
4. 把文字发给大模型，拿回答
5. 回答显示在 OLED 上，并通过外置语音模块念出来

不只问答，还能**直接操作电脑**（`pc/voice_agent.py`）：

| 你说 | 会发生什么 |
|---|---|
| 打开计算器 | 启动 calc.exe |
| 打开百度 | 浏览器打开 baidu.com |
| 搜索杭州天气 | 百度搜索 |
| 今天几号 / 查一下现在几点 | 直接播报时间日期 |
| 音量最大 / 静音 | 调系统音量 |
| 截个图 | 截图存到 `_shots/` |
| 锁屏 | 锁定工作站 |
| 记一下明天交作业 | 追加到 `_notes.txt` |
| 看看 D 盘还剩多少空间 | LLM 生成代码并执行 |

内置指令是精确匹配的，零延迟不烧 token；匹配不到才让 LLM 现场写代码。

## 快速开始

### 1. 电脑端依赖

```bash
pip install pyserial requests flask faster-whisper ctranslate2
```

语音识别模型（二选一）：

- **推荐**：使用已有的 faster-whisper 模型目录，改 `pc/local_asr.py` 里的 `MODEL_DIR`
- 或者让它自动下载 `large-v3-turbo`（约 1.5 GB，首次较慢）

> 有 NVIDIA 显卡会自动用 CUDA，3 秒音频识别约 0.4 秒；纯 CPU 也能跑，只是慢一些。

### 2. 配置

```bash
cd pc
cp gateway_config.example.json gateway_config.json
# 填入你的 llm_key
```

### 3. 板子端

把 `board/ai_companion_serial.py` 的内容作为板子的 `main.py` 烧进去。
烧录方法见 [docs/开发历程.md](docs/开发历程.md)，或者用板子自带的编程工具。

### 4. 运行

```bash
cd pc
python voice_agent.py        # 语音指令模式（能操作电脑）
# 或
python serial_bridge.py      # 纯问答模式
```

然后按板子上的 A 键说话。

## 目录结构

```
mybit-ai-companion/
├── pc/                 电脑端（Python 3.8+）
│   ├── mybit.py                板子串口客户端（raw-REPL 上传/下载/执行）
│   ├── local_asr.py            本地语音识别封装（faster-whisper）
│   ├── serial_bridge.py        串口 AI 问答桥
│   ├── voice_agent.py          语音指令执行器（能操作电脑）
│   ├── ai_gateway.py           HTTP 网关（备用，走网络时用）
│   ├── srun_client.py          校园网 SRun Portal 认证客户端
│   ├── board_server.py         HTTP 版服务端（备用）
│   ├── audio_util.py           8k→16k 重采样
│   └── gateway_config.example.json
├── board/              板子端（MicroPython）
│   ├── ai_companion_serial.py  AI 学伴主程序（串口版，推荐）
│   ├── board_sender.py         只发送不等待的简化版
│   ├── boot_safe.py            安全版 boot.py（防止误删 main.py）
│   ├── ai_companion.py         早期 HTTP 版
│   └── snake.py                贪吃蛇（带音效，示例）
├── docs/
│   ├── 问题与解决记录.md        22 个真实问题，按发生顺序记录排查过程与结论
│   ├── 开发历程.md             技术向的历程：验证数据、失败方案、最终架构
│   └── 硬件笔记.md             板子规格实测数据
├── 附加项目/            顺带完成的两个板子项目
│   ├── README.md               附加项目说明
│   ├── 飞机打外星人/           竖版射击游戏，直写显存跑到 25fps
│   └── 曲库播放器/             板子放歌 + 网页管理曲库（29 首内置曲）
├── examples/           板子示例程序
├── firmware/           固件说明
└── archive/            一次性调试脚本
```

## 附加项目

见 [附加项目/README.md](附加项目/README.md)

| 项目 | 说明 |
|---|---|
| **飞机打外星人** | 竖版射击，A/B 键左右移动，自动连射。绕开 `oled.*` 绘图 API 直接读写显存 framebuf，用 PWM 直驱蜂鸣器替代 `music.pitch()`，把单帧从 143ms 压到 40ms |
| **曲库播放器** | 板子放 `.mel` 音符谱，A/B 键选歌，OLED 显示 IP 后用浏览器上传/删除/调序/点播。实测无 I2S，放不了 MP3，只能放单声部旋律 |

## 硬件

| 项目 | 实测值 |
|---|---|
| 主控 | ESP32-D0WD-V3，240 MHz |
| 固件 | MicroPython 1.13.0 / npython v1.06.5 |
| Flash | 8 MB（文件系统 2 MB） |
| RAM | 111 KB（空载可用约 89 KB） |
| 显示 | SSD1306 OLED 128×64（I2C 0x3C） |
| 传感器 | AHT20 温湿度（I2C 0x38）、光敏、麦克风 |
| 输出 | LED、双 RGB、无源蜂鸣器、UART1 语音合成 |
| 串口 | CH9102 USB转串口，115200 8N1 |

详细实测数据（含性能基准、内存上限、踩过的坑）见 [docs/硬件笔记.md](docs/硬件笔记.md)。

## 已知限制

- **板子必须插 USB**：串口既是数据通道也是供电，拔掉就断
- **录音最长 3 秒**：4 秒会 MemoryError（内存碎片）
- **不支持 f-string**：固件是 Python 3.4 语法子集
- **OLED 约 25 fps**：单帧 40 ms，别指望做高帧率动画

## 踩坑记录

开发过程中遇到的实际问题，分两份文档：

- **[docs/问题与解决记录.md](docs/问题与解决记录.md)** —— 22 个真实问题，按时间顺序记录。包含当时的**错误判断**和后来的纠正，比如：
  - 贪吃蛇「按键没反应」，查了半天发现是出厂 `boot.py` 把 `main.py` 删了
  - 我一度判定「麦克风硬件损坏」，实际是 `sound.read()` 读的是 GPIO37 而麦克风走 I2S，读 0 属正常
  - 录音 4 秒就 `MemoryError`，但 `gc.mem_free()` 显示还有 75KB（堆碎片，不是总量）
  - 录音有 -8567 直流偏置，不去均值识别全是空
  - 刷固件把板子刷成砖，靠 8MB 全片备份救回

- **[docs/开发历程.md](docs/开发历程.md)** —— 技术向的历程，重点在验证数据和方法：
  - `md5(pwd, token)` 实际是 `HMAC-MD5(key=token, msg=pwd)`，附三组验证样本
  - xxtea 加密对比做到 104 字节 0 差异
  - 四条联网路线全部实测失败的具体表现
  - 最终架构与设计取舍

- **[docs/硬件笔记.md](docs/硬件笔记.md)** —— 板子实测规格、性能基准、API 速查

## License

MIT
