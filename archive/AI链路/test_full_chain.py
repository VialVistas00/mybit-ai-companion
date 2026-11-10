# -*- coding: utf-8 -*-
"""
全链路验证（不含板子按键）：
  用 TTS 生成的语音模拟板子录音 -> 本地 whisper 识别 -> DeepSeek -> 结果
"""
import os
import sys
import time
import wave

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")

import local_asr
import serial_bridge as SB

WAV = r"D:\数据文件\上课\信电导论\开发板\_scratch\tts_test.wav"

print("=" * 60)
print(" 全链路测试：语音 -> 识别 -> AI -> 回答")
print("=" * 60)

# 1. 读音频（模拟板子传上来的 wav）
with open(WAV, "rb") as f:
    wav_bytes = f.read()
print("\n[1] 音频 %d 字节" % len(wav_bytes))

# 2. 识别（走 serial_bridge 里的 xfyun_iat，它会优先用本地 whisper）
t0 = time.time()
text, err = SB.xfyun_iat(wav_bytes)
print("[2] 识别耗时 %.2fs" % (time.time() - t0))
if err:
    print("    识别失败:", err)
    sys.exit(1)
print("    识别结果:", text)

# 3. 问 AI
t0 = time.time()
ans, aerr = SB.call_llm(text)
print("[3] AI 耗时 %.2fs" % (time.time() - t0))
if aerr:
    print("    AI 失败:", aerr)
    sys.exit(1)
print("    回答:", ans)

print("\n" + "=" * 60)
print(" 全链路打通")
print("=" * 60)
