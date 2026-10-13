import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

exe = r"D:\Program Files\VirtualBrowser\VirtualBrowser\151.0.7922.47\VirtualBrowser.exe"
user_data = os.path.expandvars(r"%LOCALAPPDATA%\VirtualBrowser\Workers\1")

# Clean leftover locks
for lock_name in ["LOCK", "SingletonLock"]:
    for sub in [Path(user_data), Path(user_data) / "Default"]:
        p = sub / lock_name
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass

print("[*] 正在启动 VirtualBrowser 环境 1 (Worker 1)...")
with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=user_data,
        executable_path=exe,
        args=[
            "--worker-id=1",
            "--proxy-server=http://127.0.0.1:7890",
            "--start-maximized",
        ],
        headless=False,
        viewport=None,
    )
    page = browser.pages[0] if browser.pages else browser.new_page()

    print("[*] 正在访问 ChatGPT 页面 (https://chatgpt.com)...")
    page.goto("https://chatgpt.com", wait_until="domcontentloaded", timeout=45000)
    print(f"[*] 页面已加载: 标题='{page.title()}', URL='{page.url}'")

    # 等待输入框加载
    print("[*] 正在定位输入框...")
    prompt_sel = None
    candidate_selectors = [
        "#prompt-textarea",
        "div#prompt-textarea",
        "div[contenteditable='true']",
        "textarea[placeholder*='Ask']",
        "textarea",
        "[data-placeholder*='Ask ChatGPT']",
    ]

    for sel in candidate_selectors:
        try:
            page.wait_for_selector(sel, timeout=12000)
            prompt_sel = sel
            print(f"[+] 找到输入框选择器: {sel}")
            break
        except Exception:
            continue

    if not prompt_sel:
        print("[-] 未能通过常规选择器找到输入框，正在截屏留档...")
        page.screenshot(path="gpt_no_input.png")
        print("[-] 截屏已保存至 gpt_no_input.png")
    else:
        # 点击输入框并输入 hello
        print("[*] 正在聚焦输入框并输入 'hello'...")
        page.click(prompt_sel)
        time.sleep(1)
        page.keyboard.type("hello", delay=120)
        time.sleep(1)

        # 尝试点击发送按钮或按回车
        send_btn_selectors = [
            "button[data-testid='send-button']",
            "button[aria-label='Send prompt']",
            "button[aria-label*='Send']",
            "button[aria-label*='发送']",
        ]
        clicked = False
        for b_sel in send_btn_selectors:
            try:
                btn = page.query_selector(b_sel)
                if btn and btn.is_enabled():
                    btn.click()
                    clicked = True
                    print(f"[+] 点击发送按钮成功: {b_sel}")
                    break
            except Exception:
                pass

        if not clicked:
            print("[*] 发送按钮不可见或未就绪，按下回车键提交...")
            page.keyboard.press("Enter")

        print("[*] 已发送消息 'hello'，等待 ChatGPT 回复中...")

        # 等待生成回复
        time.sleep(8)

        # 尝试等待停止按钮恢复成发送按钮
        for _ in range(15):
            time.sleep(1)
            stop_btn = page.query_selector("button[data-testid='stop-button'], button[aria-label*='Stop']")
            if not stop_btn:
                break

        # 截屏保存结果
        screenshot_path = "chatgpt_hello_success.png"
        page.screenshot(path=screenshot_path)
        print(f"[+] 对话截屏已保存至: {screenshot_path}")

        # 尝试提取回复文本
        try:
            messages = page.query_selector_all("[data-message-author-role='assistant']")
            if messages:
                last_reply = messages[-1].inner_text()
                print("\n" + "=" * 50)
                print("[ChatGPT 回复内容]:")
                print(last_reply.strip())
                print("=" * 50 + "\n")
        except Exception as e:
            print(f"[!] 提取文本警告: {e}")

    # 保持窗口打开一会儿让用户看到
    print("[*] 执行完成，保持窗口展示 10 秒...")
    time.sleep(10)
    browser.close()
    print("[*] 完成。")
