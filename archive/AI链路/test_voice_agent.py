# -*- coding: utf-8 -*-
"""
测试语音指令链路：音频 -> whisper -> 意图 -> 动作
用 --dry 模式，只看识别和意图，不真正执行
"""
import io
import os
import sys
import time
import wave

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")

# 强制 dry 模式
sys.argv = [sys.argv[0], "--dry"]
import voice_agent as VA

CASES = [
    ("cmd_open_calc.wav", "打开计算器"),
    ("cmd_open_baidu.wav", "打开百度"),
    ("cmd_search.wav", "搜索杭州天气"),
    ("cmd_note.wav", "记一下明天下午三点交作业"),
    ("cmd_volume.wav", "音量最大"),
]

base = r"D:\数据文件\上课\信电导论\开发板\_scratch"

print("预加载 whisper...")
import local_asr
ok, err = local_asr.warmup()
print("  %s" % ("就绪" if ok else "失败 " + str(err)))
print()

import serial
class FakeSer:
    def write(self, b): pass
    def flush(self): pass

for fn, expect in CASES:
    p = os.path.join(base, fn)
    if not os.path.exists(p):
        print("[跳过] %s 不存在" % fn)
        continue
    w = wave.open(p, "rb")
    wav = open(p, "rb").read()
    w.close()

    print("=" * 60)
    print("音频:", fn)
    print("期望:", expect)

    t0 = time.time()
    text, err = VA.recognize(wav)
    print("识别[%.1fs]: %s" % (time.time() - t0, text or err))

    if text:
        hit, res = VA.try_builtin(text)
        if hit:
            print("内置指令命中 ->", res)
        else:
            code, cerr = VA.llm_codegen(text)
            if cerr:
                print("生成失败:", cerr)
            else:
                print("AI 生成代码:")
                for line in code.split("\n"):
                    print("   ", line)
    print()
