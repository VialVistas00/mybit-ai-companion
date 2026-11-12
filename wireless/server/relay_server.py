#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MYBIT 中转服务 —— 部署在 10.61.190.8
=========================================================
功能：
  1. 接收板子上传的录音（WAV/裸PCM）
  2. 本地 faster-whisper 识别（或转调）
  3. 调 DeepSeek 生成回答
  4. 把回答存起来，等板子来取

板子侧只需两条 HTTP 请求：
  上传语音：POST /api/ask    body=wav 二进制
  取回答：  GET  /api/reply?since=N

端口 8091（避开已有的 80/3001/8080/8090）
"""
import io
import json
import os
import struct
import threading
import time
import uuid
import wave

from flask import Flask, jsonify, request, Response

try:
    import taskqueue as TQ
except ImportError:
    TQ = None

# ---------------- 配置 ----------------
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "relay_config.json")
CONVLOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "conversations.jsonl")

DEFAULT_CONFIG = {
    "port": 8091,
    "llm_base": "https://api.deepseek.com/v1",
    "llm_key": "",
    "llm_model": "deepseek-chat",
    "system_prompt": "你是小特，一块信息科技实验板上的AI学伴。用口语化中文回答，"
                     "不用表情符号和特殊字符，回答控制在80字以内。",
    "asr_model": "large-v3-turbo",
    "asr_model_dir": "",
    "audio_dir": "/tmp/mybit_audio",
}

app = Flask(__name__)
CFG = {}
REPLIES = []
REPLY_SEQ = [0]
LOCK = threading.Lock()
LOG = []
_ASR = None


def note(msg):
    line = "%s %s" % (time.strftime("%H:%M:%S"), msg)
    LOG.append(line)
    del LOG[:-300]
    print(line, flush=True)


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            note("配置读取失败: %s" % e)
    cfg["llm_key"] = cfg.get("llm_key") or os.environ.get("DEEPSEEK_API_KEY", "")
    return cfg


# ---------------- 语音识别 ----------------
def get_asr():
    global _ASR
    if _ASR is not None:
        return _ASR
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("未安装 faster-whisper，请 pip install faster-whisper")
    model = CFG.get("asr_model") or "large-v3-turbo"
    mdir = CFG.get("asr_model_dir") or ""
    device = "cuda" if _cuda_ok() else "cpu"
    ctype = "float16" if device == "cuda" else "int8"
    note("加载 whisper: %s device=%s" % (model, device))
    if mdir and os.path.isdir(mdir):
        _ASR = WhisperModel(mdir, device=device, compute_type=ctype)
    else:
        _ASR = WhisperModel(model, device=device, compute_type=ctype)
    note("whisper 就绪")
    return _ASR


def _cuda_ok():
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def wav_to_pcm(raw):
    """从 WAV 里剥出 PCM，并返回 (pcm, rate)"""
    if raw[:4] != b"RIFF":
        return raw, 16000
    rate = 16000
    try:
        rate = struct.unpack("<I", raw[24:28])[0]
    except Exception:
        pass
    idx = raw.find(b"data")
    pcm = raw[idx + 8:] if idx >= 0 else raw
    return pcm, rate


def remove_dc_and_gain(pcm, sampwidth=2, target_rms=6000.0):
    """
    去直流 + 裁启动尖峰 + 自适应增益

    MYBIT 板子的录音问题（实测）：
      - 直流偏置约 -8500
      - 真实语音幅度只有 ±330（正常应该 ±10000）
      - 开头 ~120 个样本有 36551 的启动尖峰

    原来的实现用 p95 分位数做归一化，缺陷是：
      如果录音里 95% 是静音，p95 很小 -> 放大倍数虚高 -> 把噪声也放大成刺啦声
      实测「打开电脑上的浏览器」被识别成「拍電腦上的牛腩刺」就是这个原因。

    新做法：
      1. 去均值
      2. 裁掉开头尖峰
      3. 用「有声音段」的 RMS 算增益（先按 p90 判断哪些是有声样本）
      4. 增益上限 30 倍，防止把纯噪声放大
      5. 软限幅，避免削波失真
    """
    n = len(pcm) // 2
    if n < 400:
        return pcm

    s = struct.unpack("<%dh" % n, pcm[:n * 2])
    mean = sum(s) // n
    c = [v - mean for v in s]

    # 裁掉启动尖峰
    skip = min(200, n // 10)
    for i in range(skip):
        c[i] = 0

    # 找有声样本的阈值（p85）
    mags = sorted(abs(v) for v in c)
    if not mags:
        return pcm
    p85 = mags[int(len(mags) * 0.85)]
    if p85 < 30:
        return pcm              # 几乎全静音，不动

    # 只统计超过阈值的样本（真实语音），算 RMS
    total = 0
    cnt = 0
    for v in c:
        if abs(v) >= p85 * 0.5:
            total += v * v
            cnt += 1
    if cnt < 50:
        return pcm
    rms = (total / cnt) ** 0.5
    if rms < 20:
        return pcm

    # 算增益，限制在 1 ~ 30 倍之间
    gain = target_rms / rms
    if gain < 1.0:
        gain = 1.0
    elif gain > 30.0:
        gain = 30.0

    # 应用增益 + 软限幅（tanh 近似）
    out = bytearray()
    limit = 30000.0
    for v in c:
        x = v * gain
        if x > limit:
            # 软压：超出部分压缩到 1/8
            x = limit + (x - limit) / 8.0
            if x > 32767:
                x = 32767
        elif x < -limit:
            x = -limit + (x + limit) / 8.0
            if x < -32768:
                x = -32768
        out += struct.pack("<h", int(x))
    return bytes(out)


def resample_to_16k(pcm, rate):
    if rate == 16000:
        return pcm
    n = len(pcm) // 2
    if n < 2:
        return pcm
    s = struct.unpack("<%dh" % n, pcm[:n * 2])
    ratio = 16000.0 / rate
    out_n = int(n * ratio)
    out = bytearray()
    for i in range(out_n):
        pos = i / ratio
        i0 = int(pos)
        if i0 >= n - 1:
            v = s[-1]
        else:
            frac = pos - i0
            v = int(s[i0] * (1 - frac) + s[i0 + 1] * frac)
        out += struct.pack("<h", v)
    return bytes(out)


def recognize(raw):
    pcm, rate = wav_to_pcm(raw)
    if rate != 16000:
        pcm = resample_to_16k(pcm, rate)

    # 静音检测：这块板子信号弱（真实语音幅度仅 ±330），
    # 门槛设低一点，避免把有效语音当静音丢掉。
    rms = pcm_rms(pcm)
    note("音频强度 rms=%.1f  bytes=%d" % (rms, len(pcm)))
    if rms < 25:
        note("静音，跳过识别")
        return "", None

    pcm = remove_dc_and_gain(pcm)
    note("增益后 rms=%.1f" % pcm_rms(pcm))

    d = CFG.get("audio_dir") or "/tmp/mybit_audio"
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, "ask_%s.wav" % uuid.uuid4().hex[:8])
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm)

    try:
        model = get_asr()
        segs, info = model.transcribe(
            tmp, language="zh", task="transcribe", beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300,
                            "speech_pad_ms": 100,
                            "threshold": 0.5},
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4)
        # ★ 注意：不要用 initial_prompt —— 实测 whisper 会把提示词本身
        #   当成识别结果输出（录到静音时会把 prompt 原样吐出来）。
        parts = []
        for s in segs:
            t = (s.text or "").strip()
            if not t:
                continue
            if getattr(s, "no_speech_prob", 0) > 0.6:
                continue
            parts.append(t)
        text = "".join(parts).strip()

        # 过滤已知的 hallucination 产物
        bad = ("请使用简体中文转写", "请使用简体中文", "字幕由", "感谢观看",
               "谢谢观看", "订阅", "Amara", "字幕", "字幕by")
        for b in bad:
            if text.startswith(b):
                text = text.replace(b, "").strip()
        if text in bad:
            text = ""

        # 繁体转简体（whisper 有时输出繁体）
        text = to_simplified(text)

        return text, None
    except Exception as e:
        return None, "识别失败: %s" % str(e)[:80]
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass


def pcm_rms(pcm):
    """
    计算 PCM 的真实信号强度（去掉直流偏置后的标准差）。
    MYBIT 录音有约 -8500 的直流偏置，直接算 RMS 会被偏置淹没。
    """
    n = len(pcm) // 2
    if n < 100:
        return 0.0
    step = max(1, n // 3000)
    vals = []
    for i in range(0, n, step):
        vals.append(struct.unpack("<h", pcm[i * 2:i * 2 + 2])[0])
    if len(vals) < 10:
        return 0.0
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    return var ** 0.5


# ---------------- 电脑操作指令 ----------------
# LLM 用它判断用户是否想让电脑做事，并给出结构化指令
AGENT_PROMPT = """你是一个电脑操作指令解析器。用户的话来自语音识别，可能有个别字听错。

