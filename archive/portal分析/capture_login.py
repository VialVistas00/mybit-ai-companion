# -*- coding: utf-8 -*-
"""
用 Playwright 打开认证页，真实登录一次，抓取所有网络请求
目的：找出我手写请求里到底缺了什么
"""
import json
import sys
import time

from playwright.sync_api import sync_playwright

PORTAL = "PORTAL_IP"
USER = "YOUR_STUDENT_ID"
PWD = "YOUR_PASSWORD"

captured = []


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="msedge",
            headless=False,
            args=["--ignore-certificate-errors", "--no-sandbox"],
        )
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        def on_request(req):
            url = req.url
            if "srun" in url or "cgi-bin" in url or "get_challenge" in url:
                info = {"method": req.method, "url": url}
                try:
                    if req.post_data:
                        info["post"] = req.post_data[:1500]
                except Exception:
                    pass
                info["headers"] = {k: v for k, v in req.headers.items()
                                   if k.lower() in ("referer", "cookie", "content-type",
                                                    "x-requested-with", "user-agent")}
                captured.append(info)
                print("[REQ] %s %s" % (req.method, url[:200]))

        def on_response(resp):
            url = resp.url
            if "srun_portal" in url or "get_challenge" in url:
                try:
                    txt = resp.text()[:800]
                except Exception:
                    txt = "(无法读取)"
                print("[RESP] %s -> %s" % (url[:120], txt[:300]))
                captured.append({"type": "resp", "url": url, "body": txt})

        page.on("request", on_request)
        page.on("response", on_response)

        print("打开认证页...")
        page.goto("http://%s/srun_portal_pc?ac_id=1&theme=pro" % PORTAL, timeout=30000)
        page.wait_for_timeout(3000)

        # 填表单
        print("填账号密码...")
        try:
            page.fill("#username", USER, timeout=8000)
            page.fill("#password", PWD, timeout=8000)
        except Exception as e:
            print("填表失败:", e)
            page.screenshot(path=r"D:\数据文件\上课\信电导论\开发板\_scratch\login_page.png")
            browser.close()
            return

        page.screenshot(path=r"D:\数据文件\上课\信电导论\开发板\_scratch\login_filled.png")
        print("点击登录...")
        try:
            page.click("#login-account, .login-btn, #btn-login, button[type=submit]",
                       timeout=5000)
        except Exception:
            # 尝试所有可能的登录按钮
            for sel in ("#login-account", ".btn-login", "#login", "a.login-btn"):
                try:
                    page.click(sel, timeout=2000)
                    break
                except Exception:
                    continue
            else:
                print("找不到登录按钮，尝试回车")
                page.keyboard.press("Enter")

        page.wait_for_timeout(6000)
        print("当前 URL:", page.url)
        page.screenshot(path=r"D:\数据文件\上课\信电导论\开发板\_scratch\login_result.png")

        # 保存抓包
        with open(r"D:\数据文件\上课\信电导论\开发板\_scratch\captured.json", "w",
                  encoding="utf-8") as f:
            json.dump(captured, f, ensure_ascii=False, indent=2)
        print("\n共抓取 %d 条请求" % len(captured))

        time.sleep(2)
        browser.close()


main()
