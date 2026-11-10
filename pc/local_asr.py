# -*- coding: utf-8 -*-
"""
本地语音识别模块（复用 D:\数据文件\项目\audio-to-text 的 faster-whisper 引擎）
不依赖任何云服务凭据，纯离线。
"""
import os
import struct
import sys
import tempfile

AUDIO2TEXT_DIR = r"D:\数据文件\项目\audio-to-text"
MODEL_DIR = r"D:\数据文件\模型\faster-whisper"
if not os.path.isdir(MODEL_DIR):
    MODEL_DIR = r"D:\数据文件\模型\faster-whisper"

_engines = {}
_model_lock = None
_loaded = {}


def _get_engine(model_name="large-v3-turbo"):
    if model_name in _engines:
        return _engines[model_name]
    if AUDIO2TEXT_DIR not in sys.path:
        sys.path.insert(0, AUDIO2TEXT_DIR)
    try:
        from audio_transcriber import TranscriptionEngine, TranscriptionOptions
    except ImportError as e:
        raise RuntimeError("找不到 audio_transcriber: %s" % e)
    opts = TranscriptionOptions(
        model_name=model_name,
        model_dir=MODEL_DIR,
        device="auto",
        compute_type="auto",
        language="zh",
    )
    eng = TranscriptionEngine(opts, log=lambda m: print("  [whisper]", m, flush=True))
    eng.load()
    _engines[model_name] = eng
    return eng


def remove_dc_and_gain(pcm, sampwidth=2):
    """去掉直流偏置、裁掉启动尖峰、按稳健峰值归一化。
    这块板子的 audio.record 特征（实测）：
      - 直流偏置约 -8567
      - 开头 60~70 个样本有 30000+ 的启动瞬态尖峰
      - 真实信号幅度只有 ±330 左右
    若按绝对峰值归一化，真实语音会被压得听不见，所以用稳健峰值。"""
    if sampwidth != 2:
        return pcm
    n = len(pcm) // 2
    if n < 400:
        return pcm
    s = struct.unpack("<%dh" % n, pcm[:n * 2])

    # 1. 去均值
    mean = sum(s) // n
    centered = [v - mean for v in s]

    # 2. 裁掉开头的启动瞬态（前 120 个样本置零）
    for i in range(min(120, n)):
        centered[i] = 0

    # 3. 稳健峰值：取 |样本| 的分位数，避免被个别尖峰带偏
    mags = sorted(abs(v) for v in centered)
    p95 = mags[int(len(mags) * 0.95)] if mags else 0
    peak = p95 if p95 > 200 else max(mags) if mags else 0
    if peak < 100:            # 几乎静音
        return pcm

    # 4. 归一化到 60% 量程并限幅
    scale = 0.6 * 32767.0 / peak
    out = bytearray()
    for v in centered:
        x = int(v * scale)
        if x > 32767:
            x = 32767
        elif x < -32768:
            x = -32768
        out += struct.pack("<h", x)
    return bytes(out)


def transcribe_pcm(pcm_bytes, sample_rate=16000, channels=1, sampwidth=2):
    """把 PCM 数据转成文字"""
    import wave

    if sample_rate != 16000:
        pcm_bytes = resample_to_16k(pcm_bytes, sample_rate)

    # 去直流 + 增益（关键：板子录音有大幅直流偏置）
    pcm_bytes = remove_dc_and_gain(pcm_bytes, sampwidth)

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    path = tmp.name
    tmp.close()
    try:
        w = wave.open(path, "wb")
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm_bytes)
        w.close()

        eng = _get_engine()
        segments, info = eng.model.transcribe(
            path,
            language="zh",
            task="transcribe",
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 200},
            initial_prompt="以下是一段普通话中文对话，请使用简体中文转写，并保留自然标点。",
        )
        parts = []
        for seg in segments:
            t = (seg.text or "").strip()
            if t:
                parts.append(t)
        text = "".join(parts).strip()
        return text, None
    except Exception as e:
        return None, "本地识别失败: %s" % str(e)[:80]
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


def resample_to_16k(pcm, rate):
    """任意采样率 -> 16kHz（线性插值）"""
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


def warmup():
    """预加载模型，避免第一次提问等待"""
    try:
        _get_engine()
        return True, None
    except Exception as e:
        return False, str(e)[:120]