重要：语音识别常有同音字错误，请按语义理解，不要被个别错字卡住。
例如：
- "打开电脑上的牛奶器" -> 实际是"浏览器"
- "打开记是本" -> "记事本"
- "打开鸡算器" -> "计算器"
- "截过图" -> "截图"
- "把阴凉调大" -> "音量调大"
- "给张三发小心说明天见" -> "发消息"

判断用户的话是否想操作电脑：
- 想操作电脑 -> 只输出一行 JSON，不要任何解释和markdown
- 不想操作电脑 -> 只输出：NONE

支持的指令类型：

1. 打开网址/网站/浏览器（"浏览器""百度""搜索xxx"都归这里）
   {"type":"open_url","url":"https://...","name":"网站名"}
   例：打开电脑上的浏览器 -> {"type":"open_url","url":"https://www.bing.com","name":"浏览器"}
   例：打开百度 -> {"type":"open_url","url":"https://www.baidu.com","name":"百度"}
   例：搜索杭州天气 -> {"type":"open_url","url":"https://www.bing.com/search?q=杭州天气","name":"搜索"}

2. 打开电脑程序
   {"type":"app","name":"notepad","label":"记事本"}
   可用：notepad(记事本) calc(计算器) mspaint(画图) explorer(资源管理器)
         cmd(命令行) taskmgr(任务管理器) control(控制面板)
   例：打开记事本 -> {"type":"app","name":"notepad","label":"记事本"}

