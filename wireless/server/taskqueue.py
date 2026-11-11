#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务队列模块 —— 中转服务与电脑执行端之间的指令通道
=========================================================
设计：
  板子语音 -> 识别 -> LLM 判断是否要执行电脑操作
    -> 是：生成指令 JSON，塞进队列
    -> 否：直接回答

  电脑端轮询 /api/task/pull 取任务 -> 执行 -> /api/task/result 回报
  板子再轮询 /api/task/done 拿执行结果播报/显示

任务 JSON：
  {"id": "abc123", "type": "shell|open|qq|browser", "payload": {...}, "ts": ...}

结果 JSON：
  {"id": "abc123", "ok": true, "output": "...", "ts": ...}
"""
import json
import os
import threading
import time
import uuid

QUEUE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "tasks.jsonl")

_LOCK = threading.Lock()
_PENDING = []       # 待执行
_DONE = {}          # id -> result
_SEQ = [0]


def submit(task_type, payload, source="board"):
    """提交一个任务，返回任务 id"""
    tid = uuid.uuid4().hex[:12]
    rec = {
        "id": tid,
        "type": task_type,
        "payload": payload or {},
        "source": source,
        "ts": int(time.time()),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pending",
    }
    with _LOCK:
        _PENDING.append(rec)
        _SEQ[0] += 1
        _log(rec)
    return tid


def pull(limit=5):
    """电脑端取任务（取走即从待执行队列移除）"""
    with _LOCK:
        if not _PENDING:
            return []
        take = _PENDING[:limit]
        del _PENDING[:limit]
        for t in take:
            t["status"] = "taken"
        return take


def complete(tid, ok, output, extra=None):
    """电脑端回报结果"""
    rec = {
        "id": tid,
        "ok": bool(ok),
        "output": str(output or "")[:2000],
        "ts": int(time.time()),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if extra:
        rec.update(extra)
    with _LOCK:
        _DONE[tid] = rec
        # 只保留最近 100 条
        if len(_DONE) > 100:
            for k in list(_DONE.keys())[:len(_DONE) - 100]:
                del _DONE[k]
        _log(rec)
    return rec


def get_done(since_ts=0):
    """板子取执行结果"""
    out = []
    with _LOCK:
        for rec in _DONE.values():
            if rec.get("ts", 0) > since_ts:
                out.append(rec)
    out.sort(key=lambda x: x.get("ts", 0))
    return out[-20:]


def stats():
    with _LOCK:
        return {"pending": len(_PENDING), "done": len(_DONE)}


def _log(rec):
    try:
        with open(QUEUE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
