# -*- coding: utf-8 -*-
"""直接向 DeepSeek 发一个能暴露身份的问题"""
import json
import sys

import requests

c = json.load(open(r"D:\数据文件\上课\信电导论\开发板\gateway_config.json", encoding="utf-8"))
url = c["llm_base"].rstrip("/") + "/chat/completions"

print("接口:", url)
print("模型参数:", c["llm_model"])
print("Key:", c["llm_key"][:10] + "..." + c["llm_key"][-6:])
print()

questions = [
    "你是什么模型？请说出你的开发公司和具体型号。",
    "你的训练数据截止到什么时候？",
]

for q in questions:
    payload = {
        "model": c["llm_model"],
        "messages": [{"role": "user", "content": q}],
        "stream": False,
        "max_tokens": 300,
    }
    r = requests.post(url, headers={"Authorization": "Bearer " + c["llm_key"],
                                    "Content-Type": "application/json"},
                      json=payload, timeout=60)
    print("问题:", q)
    if r.status_code == 200:
        j = r.json()
        print("回答:", j["choices"][0]["message"]["content"].strip())
        print("响应里的 model 字段:", j.get("model"))
        print("usage:", j.get("usage"))
    else:
        print("失败:", r.status_code, r.text[:200])
    print("-" * 60)