3. 给QQ某人发消息
   {"type":"qq","contact":"联系人名","message":"消息内容"}
   例：给张三发消息说明天见 -> {"type":"qq","contact":"张三","message":"明天见"}

4. 执行 PowerShell 命令（查询信息类）
   {"type":"shell","command":"命令"}
   例：看看D盘还剩多少空间 -> {"type":"shell","command":"Get-PSDrive D | Select-Object Used,Free"}

5. 控制音量
   {"type":"volume","level":0到100}  或  {"type":"volume","mute":true}
   例：音量调到50 -> {"type":"volume","level":50}
   例：阴凉调到50 -> {"type":"volume","level":50}
   例：静音 -> {"type":"volume","mute":true}

6. 截图
   {"type":"screenshot"}

7. 锁定电脑
   {"type":"lock"}

8. 打开文件或文件夹
   {"type":"path","path":"D:\\\\数据文件","label":"数据文件"}

9. 向 DSH 对话窗口发送文字（当用户想让AI做事、提问、或说的话不是上面任何操作时，
   默认走这个）
   {"type":"dsh","text":"要发送的完整文字"}
   例：帮我写一个冒泡排序 -> {"type":"dsh","text":"帮我写一个冒泡排序"}
   例：你好小特介绍一下你自己 -> {"type":"dsh","text":"你好小特介绍一下你自己"}
   例：今天天气怎么样 -> {"type":"dsh","text":"今天天气怎么样"}

