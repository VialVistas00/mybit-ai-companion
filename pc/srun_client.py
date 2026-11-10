# -*- coding: utf-8 -*-
"""
SRun(深澜) Portal 认证客户端 —— MicroPython 版
协议: SRunCGIAuthIntfSvr V1.18 / enc_ver=srun_bx1
流程: get_challenge 取 token -> hmd5=MD5(pwd+token) -> info={SRBX1}base64(xxtea(json,token))
      -> chksum=MD5(token+user+token+hmd5+token+acid+token+ip+token+n+token+type+token+info)
      -> GET /cgi-bin/srun_portal
"""
import socket
import time

try:
    import uhashlib as _hash
except ImportError:
    import hashlib as _hash

try:
    import ubinascii as _b64
except ImportError:
    import binascii as _b64

try:
    import ujson as _json
except ImportError:
    import json as _json


def hmac_md5_hex(key, msg):
    """HMAC-MD5(key=token, msg=password) —— SRun 的 md5(pwd, token) 真实含义
    实测验证：md5('aaa','bbb') == hmac_md5('bbb','aaa')"""
    if isinstance(key, str):
        key = key.encode('utf-8')
    if isinstance(msg, str):
        msg = msg.encode('utf-8')
    try:
        import hmac as _hmac
        return _hmac.new(key, msg, _hash.md5).hexdigest()
    except ImportError:
        pass
    # ---- 纯 Python HMAC-MD5（MicroPython 无 hmac 模块时）----
    blocksize = 64
    if len(key) > blocksize:
        h = _hash.md5(key)
        try:
            key = h.digest()
        except AttributeError:
            key = _b64.unhexlify(h.hexdigest())
    key = key + b'\x00' * (blocksize - len(key))
    ipad = bytes((b ^ 0x36) for b in key)
    opad = bytes((b ^ 0x5c) for b in key)

    def _md5hex(data):
        h = _hash.md5(data)
        try:
            return h.hexdigest()
        except AttributeError:
            return _b64.hexlify(h.digest()).decode('utf-8')

    inner = _b64.unhexlify(_md5hex(ipad + msg).encode())
    return _md5hex(opad + inner)


def md5(text):
    if isinstance(text, str):
        text = text.encode('utf-8')
    h = _hash.md5(text)
    try:
        return h.hexdigest()
    except AttributeError:
        # MicroPython 的 md5 只有 digest()
        return _b64.hexlify(h.digest()).decode('utf-8')


def sha1(text):
    """本 Portal 的 chksum 用的是 sha1；MicroPython 的 uhashlib 没有 sha1，故内置实现"""
    if isinstance(text, str):
        text = text.encode('utf-8')
    try:
        h = _hash.sha1(text)
        try:
            return h.hexdigest()
        except AttributeError:
            return _b64.hexlify(h.digest()).decode('utf-8')
    except AttributeError:
        pass
    # ---- 纯 Python SHA1 ----
    ml = len(text) * 8
    msg = text + b'\x80'
    while len(msg) % 64 != 56:
        msg += b'\x00'
    msg += ml.to_bytes(8, 'big')
    h0, h1, h2, h3, h4 = 0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0
    for blk in range(0, len(msg), 64):
        w = [0] * 80
        for j in range(16):
            k = blk + j * 4
            w[j] = (msg[k] << 24) | (msg[k + 1] << 16) | (msg[k + 2] << 8) | msg[k + 3]
        for j in range(16, 80):
            v = w[j - 3] ^ w[j - 8] ^ w[j - 14] ^ w[j - 16]
            w[j] = ((v << 1) | (v >> 31)) & 0xffffffff
        a, b, c, d, e = h0, h1, h2, h3, h4
        for j in range(80):
            if j < 20:
                f = (b & c) | ((~b & 0xffffffff) & d)
                kk = 0x5A827999
            elif j < 40:
                f = b ^ c ^ d
                kk = 0x6ED9EBA1
            elif j < 60:
                f = (b & c) | (b & d) | (c & d)
                kk = 0x8F1BBCDC
            else:
                f = b ^ c ^ d
                kk = 0xCA62C1D6
            tmp = ((((a << 5) | (a >> 27)) & 0xffffffff) + f + e + kk + w[j]) & 0xffffffff
            e = d
            d = c
            c = ((b << 30) | (b >> 2)) & 0xffffffff
            b = a
            a = tmp
        h0 = (h0 + a) & 0xffffffff
        h1 = (h1 + b) & 0xffffffff
        h2 = (h2 + c) & 0xffffffff
        h3 = (h3 + d) & 0xffffffff
        h4 = (h4 + e) & 0xffffffff
    return '%08x%08x%08x%08x%08x' % (h0, h1, h2, h3, h4)


# ---------------- xxtea (SRun xencode) ----------------
def _ordat(msg, idx):
    if len(msg) > idx:
        return ord(msg[idx])
    return 0


