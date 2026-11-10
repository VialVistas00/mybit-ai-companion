# -*- coding: utf-8 -*-
"""复用 audio-to-text 项目的引擎，测一段本地 wav"""
import sys
import time

sys.path.insert(0, r"D:\数据文件\项目\audio-to-text")

from audio_transcriber import TranscriptionEngine, TranscriptionOptions

WAV = r"D:\数据文件\上课\信电导论\开发板\_scratch\live.wav"

opts = TranscriptionOptions(
    model_name="large-v3-turbo",
    language="zh",
    beam_size=5,
    vad_filter=True,
)

logs = []
def log(msg):
    logs.append(msg)
    print("  [log]", msg)

t0 = time.time()
eng = TranscriptionEngine(opts, log=log)
eng.load()
print("加载耗时 %.1fs，设备 %s/%s" % (time.time() - t0, eng.active_device, eng.active_compute_type))

t1 = time.time()
segments, info = eng.model.transcribe(
    WAV,
    language="zh",
    task="transcribe",
    beam_size=5,
    vad_filter=True,
    vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 200},
    initial_prompt="以下是一段普通话中文对话，请使用简体中文转写，并保留自然标点。",
)
texts = []
for seg in segments:
    texts.append(seg.text.strip())
    print("  [%5.2f-%5.2f] %s" % (seg.start, seg.end, seg.text.strip()))

print("\n识别耗时 %.2fs，音频时长 %.2fs" % (time.time() - t1, info.duration))
print("结果:", repr("".join(texts)))
