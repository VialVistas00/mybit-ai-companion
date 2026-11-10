# -*- coding: utf-8 -*-
"""测 LLM 代码生成：挑几个内置指令覆盖不到的指令"""
import sys

sys.path.insert(0, r"D:\数据文件\上课\信电导论\开发板")
sys.argv = [sys.argv[0], "--dry"]
import voice_agent as VA

TESTS = [
    "看看 D 盘还剩多少空间",
    "列出上课文件夹里有多少个文件",
    "把屏幕亮度调到最低",
    "查一下现在几点",
]

for t in TESTS:
    print("=" * 60)
    print("指令:", t)
    hit, res = VA.try_builtin(t)
    if hit:
        print("内置 ->", res)
        continue
    code, err = VA.llm_codegen(t)
    if err:
        print("生成失败:", err)
        continue
    print("生成的代码:")
    for line in code.split("\n"):
        print("   ", line)
    print()