def _sencode(msg, key):
    l = len(msg)
    pwd = []
    i = 0
    while i < l:
        pwd.append(_ordat(msg, i) | (_ordat(msg, i + 1) << 8)
                   | (_ordat(msg, i + 2) << 16) | (_ordat(msg, i + 3) << 24))
        i += 4
    if key:
        pwd.append(l)
    return pwd


def _lencode(msg, key):
    l = len(msg)
    ll = (l - 1) << 2
    if key:
        m = msg[l - 1]
        if m < ll - 3 or m > ll:
            return None
        ll = m
    out = bytearray()
    for i in range(l):
        v = msg[i] & 0xffffffff
        out.append(v & 0xff)
        out.append((v >> 8) & 0xff)
        out.append((v >> 16) & 0xff)
        out.append((v >> 24) & 0xff)
    if key:
        return bytes(out)[:ll]
    return bytes(out)


def xencode(msg, key):
    """SRun 的 xxtea 变体加密，返回 bytes"""
    if msg == '':
        return b''
    pwd = _sencode(msg, True)
    pwdk = _sencode(key, False)
    while len(pwdk) < 4:
        pwdk.append(0)
    n = len(pwd) - 1
    z = pwd[n]
    y = pwd[0]
    c = 0x86014019 | 0x183639A0
    d = 0
    q = int(6 + 52 / (n + 1))
    while q > 0:
        d = (d + c) & (0x8CE0D9BF | 0x731F2640)
        e = (d >> 2) & 3
        p = 0
        while p < n:
            y = pwd[p + 1]
            m = (z >> 5) ^ (y << 2)
            m = m + (((y >> 3) ^ (z << 4)) ^ (d ^ y))
            m = m + (pwdk[(p & 3) ^ e] ^ z)
            pwd[p] = (pwd[p] + m) & (0xEFB8D130 | 0x10472ECF)
            z = pwd[p]
            p += 1
        y = pwd[0]
        m = (z >> 5) ^ (y << 2)
        m = m + (((y >> 3) ^ (z << 4)) ^ (d ^ y))
        m = m + (pwdk[(p & 3) ^ e] ^ z)
        pwd[n] = (pwd[n] + m) & (0xBB390742 | 0x44C6F8BD)
        z = pwd[n]
        q -= 1
    return _lencode(pwd, False)


def b64(data):
    return _b64.b2a_base64(data).decode('utf-8').strip()


def quote(s):
    keep = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0YOUR_WIFI_PASSWORD9-_.~'
    out = ''
    for ch in s:
        if ch in keep:
            out += ch
        else:
            out += '%%%02X' % ord(ch)
    return out


# ---------------- HTTP ----------------
def http_get(host, port, path, timeout=10, maxlen=1500):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(socket.getaddrinfo(host, port)[0][4])
        req = ('GET ' + path + ' HTTP/1.1\r\nHost: ' + host
               + '\r\nConnection: close\r\nUser-Agent: Mozilla/5.0\r\n\r\n')
        s.send(req.encode())
        buf = b''
        while len(buf) < maxlen:
            try:
                c = s.recv(300)
            except Exception:
                break
            if not c:
                break
            buf += c
        return buf.decode('utf-8', 'replace')
    finally:
        s.close()


def _json_of(text):
    """从 cb({...}) 里抠出 JSON"""
    a = text.find('{')
    b = text.rfind('}')
    if a < 0 or b < 0:
        return None
    try:
        return _json.loads(text[a:b + 1])
    except Exception:
        return None


# ---------------- 主流程 ----------------
def login(portal, user, pwd, ip, ac_id='1', n='200', typ='1', os_name='Windows 10'):
    ts = str(int(time.time() * 1000))
    r = http_get(portal, 80,
                 '/cgi-bin/get_challenge?callback=cb&username=' + quote(user)
                 + '&ip=' + ip + '&_=' + ts)
    j = _json_of(r)
    if not j or 'challenge' not in j:
        return {'stage': 'challenge', 'error': 'all', 'raw': r[:400]}
    token = j['challenge']

    hmd5 = hmac_md5_hex(token, pwd)
    info_json = ('{"username":"%s","password":"%s","ip":"%s","acid":"%s","enc_ver":"srun_bx1"}'
                 % (user, pwd, ip, ac_id))
    info_enc = '{SRBX1}' + b64(xencode(info_json, token))

    chk_src = (token + user + token + hmd5 + token + ac_id + token + ip
               + token + n + token + typ + token + info_enc)
    chksum = sha1(chk_src)

    path = ('/cgi-bin/srun_portal?callback=cb&action=login&username=' + quote(user)
            + '&password=' + quote('{MD5}' + hmd5)
            + '&ac_id=' + ac_id + '&ip=' + ip
            + '&chksum=' + chksum
            + '&info=' + quote(info_enc)
            + '&n=' + n + '&type=' + typ
            + '&os=' + quote(os_name) + '&name=' + quote(os_name)
            + '&double_stack=0&_=' + ts)

    r2 = http_get(portal, 80, path)
    j2 = _json_of(r2)
    return {'stage': 'login', 'token': token, 'chksum': chksum,
            'info': info_enc[:40] + '...', 'result': j2, 'raw': r2[:600]}
