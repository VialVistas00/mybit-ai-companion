# -*- coding: utf-8 -*-
"""
mybit.py —— MYBIT(信息科技实验板) 串口客户端
基于 MicroPython 1.13 raw-REPL。不依赖 ampy/mpremote。

用法:
    from mybit import MyBit
    dev = MyBit("COM3")
    dev.exec("print(1+1)")            # 执行并返回输出
    dev.put("microdot.py", "microdot.py")   # 上传本地文件
    dev.get("main.py", "backup_main.py")    # 下载板载文件
    dev.ls()                          # 列目录
    dev.reset()                       # Ctrl-D 软重启
"""
import base64
import time

import serial


class MyBit:
    CHUNK = 1024  # 单次写入的字节数（raw-REPL 单行长度上限保守值）

    def __init__(self, port="COM3", baud=115200, timeout=1.0):
        self.ser = serial.Serial(port, baud, timeout=timeout,
                                 rtscts=False, dsrdtr=False)
        # ESP32 自动下载电路：RTS->EN，DTR->IO0。两者保持高电平才是正常运行态，
        # 拉低 RTS 会让板子一直处于复位循环（表现为程序不动、按键没反应）。
        try:
            self.ser.dtr = True
            self.ser.rts = True
        except Exception:
            pass
        self.ser.write(b"\x03\x03")
        self._drain(0.4)

    # ---------- 低层 ----------
    def _drain(self, t=0.4):
        time.sleep(t)
        buf = b""
        while self.ser.in_waiting:
            buf += self.ser.read(self.ser.in_waiting)
            time.sleep(0.03)
        return buf

    def _read_until(self, token, deadline=6.0):
        buf = b""
        end = time.time() + deadline
        while time.time() < end:
            buf += self.ser.read(self.ser.in_waiting or 1)
            if buf.endswith(token):
                return buf
        return buf

    def _raw_enter(self):
        self.ser.write(b"\x03\x03")
        self._drain(0.25)
        self.ser.reset_input_buffer()
        self.ser.write(b"\x01")
        got = self._read_until(b">", 5.0)
        if b"raw REPL" not in got:
            raise RuntimeError("raw REPL 未就绪: %r" % got[:200])

    def _raw_exit(self):
        self.ser.write(b"\x02")
        time.sleep(0.15)
        self._drain(0.2)

    def _raw_exec(self, code, deadline=10.0):
        """在 raw REPL 中执行一段代码，返回 (stdout, stderr)"""
        if not code.endswith("\n"):
            code += "\n"
        self.ser.write(code.encode("utf-8") + b"\x04")
        buf = b""
        end = time.time() + deadline
        while time.time() < end:
            buf += self.ser.read(self.ser.in_waiting or 1)
            if b"\x04>" in buf:
                break
        if not buf.startswith(b"OK"):
            pass
        body = buf[2:] if buf.startswith(b"OK") else buf
        out, err = body, b""
        if b"\x04" in body:
            out, _, tail = body.partition(b"\x04")
            err, _, _ = tail.partition(b"\x04")
        return out.decode("utf-8", "replace"), err.decode("utf-8", "replace")

    # ---------- 对外 ----------
    def exec(self, code, deadline=10.0):
        self._raw_enter()
        try:
            out, err = self._raw_exec(code, deadline)
        finally:
            self._raw_exit()
        if err.strip():
            raise RuntimeError(err.strip())
        return out

    def ls(self, path="/"):
        return self.exec("import os;print(sorted(os.listdir('%s')))" % path).strip()

    def get(self, remote, local):
        data = self.exec(
            "import ubinascii;"
            "f=open('%s','rb');d=f.read();f.close();"
            "print(ubinascii.b2a_base64(d).decode())" % remote, deadline=20)
        raw = base64.b64decode(data.strip() + "===")
        with open(local, "wb") as fh:
            fh.write(raw)
        return len(raw)

    def put(self, local, remote=None):
        remote = remote or local.split("\\")[-1].split("/")[-1]
        with open(local, "rb") as fh:
            data = fh.read()
        self._raw_enter()
        try:
            self._raw_exec("f=open('%s','wb')" % remote)
            for i in range(0, len(data), self.CHUNK):
                part = data[i:i + self.CHUNK]
                b64 = base64.b64encode(part).decode()
                self._raw_exec(
                    "f.write(__import__('ubinascii').a2b_base64('%s'))" % b64,
                    deadline=15)
            self._raw_exec("f.close()")
        finally:
            self._raw_exit()
        return len(data)

    def reset(self):
        self.ser.write(b"\x02\x04")
        return self._drain(1.2).decode("utf-8", "replace")

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