只在完全无法理解或明显是闲聊时才输出 NONE。
判断不准时，优先选 dsh（把文字发进对话窗口）而不是 NONE。"""

# whisper 有时输出繁体或台湾用词，转成简体常用词
T2S_MAP = {
    "開": "开", "電": "电", "腦": "脑", "瀏": "浏", "覽": "览", "器": "器",
    "網": "网", "頁": "页", "關": "关", "閉": "闭", "檔": "档", "案": "案",
    "夾": "夹", "記": "记", "事": "事", "算": "算", "畫": "画", "圖": "图",
    "聲": "声", "音": "音", "調": "调", "節": "节", "靜": "静", "截": "截",
    "螢": "萤", "幕": "幕", "屏": "屏", "鎖": "锁", "定": "定", "務": "务",
    "管": "管", "理": "理", "資": "资", "源": "源", "應": "应", "用": "用",
    "程": "程", "式": "式", "給": "给", "發": "发", "訊": "讯", "息": "息",
    "這": "这", "個": "个", "請": "请", "幫": "帮", "我": "我", "查": "查",
    "看": "看", "還": "还", "剩": "剩", "多": "多", "少": "少", "間": "间",
    "執": "执", "行": "行", "命": "命", "令": "令", "對": "对", "話": "话",
    "視": "视", "窗": "窗", "口": "口", "系": "系", "統": "统", "啟": "启",
    "動": "动", "選": "选", "擇": "择", "設": "设", "置": "置", "時": "时",
    "鐘": "钟", "日": "日", "曆": "历", "計": "计", "轉": "转", "換": "换",
    "輸": "输", "入": "入", "搜": "搜", "尋": "寻", "熱": "热", "門": "门",
}


def to_simplified(text):
    """繁体转简体（只处理常见字）"""
    if not text:
        return text
    out = []
    for ch in text:
        out.append(T2S_MAP.get(ch, ch))
    return "".join(out)


# 语音识别常见同音错字 -> 正确词（用于本地纠错，喂给 LLM 前先过一遍）
ASR_FIXES = [
    # 浏览器相关
    ("牛奶器", "浏览器"), ("浏懒器", "浏览器"), ("流览器", "浏览器"),
    ("浏览其", "浏览器"), ("浏然器", "浏览器"), ("留览器", "浏览器"),
    ("牛奶起", "浏览器"),
    # 记事本
    ("记是本", "记事本"), ("计事本", "记事本"), ("记事本本", "记事本"),
    # 计算器
    ("鸡算器", "计算器"), ("记算器", "计算器"), ("几算器", "计算器"),
    # 音量
    ("阴凉", "音量"), ("阴量", "音量"), ("音凉", "音量"),
    # 截图
    ("截过图", "截图"), ("截土", "截图"), ("接图", "截图"),
    # 消息
    ("发小心", "发消息"), ("发消西", "发消息"), ("发小气", "发消息"),
    # 文件夹
    ("文件家", "文件夹"), ("问价夹", "文件夹"), ("文件甲", "文件夹"),
    # 屏幕
    ("平幕", "屏幕"), ("瓶幕", "屏幕"),
    # 任务
    ("认务", "任务"),
    # 桌面
    ("桌免", "桌面"), ("卓面", "桌面"),
]


def fix_asr_text(text):
    """修正语音识别的常见同音错字 + 繁体转简体"""
    if not text:
        return text
    out = to_simplified(text)
    for wrong, right in ASR_FIXES:
        if wrong in out:
            out = out.replace(wrong, right)
    return out


def parse_agent_intent(text):
    """让 LLM 判断是否要操作电脑，返回 task dict 或 None"""
    import requests
    if not CFG.get("llm_key"):
        return None

    # 先做本地同音字纠错
    fixed = fix_asr_text(text)
    if fixed != text:
        note("纠错: %s -> %s" % (text[:30], fixed[:30]))

    try:
        r = requests.post(
            CFG["llm_base"].rstrip("/") + "/chat/completions",
            headers={"Authorization": "Bearer " + CFG["llm_key"],
                     "Content-Type": "application/json"},
            json={
                "model": CFG["llm_model"],
                "messages": [
                    {"role": "system", "content": AGENT_PROMPT},
                    {"role": "user", "content": fixed},
                ],
                "stream": False,
                "max_tokens": 200,
                "temperature": 0,
            },
            timeout=25)
        if r.status_code != 200:
            note("意图解析 HTTP %d" % r.status_code)
            return None
        out = r.json()["choices"][0]["message"]["content"].strip()
        note("意图解析: %s" % out[:100])

        if not out or out.upper().startswith("NONE"):
            return None

        # 去掉可能的 ```json 包裹
        if "```" in out:
            a = out.find("{")
            b = out.rfind("}")
            if a >= 0 and b > a:
                out = out[a:b + 1]
        else:
            a = out.find("{")
            b = out.rfind("}")
            if a >= 0 and b > a:
                out = out[a:b + 1]

        task = json.loads(out)
        ttype = task.get("type")
        if not ttype:
            return None
        payload = {k: v for k, v in task.items() if k != "type"}
        return {"type": ttype, "payload": payload}
    except Exception as e:
        note("意图解析失败: %s" % str(e)[:60])
        return None


# 本地模糊匹配兜底（LLM 挂了或没配 key 时也能用）
FUZZY_RULES = [
    # (关键词列表, 任务类型, payload)
    (["浏览器", "打开网页", "上网", "bing"], "open_url",
     {"url": "https://www.bing.com", "name": "浏览器"}),
    (["百度"], "open_url",
     {"url": "https://www.baidu.com", "name": "百度"}),
    (["记事本"], "app", {"name": "notepad", "label": "记事本"}),
    (["计算器"], "app", {"name": "calc", "label": "计算器"}),
    (["画图"], "app", {"name": "mspaint", "label": "画图"}),
    (["资源管理器", "我的电脑"], "app", {"name": "explorer", "label": "资源管理器"}),
    (["任务管理器"], "app", {"name": "taskmgr", "label": "任务管理器"}),
    (["截图", "截屏"], "screenshot", {}),
    (["锁屏", "锁定"], "lock", {}),
    (["静音"], "volume", {"mute": True}),
]


def fuzzy_match(text):
    """兜底：纯关键词匹配，不依赖 LLM"""
    if not text:
        return None
    t = fix_asr_text(text)
    low = t.lower()
    for keys, ttype, payload in FUZZY_RULES:
        for k in keys:
            if k in low:
                return {"type": ttype, "payload": dict(payload)}
    # 发消息
    if "发消息" in low or "发个消息" in low:
        import re as _re
        m = _re.search(r"给(.{1,8}?)(?:发消息|发个消息)", t)
        if m:
            contact = m.group(1).strip()
            body = t[m.end():].strip()
            if contact:
                return {"type": "qq",
                        "payload": {"contact": contact,
                                    "message": body or "你好"}}
    return None


# ---------------- LLM ----------------
def call_llm(q):
    import requests
    if not CFG.get("llm_key"):
        return None, "服务端未配置 llm_key"
    url = CFG["llm_base"].rstrip("/") + "/chat/completions"
    payload = {
        "model": CFG["llm_model"],
        "messages": [
            {"role": "system", "content": CFG["system_prompt"]},
            {"role": "user", "content": q},
        ],
        "stream": False,
        "max_tokens": 400,
    }
    try:
        r = requests.post(url,
                          headers={"Authorization": "Bearer " + CFG["llm_key"],
                                   "Content-Type": "application/json"},
                          json=payload, timeout=45)
        if r.status_code != 200:
            return None, "AI %d" % r.status_code
        return r.json()["choices"][0]["message"]["content"].strip(), None
    except Exception as e:
        return None, "AI异常: %s" % str(e)[:60]


def push_reply(text, kind="reply", meta=None):
    with LOCK:
        REPLY_SEQ[0] += 1
        REPLIES.append({
            "seq": REPLY_SEQ[0],
            "type": kind,
            "text": text,
            "meta": meta or {},
            "ts": int(time.time()),
        })


def log_conv(q, a, kind="voice", extra=None):
    """写对话日志（jsonl，一行一条）"""
    rec = {
        "ts": int(time.time()),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "kind": kind,
        "q": q or "",
        "a": a or "",
    }
    if extra:
        rec.update(extra)
    try:
        with open(CONVLOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        note("写日志失败: %s" % e)


# ---------------- 路由 ----------------
@app.route("/api/debug/save", methods=["POST"])
def api_debug_save():
    """保存上传的 WAV 到服务器，方便本地分析"""
    raw = request.get_data()
    if not raw:
        return jsonify({"ok": False, "error": "no audio"}), 400
    d = "/tmp/mybit_audio"
    os.makedirs(d, exist_ok=True)
    fn = os.path.join(d, "board_%s.wav" % time.strftime("%H%M%S"))
    with open(fn, "wb") as f:
        f.write(raw)
    note("保存音频 %s (%d 字节)" % (fn, len(raw)))
    return jsonify({"ok": True, "path": fn, "bytes": len(raw)})


@app.route("/api/debug/asr", methods=["POST"])
def api_debug_asr():
    """
    调试语音识别：上传 WAV，返回音频统计（不做意图解析）
    用来判断录音质量到底如何。
    """
    raw = request.get_data()
    if not raw:
        return jsonify({"ok": False, "error": "no audio"}), 400

    pcm, rate = wav_to_pcm(raw)
    if rate != 16000:
        pcm = resample_to_16k(pcm, rate)

    rms_before = pcm_rms(pcm)
    pcm2 = remove_dc_and_gain(pcm)
    rms_after = pcm_rms(pcm2)

    # 峰值
    n = len(pcm) // 2
    peak_before = 0
    peak_after = 0
    if n > 100:
        step = max(1, n // 2000)
        for i in range(0, n, step):
            v = abs(struct.unpack("<h", pcm[i * 2:i * 2 + 2])[0])
            if v > peak_before:
                peak_before = v
        for i in range(0, min(len(pcm2) // 2, n), step):
            v = abs(struct.unpack("<h", pcm2[i * 2:i * 2 + 2])[0])
            if v > peak_after:
                peak_after = v

    text, err = recognize(raw)

    return jsonify({
        "ok": True,
        "bytes": len(raw),
        "pcm_bytes": len(pcm),
        "rate": rate,
        "rms_before": round(rms_before, 1),
        "rms_after": round(rms_after, 1),
        "peak_before": peak_before,
        "peak_after": peak_after,
        "gain": round(max(1.0, 6000.0 / max(rms_before, 1)), 2),
        "text": text,
        "error": err,
    })


@app.route("/api/task/pull")
def api_task_pull():
    """电脑端拉取待执行任务"""
    if TQ is None:
        return jsonify({"ok": False, "error": "taskqueue 未加载"}), 503
    try:
        limit = int(request.args.get("limit", "5"))
    except ValueError:
        limit = 5
    tasks = TQ.pull(limit)
    if tasks:
        note("电脑取走 %d 个任务" % len(tasks))
    return jsonify({"ok": True, "tasks": tasks})


@app.route("/api/task/result", methods=["POST"])
def api_task_result():
    """电脑端回报执行结果"""
    if TQ is None:
        return jsonify({"ok": False, "error": "taskqueue 未加载"}), 503
    j = request.get_json(silent=True) or {}
    tid = j.get("id")
    if not tid:
        return jsonify({"ok": False, "error": "missing id"}), 400
    ok = j.get("ok", False)
    output = j.get("output", "")
    rec = TQ.complete(tid, ok, output)
    note("任务完成 %s ok=%s: %s" % (tid, ok, str(output)[:60]))
    # 把结果也推给板子
    push_reply(("执行成功：" if ok else "执行失败：") + str(output)[:80],
               "task", {"task_id": tid})
    return jsonify({"ok": True, "id": tid})


@app.route("/api/task/done")
def api_task_done():
    """板子取执行结果"""
    if TQ is None:
        return jsonify({"ok": False, "error": "taskqueue 未加载"}), 503
    try:
        since = int(request.args.get("since", "0"))
    except ValueError:
        since = 0
    return jsonify({"ok": True, "results": TQ.get_done(since)})


@app.route("/api/task/submit", methods=["POST"])
def api_task_submit():
    """手动提交任务（调试用）"""
    if TQ is None:
        return jsonify({"ok": False, "error": "taskqueue 未加载"}), 503
    j = request.get_json(silent=True) or {}
    ttype = j.get("type")
    if not ttype:
        return jsonify({"ok": False, "error": "missing type"}), 400
    tid = TQ.submit(ttype, j.get("payload") or {})
    note("手动提交任务 %s: %s" % (tid, ttype))
    return jsonify({"ok": True, "id": tid})


@app.route("/api/ping")
def api_ping():
    with LOCK:
        pending = len(REPLIES)
        seq = REPLY_SEQ[0]
    return jsonify({
        "ok": True,
        "service": "mybit-relay",
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "pending": pending,
        "seq": seq,
        "asr_ready": _ASR is not None,
    })


@app.route("/api/ask", methods=["POST"])
def api_ask():
    raw = request.get_data()
    if not raw:
        return jsonify({"ok": False, "error": "no audio"}), 400
    note("收到语音 %d 字节 from %s" % (len(raw), request.remote_addr))

    t0 = time.time()
    text, err = recognize(raw)
    if err:
        note("识别失败: " + err)
        return jsonify({"ok": False, "error": err}), 503
    if not text:
        note("识别为空")
        push_reply("没听清，请再说一次", "error")
        return jsonify({"ok": False, "error": "empty"}), 200
    note("识别(%.1fs): %s" % (time.time() - t0, text))

    # 先判断是不是要操作电脑
    if TQ is not None:
        task = parse_agent_intent(text)
        if task is None:
            # LLM 判断不出来，用模糊匹配兜底
            task = fuzzy_match(text)
            if task:
                note("模糊匹配命中: %s" % task["type"])

        if task:
            tid = TQ.submit(task["type"], task["payload"], source="board")
            note("生成电脑任务 %s: %s" % (tid, task["type"]))
            ans = "好的，正在执行"
            log_conv(text, ans, "voice", {"ip": request.remote_addr,
                                          "bytes": len(raw), "task": tid})
            push_reply(ans, "reply", {"q": text, "task": tid})
            return jsonify({"ok": True, "q": text, "a": ans, "task": tid})

    t1 = time.time()
    ans, aerr = call_llm(text)
    if aerr:
        note("AI 失败: " + aerr)
        push_reply("AI 暂时不可用", "error", {"q": text})
        return jsonify({"ok": False, "error": aerr}), 502
    note("AI(%.1fs): %s" % (time.time() - t1, ans[:60]))

    log_conv(text, ans, "voice", {"ip": request.remote_addr, "bytes": len(raw)})
    push_reply(ans, "reply", {"q": text})
    return jsonify({"ok": True, "q": text, "a": ans})


@app.route("/api/ask_text", methods=["POST", "GET"])
def api_ask_text():
    if request.method == "GET":
        q = request.args.get("q", "").strip()
    else:
        j = request.get_json(silent=True) or {}
        q = (j.get("q") or "").strip()
    if not q:
        return jsonify({"ok": False, "error": "empty"}), 400
    note("文本提问: " + q)

    if TQ is not None:
        task = parse_agent_intent(q)
        if task is None:
            task = fuzzy_match(q)
            if task:
                note("模糊匹配命中: %s" % task["type"])
        if task:
            tid = TQ.submit(task["type"], task["payload"], source="text")
            note("生成电脑任务 %s: %s" % (tid, task["type"]))
            ans = "好的，正在执行"
            log_conv(q, ans, "text", {"ip": request.remote_addr, "task": tid})
            push_reply(ans, "reply", {"q": q, "task": tid})
            return jsonify({"ok": True, "q": q, "a": ans, "task": tid})

    ans, err = call_llm(q)
    if err:
        return jsonify({"ok": False, "error": err}), 502
    note("AI: " + ans[:60])
    log_conv(q, ans, "text", {"ip": request.remote_addr})
    push_reply(ans, "reply", {"q": q})
    return jsonify({"ok": True, "q": q, "a": ans})


@app.route("/api/reply")
def api_reply():
    try:
        since = int(request.args.get("since", "0"))
    except ValueError:
        since = 0
    with LOCK:
        items = [m for m in REPLIES if m["seq"] > since]
        seq = REPLY_SEQ[0]
        if len(REPLIES) > 200:
            del REPLIES[:-200]
    return jsonify({"ok": True, "seq": seq, "count": len(items), "messages": items})


@app.route("/api/conversations")
def api_conversations():
    """读取对话历史（jsonl），供 DSH 或前端查询"""
    try:
        since = int(request.args.get("since", "0"))
    except ValueError:
        since = 0
    try:
        limit = int(request.args.get("limit", "50"))
    except ValueError:
        limit = 50

    items = []
    try:
        with open(CONVLOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("ts", 0) > since:
                    items.append(rec)
    except FileNotFoundError:
        pass
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    if limit and len(items) > limit:
        items = items[-limit:]
    return jsonify({"ok": True, "count": len(items), "items": items})


@app.route("/api/say", methods=["POST"])
def api_say():
    j = request.get_json(silent=True) or {}
    t = (j.get("text") or "").strip()
    if not t:
        return jsonify({"ok": False, "error": "empty"}), 400
    push_reply(t, j.get("type", "notice"))
    return jsonify({"ok": True, "queued": t})


@app.route("/")
def index():
    with LOCK:
        pending = len(REPLIES)
        seq = REPLY_SEQ[0]
    rows = "".join("<li>%s</li>" % l.replace("<", "&lt;") for l in LOG[-40:][::-1]) or "<li>暂无</li>"
    return Response("""<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="3"><title>MYBIT 中转服务</title>
