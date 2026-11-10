# -*- coding: utf-8 -*-
"""
在浏览器里注入我的 xencode 实现，与页面实现的输出直接对比
这样能精确定位 xxtea 的差异
"""
import json
import sys
import time

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"

# 我自己的 xxtea（转成 JS）
MY_XTEA_JS = """
function myXencode(msg, key) {
  function ordat(str, idx) { return str.length > idx ? str.charCodeAt(idx) : 0; }
  function sencode(str, keyFlag) {
    var l = str.length, out = [], i = 0;
    while (i < l) {
      out.push((ordat(str,i) | (ordat(str,i+1)<<8) | (ordat(str,i+2)<<16) | (ordat(str,i+3)<<24)) >>> 0);
      i += 4;
    }
    if (keyFlag) out.push(l);
    return out;
  }
  function lencode(arr, keyFlag) {
    var l = arr.length, ll = (l-1) << 2, out = [];
    if (keyFlag) {
      var m = arr[l-1];
      if (m < ll-3 || m > ll) return null;
      ll = m;
    }
    for (var i=0;i<l;i++) {
      var v = arr[i];
      out.push(v & 0xff, (v>>>8)&0xff, (v>>>16)&0xff, (v>>>24)&0xff);
    }
    return keyFlag ? out.slice(0, ll) : out;
  }
  if (msg === '') return [];
  var pwd = sencode(msg, true);
  var pwdk = sencode(key, false);
  while (pwdk.length < 4) pwdk.push(0);
  var n = pwd.length - 1, z = pwd[n], y = pwd[0];
  var c = 0x86014019 | 0x183639A0, d = 0;
  var q = Math.floor(6 + 52 / (n + 1));
  while (q-- > 0) {
    d = (d + c) >>> 0;
    var e = (d >>> 2) & 3;
    for (var p = 0; p < n; p++) {
      y = pwd[p+1];
      var m = ((z>>>5) ^ (y<<2)) >>> 0;
      m = (m + ((((y>>>3) ^ (z<<4)) >>> 0) ^ (d ^ y))) >>> 0;
      m = (m + (pwdk[(p&3) ^ e] ^ z)) >>> 0;
      pwd[p] = (pwd[p] + m) >>> 0;
      z = pwd[p];
    }
    y = pwd[0];
    var m2 = ((z>>>5) ^ (y<<2)) >>> 0;
    m2 = (m2 + ((((y>>>3) ^ (z<<4)) >>> 0) ^ (d ^ y))) >>> 0;
    m2 = (m2 + (pwdk[(n&3) ^ e] ^ z)) >>> 0;
    pwd[n] = (pwd[n] + m2) >>> 0;
    z = pwd[n];
  }
  return lencode(pwd, false);
}
function myB64(bytes) {
  var s = '';
  for (var i = 0; i < bytes.length; i++) s += String.fromCharCode(bytes[i]);
  return btoa(s);
}
function myEncodeUserInfo(plain, token) {
  return '{SRBX1}' + myB64(myXencode(plain, token));
}
"""

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=False,
                                args=["--ignore-certificate-errors"])
    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()
    page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=25000)
    page.wait_for_timeout(3000)

    page.add_script_tag(content=MY_XTEA_JS)
    print("我的 xencode 已注入")

    # 拿一个 token
    token = page.evaluate("""async () => {
        var r = await fetch('http://PORTAL_IP/cgi-bin/get_challenge?callback=cb&username=YOUR_STUDENT_ID&ip=CLIENT_IP');
        var t = await r.text();
        var a = t.indexOf('{'), b = t.lastIndexOf('}');
        return JSON.parse(t.substring(a, b+1)).challenge;
    }""")
    print("token:", token[:32], "...")

    ip = "CLIENT_IP"
    plain = '{"username":"%s","password":"%s","ip":"%s","acid":"1","enc_ver":"srun_bx1"}' % (USER, PWD, ip)
    print("明文:", plain)

    # 我的实现
    mine = page.evaluate("(args) => myEncodeUserInfo(args.p, args.t)", {"p": plain, "t": token})
    print()
    print("我的实现:", mine)

    # 用浏览器原生的 base64 + 让页面自己算（通过登录流程抓）
    # 先检查我的 xxtea 是否可逆
    browser.close()
