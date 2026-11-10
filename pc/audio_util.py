# -*- coding: utf-8 -*-
"""把 8kHz 单声道 16bit PCM 上采样到 16kHz（讯飞 iat 要求）"""
import wave


def resample_8k_to_16k(pcm_bytes):
    """线性插值上采样 2 倍：8k -> 16k"""
    import struct

    n = len(pcm_bytes) // 2
    if n == 0:
        return b""
    samples = struct.unpack("<%dh" % n, pcm_bytes[:n * 2])
    out = bytearray()
    for i in range(n - 1):
        a = samples[i]
        b = samples[i + 1]
        mid = int((a + b) / 2)
        out += struct.pack("<h", a)
        out += struct.pack("<h", mid)
    out += struct.pack("<h", samples[-1])
    out += struct.pack("<h", samples[-1])
    return bytes(out)


def wav_info(path):
    w = wave.open(path, "rb")
    info = {
        "channels": w.getnchannels(),
        "rate": w.getframerate(),
        "width": w.getsampwidth(),
        "frames": w.getnframes(),
        "seconds": w.getnframes() / float(w.getframerate()),
    }
    data = w.readframes(w.getnframes())
    w.close()
    return info, data