<style>body{font-family:Consolas,monospace;background:#111;color:#0f0;padding:16px}
h2{color:#8cf}li{list-style:none;border-bottom:1px solid #222;padding:2px 0}</style></head>
<body><h2>MYBIT 中转服务 · 运行中</h2>
<p>待取消息 %d ｜ seq=%d ｜ ASR: %s ｜ 模型 %s</p>
<p>板子接口：<code>POST /api/ask</code> ｜ <code>GET /api/reply?since=N</code></p>
<ul>%s</ul></body></html>""" % (pending, seq,
                                "已加载" if _ASR else "未加载",
                                CFG.get("llm_model", "-"), rows),
                    mimetype="text/html")


if __name__ == "__main__":
    CFG = load_config()
    os.makedirs(CFG.get("audio_dir", "/tmp/mybit_audio"), exist_ok=True)
    note("=" * 56)
    note(" MYBIT 中转服务启动")
    note("   端口 %d" % CFG["port"])
    note("   模型 %s" % CFG["llm_model"])
    note("=" * 56)
    # 后台预加载
    try:
        threading.Thread(target=lambda: (lambda: None)() if False else get_asr(), daemon=True).start()
    except Exception:
        pass
    app.run(host="0.0.0.0", port=CFG["port"], debug=False, threaded=True)
