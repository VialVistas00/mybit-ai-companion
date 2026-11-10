# -*- coding: utf-8 -*-
"""web.py —— MYBIT 曲库播放器的极简 HTTP 服务
单线程、非阻塞：全部处理都在主循环时间片内完成，不与播放抢线程。
不 import player，靠构造参数拿状态与动作，避免循环依赖。
"""
import os
import time
import select
import socket

SONG_DIR = '/songs'
PAGE_FILE = '/www/index.html'
MAX_UP = 64 * 1024

H_PAGE = ('HTTP/1.1 200 OK\r\n'
          'Content-Type: text/html; charset=utf-8\r\n'
          'Connection: close\r\n\r\n')
H_JSON = ('HTTP/1.1 200 OK\r\n'
          'Content-Type: application/json; charset=utf-8\r\n'
          'Connection: close\r\n\r\n')
H_TXT = ('HTTP/1.1 200 OK\r\n'
         'Content-Type: text/plain; charset=utf-8\r\n'
         'Connection: close\r\n\r\n')


class Web(object):
    def __init__(self, port, state, api):
        self.S = state
        self.api = api
        self.srv = socket.socket()
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv.bind(('0.0.0.0', port))
        self.srv.listen(2)
        self.srv.settimeout(0)
        self.cli = None
        self.buf = b''
        self.t0 = 0
        self.method = ''
        self.path = ''
        self.clen = 0
        self.hdr = False
        self.uph = None
        self.upleft = 0
        self.uptmp = ''
        self.upfinal = ''

    # ---------------- 基础 ----------------
    def close(self):
        if self.uph:
            try:
                self.uph.close()
            except Exception:
                pass
            self.uph = None
            try:
                os.remove(self.uptmp)
            except Exception:
                pass
        if self.cli:
            try:
                self.cli.close()
            except Exception:
                pass
        self.cli = None
        self.buf = b''
        self.hdr = False
        self.upleft = 0

    def send(self, head, body):
        if self.cli:
            try:
                self.cli.settimeout(2)
                self.cli.sendall(head.encode() + body.encode())
            except Exception as e:
                print('send err', e)
        self.close()

    def unquote(self, s):
        out = ''
        i = 0
        while i < len(s):
            c = s[i]
            if c == '%' and i + 2 < len(s):
                try:
                    out += chr(int(s[i + 1:i + 3], 16))
                    i += 3
                    continue
                except Exception:
                    pass
            elif c == '+':
                out += ' '
                i += 1
                continue
            out += c
            i += 1
        return out

    def arg(self, key):
        q = ''
        p = self.path
        if '?' in p:
            p, q = p.split('?', 1)
        for kv in q.split('&'):
            if '=' in kv:
                k, v = kv.split('=', 1)
                if self.unquote(k) == key:
                    return self.unquote(v)
        return ''

    def safe_name(self, s):
        out = ''
        for c in s:
            if ('a' <= c <= 'z') or ('A' <= c <= 'Z') or ('0' <= c <= '9') \
                    or c in '_-.':
                out += c
        if not out:
            out = 'song'
        if not out.lower().endswith('.mel'):
            out += '.mel'
        if len(out) > 32:
            out = out[:28] + '.mel'
        return out

    def files(self):
        return self.S['files']

    # ---------------- 路由 ----------------
    def route(self):
        m = self.method
        p = self.path.split('?')[0]
        if m == 'GET' and (p == '/' or p == '/index.html'):
            self.page()
            return
        if m == 'GET' and p == '/api/list':
            self.send(H_JSON, self.json_list())
            return
        if m == 'GET' and p == '/api/status':
            self.send(H_JSON,
                      '{"playing":%s,"paused":%s,"idx":%d,"name":"%s"}'
                      % ('true' if self.S['playing'] else 'false',
                         'true' if self.S['paused'] else 'false',
                         self.S['idx'] + 1,
                         self.S['name'].replace('"', '').replace('\\', '')))
            return
        if m == 'GET' and p == '/play':
            self.cmd_play(self.arg('f'))
            self.send(H_TXT, 'ok')
            return
        if m == 'GET' and p == '/stop':
            self.api['stop']()
            self.send(H_TXT, 'ok')
            return
        if m == 'GET' and p == '/rm':
            self.cmd_rm(self.arg('f'))
            self.send(H_TXT, 'ok')
            return
        if m == 'GET' and p == '/mv':
            self.cmd_mv(self.arg('f'), self.arg('d'))
            self.send(H_TXT, 'ok')
            return
        if m == 'GET' and p == '/rn':
            self.cmd_rn(self.arg('f'), self.arg('n'))
            self.send(H_TXT, 'ok')
            return
        self.send('HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n', 'not found')

    def page(self):
        try:
            fp = open(PAGE_FILE, 'r')
            html = fp.read()
            fp.close()
        except Exception as e:
            self.send(H_TXT, 'page missing: %s' % e)
            return
        html = html.replace('__N__', str(len(self.files())))
        html = html.replace('__IP__', self.S['ip'] if self.S['ip'] else 'offline')
        self.send(H_PAGE, html)

    def json_list(self):
        parts = ['{"files":[']
        first = True
        fl = self.files()
        for i in range(len(fl)):
            fn = fl[i]
            nm = fn
            bs = 120
            tot = 0
            try:
                fp = open(SONG_DIR + '/' + fn, 'r')
                head = fp.read(1500)
                fp.close()
                nm2, b2, lp, tk, tt = self.api['parse'](head, fn)
                nm = nm2
                bs = b2
                tot = tt
            except Exception:
                pass
            if not first:
                parts.append(',')
            first = False
            parts.append('{"i":%d,"f":"%s","n":"%s","sec":%d}'
                         % (i + 1, fn, nm.replace('"', '').replace('\\', ''),
                            int(tot * (60000.0 / (bs * 4.0)) / 1000.0)))
        parts.append(']}')
        return ''.join(parts)

    # ---------------- 动作 ----------------
    def cmd_play(self, f):
        fl = self.files()
        for i in range(len(fl)):
            if fl[i] == f:
                self.api['goto'](i, True)
                return

    def write_order(self, fl):
        try:
            fp = open(SONG_DIR + '/order.txt', 'w')
            fp.write('\n'.join(fl) + '\n')
            fp.close()
        except Exception as e:
            print('order err', e)

    def cmd_rm(self, f):
        if not f:
            return
        fl = self.files()
        was = fl[self.S['idx']] if fl else ''
        try:
            os.remove(SONG_DIR + '/' + f)
        except Exception as e:
            print('rm err', e)
        try:
            fp = open(SONG_DIR + '/order.txt', 'r')
            lines = fp.read().split('\n')
            fp.close()
            keep = []
            for l in lines:
                l = l.strip()
                if l and l != f:
                    keep.append(l)
            self.write_order(keep)
        except Exception:
            pass
        self.api['rescan']()
        if was == f:
            self.api['stop']()
            self.api['goto'](self.S['idx'], False)

    def cmd_mv(self, f, d):
        fl = self.files()
        if f not in fl:
            return
        i = fl.index(f)
        j = i - 1 if d == 'u' else i + 1
        if j < 0 or j >= len(fl):
            return
        fl[i], fl[j] = fl[j], fl[i]
        self.write_order(fl)
        self.S['need_load'] = True

    def cmd_rn(self, f, n):
        if not f or not n:
            return
        new = self.safe_name(n)
        if new == f:
            return
        fl = self.files()
        was = fl[self.S['idx']] if fl else ''
        try:
            os.remove(SONG_DIR + '/' + new)
        except Exception:
            pass
        try:
            os.rename(SONG_DIR + '/' + f, SONG_DIR + '/' + new)
        except Exception as e:
            print('rn err', e)
            return
        try:
            fp = open(SONG_DIR + '/order.txt', 'r')
            lines = fp.read().split('\n')
            fp.close()
            out = []
            for l in lines:
                l = l.strip()
                if l:
                    out.append(new if l == f else l)
            self.write_order(out)
        except Exception:
            pass
        self.api['rescan']()
        if was == f:
            self.S['need_load'] = True

    # ---------------- 上传 ----------------
    def start_upload(self):
        name = self.safe_name(self.arg('f') or 'song')
        if self.clen <= 0 or self.clen > MAX_UP:
            self.send('HTTP/1.1 413 Payload Too Large\r\n'
                      'Connection: close\r\n\r\n', 'too large (max 64KB)')
            return
        try:
            st = os.statvfs('/')
            if st[0] * st[3] < self.clen + 8192:
                self.send('HTTP/1.1 507 Insufficient Storage\r\n'
                          'Connection: close\r\n\r\n', 'no space')
                return
        except Exception:
            pass
        self.upfinal = SONG_DIR + '/' + name
        self.uptmp = SONG_DIR + '/_up.tmp'
        try:
            self.uph = open(self.uptmp, 'wb')
        except Exception as e:
            print('up open err', e)
            self.send('HTTP/1.1 500 Server Error\r\nConnection: close\r\n\r\n',
                      'open fail')
            return
        self.upleft = self.clen
        if self.buf:
            data = self.buf
            self.buf = b''
            n = min(len(data), self.upleft)
            try:
                self.uph.write(data[:n])
            except Exception as e:
                print('up write err', e)
            self.upleft -= n
        if self.upleft <= 0:
            self.finish_upload()

    def finish_upload(self):
        try:
            self.uph.close()
        except Exception:
            pass
        self.uph = None
        try:
            os.remove(self.upfinal)
        except Exception:
            pass
        try:
            os.rename(self.uptmp, self.upfinal)
        except Exception as e:
            print('up rename err', e)
            self.send(H_TXT, 'ok')
            return
        empty = (len(self.files()) == 0)
        self.api['rescan']()
        if empty:
            self.api['goto'](0, False)
        self.send(H_TXT, 'ok')

    def feed_upload(self):
        if self.upleft <= 0:
            return
        try:
            r, _, _ = select.select([self.cli], [], [], 0)
        except Exception:
            self.close()
            return
        if not r:
            return
        try:
            data = self.cli.recv(2048)
        except Exception:
            self.close()
            return
        if not data:
            self.close()
            return
        n = min(len(data), self.upleft)
        try:
            self.uph.write(data[:n])
        except Exception as e:
            print('up write err', e)
            self.close()
            return
        self.upleft -= n
        if self.upleft <= 0:
            self.finish_upload()

    # ---------------- 主轮询 ----------------
    def tick(self, budget_ms, block=0.0):
        end = time.ticks_add(time.ticks_ms(), budget_ms)
        while True:
            if self.cli is None:
                try:
                    self.cli, addr = self.srv.accept()
                except Exception:
                    if block > 0:
                        time.sleep_ms(int(block * 1000))
                    return
                if self.cli is None:
                    return
                self.cli.settimeout(0)
                self.buf = b''
                self.hdr = False
                self.t0 = time.ticks_ms()
                self.upleft = 0
                self.uph = None

            if self.upleft > 0:
                self.feed_upload()
            else:
                try:
                    r, _, _ = select.select([self.cli], [], [], block)
                except Exception:
                    self.close()
                    return
                if not r:
                    if time.ticks_diff(time.ticks_ms(), self.t0) > 6000:
                        self.close()
                    return
                try:
                    data = self.cli.recv(1024)
                except Exception:
                    self.close()
                    return
                if not data:
                    self.close()
                    if time.ticks_diff(end, time.ticks_ms()) <= 0:
                        return
                    continue
                self.buf += data
                if (not self.hdr) and (b'\r\n\r\n' in self.buf):
                    self.parse_head()

            if time.ticks_diff(end, time.ticks_ms()) <= 0:
                return

    def parse_head(self):
        head, _, rest = self.buf.partition(b'\r\n\r\n')
        self.buf = rest
        lines = head.split(b'\r\n')
        try:
            parts = lines[0].decode().split()
            self.method = parts[0]
            self.path = parts[1]
        except Exception:
            self.close()
            return
        self.clen = 0
        for ln in lines[1:]:
            s = ln.decode()
            if s.lower().startswith('content-length:'):
                try:
                    self.clen = int(s.split(':', 1)[1].strip())
                except Exception:
                    self.clen = 0
        self.hdr = True
        if self.method == 'POST':
            if self.path.split('?')[0] == '/up':
                self.start_upload()
            else:
                self.send(H_TXT, 'ok')
            return
        self.route()
