"""VirtualBrowser Core Engine & Automation Backend
=================================================
Provides data persistence, Chromium process management, fingerprint generation,
and Playwright/CDP automation for VirtualBrowser.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import random
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# -------------------- Path Configuration --------------------
LOCAL_APP_DATA = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
VB_USER_DATA_DIR = Path(LOCAL_APP_DATA) / "VirtualBrowser" / "User Data"
VB_WORKERS_DIR = Path(LOCAL_APP_DATA) / "VirtualBrowser" / "Workers"
VB_EXTENSIONS_DIR = Path(LOCAL_APP_DATA) / "VirtualBrowser" / "Extensions"

VIRTUAL_DAT = VB_USER_DATA_DIR / "virtual.dat"
GLOBAL_DAT = VB_USER_DATA_DIR / "global.dat"
EXTENSIONS_DAT = VB_USER_DATA_DIR / "extensions.json"

# Candidate paths for VirtualBrowser executable
CANDIDATE_EXE_PATHS = [
    Path(r"D:\Program Files\VirtualBrowser\VirtualBrowser\154.0.8037.98\VirtualBrowser.exe"),
    Path(r"D:\Program Files\VirtualBrowser\VirtualBrowser\151.0.7922.47\VirtualBrowser.exe"),
    Path(r"C:\Program Files\VirtualBrowser\VirtualBrowser\154.0.8037.98\VirtualBrowser.exe"),
    Path(r"C:\Program Files\VirtualBrowser\VirtualBrowser\151.0.7922.47\VirtualBrowser.exe"),
    Path(r"D:\VirtualBrowser\Chrome-bin\VirtualBrowser.exe"),
    Path(r"C:\VirtualBrowser\Chrome-bin\VirtualBrowser.exe"),
]


def find_browser_executable() -> Path:
    """Find the core VirtualBrowser Chromium executable."""
    for p in CANDIDATE_EXE_PATHS:
        if p.exists():
            return p

    # Dynamic search in Program Files
    for base in [
        Path(r"D:\Program Files\VirtualBrowser"),
        Path(r"C:\Program Files\VirtualBrowser"),
        Path(LOCAL_APP_DATA) / "Programs" / "VirtualBrowser",
    ]:
        if base.exists():
            matches = list(base.glob("**/VirtualBrowser.exe"))
            for m in matches:
                # Need inner Chromium executable, not electron wrapper
                if m.parent.name != "VirtualBrowser" or "resources" not in str(m):
                    if (m.parent / "chrome.dll").exists() or (m.parent / "chromedriver.exe").exists():
                        return m

    raise FileNotFoundError("未找到 VirtualBrowser Chromium 内核执行程序 (VirtualBrowser.exe)")


def get_core_versions() -> List[str]:
    """Get installed Chromium core versions."""
    versions: List[str] = []
    for base in [
        Path(r"D:\Program Files\VirtualBrowser\VirtualBrowser"),
        Path(r"C:\Program Files\VirtualBrowser\VirtualBrowser"),
    ]:
        if base.exists():
            for child in base.iterdir():
                if child.is_dir() and (child / "VirtualBrowser.exe").exists():
                    versions.append(child.name)
    if not versions:
        versions = ["154.0.8037.98"]
    return sorted(list(set(versions)))


# -------------------- Data Storage Helpers --------------------
def read_virtual_dat() -> Dict[str, Any]:
    """Read virtual.dat safely."""
    if not VIRTUAL_DAT.exists():
        return {"users": []}
    try:
        with open(VIRTUAL_DAT, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "users" in data:
                return data
            return {"users": []}
    except Exception as e:
        print(f"[Error] 读取 virtual.dat 失败: {e}")
        return {"users": []}


def write_virtual_dat(data: Dict[str, Any]) -> None:
    """Write virtual.dat with backup protection."""
    VB_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = VIRTUAL_DAT.with_suffix(".tmp")
    bak_file = VIRTUAL_DAT.with_suffix(".bak")

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    if VIRTUAL_DAT.exists():
        try:
            with open(bak_file, "w", encoding="utf-8") as f:
                json.dump(read_virtual_dat(), f, ensure_ascii=False)
        except Exception:
            pass

    temp_file.replace(VIRTUAL_DAT)


def read_global_dat() -> Dict[str, Any]:
    """Read global.dat safely."""
    if not GLOBAL_DAT.exists():
        return {
            "group": [{"id": 1, "name": "默认分组", "timestamp": int(time.time() * 1000)}],
            "cacheDirectory": str(VB_WORKERS_DIR),
            "Channel": "virtualbrowser",
        }
    try:
        with open(GLOBAL_DAT, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            if not raw:
                return {"group": []}
            parsed = json.loads(raw)
            if isinstance(parsed, str):
                parsed = json.loads(parsed)
            return parsed if isinstance(parsed, dict) else {"group": []}
    except Exception as e:
        print(f"[Error] 读取 global.dat 失败: {e}")
        return {"group": []}


def write_global_dat(data: Dict[str, Any]) -> None:
    """Write global.dat (double json-encoded as original software expects)."""
    VB_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = GLOBAL_DAT.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        inner_str = json.dumps(data, ensure_ascii=False)
        f.write(json.dumps(inner_str, ensure_ascii=False))
    temp_file.replace(GLOBAL_DAT)


def read_extensions_dat() -> List[Dict[str, Any]]:
    """Read extensions registry."""
    if not EXTENSIONS_DAT.exists():
        return []
    try:
        with open(EXTENSIONS_DAT, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def write_extensions_dat(exts: List[Dict[str, Any]]) -> None:
    VB_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(EXTENSIONS_DAT, "w", encoding="utf-8") as f:
        json.dump(exts, f, ensure_ascii=False, indent=2)


def sync_worker_profile_files(worker_id: Union[int, str]) -> None:
    """Ensure worker profile directory has required virtual.dat/global.dat."""
    wid = str(worker_id)
    target_dir = VB_WORKERS_DIR / wid
    target_dir.mkdir(parents=True, exist_ok=True)

    master_v = read_virtual_dat()
    master_g = read_global_dat()

    worker_v = target_dir / "virtual.dat"
    worker_g = target_dir / "global.dat"

    try:
        with open(worker_v, "w", encoding="utf-8") as f:
            json.dump(master_v, f, ensure_ascii=False)
        with open(worker_g, "w", encoding="utf-8") as f:
            f.write(json.dumps(json.dumps(master_g, ensure_ascii=False), ensure_ascii=False))
    except Exception as e:
        print(f"[Warn] 同步 worker 配置文件失败: {e}")


def cleanup_profile_locks(worker_id: Union[int, str]) -> None:
    """清理异常残留的锁定文件，防止浏览器启动闪退。"""
    wid = str(worker_id)
    worker_dir = VB_WORKERS_DIR / wid
    lock_targets = [
        worker_dir / "LOCK",
        worker_dir / "SingletonLock",
        worker_dir / "lockfile",
        worker_dir / "Default" / "LOCK",
        worker_dir / "Default" / "SingletonLock",
        worker_dir / "Default" / "lockfile",
    ]
    for p in lock_targets:
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass


def update_browser_running_status_in_dat(worker_id: Union[int, str], is_running: bool) -> None:
    """实时同步更新 virtual.dat 中的 isRunning 状态，使客户端界面保持一致。"""
    str_id = str(worker_id).strip()
    data = read_virtual_dat()
    changed = False
    for u in data.get("users", []):
        if str(u.get("id")).strip() == str_id:
            if u.get("isRunning") != is_running:
                u["isRunning"] = is_running
                u["runLoading"] = False
                u["timestamp"] = int(time.time() * 1000)
                changed = True
    if changed:
        try:
            write_virtual_dat(data)
        except Exception as e:
            print(f"[Warn] 同步 virtual.dat 运行状态失败: {e}")


# -------------------- Process & CDP Management --------------------
class RunningBrowser:
    def __init__(self, worker_id: Union[int, str], pid: int, port: int, ws_url: str, proc: subprocess.Popen):
        self.worker_id = str(worker_id)
        self.pid = pid
        self.port = port
        self.ws_url = ws_url
        self.http_url = f"127.0.0.1:{port}"
        self.proc = proc
        self.start_time = time.time()

    def is_alive(self) -> bool:
        if self.proc.poll() is not None:
            return False
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}/json/version")
            with urllib.request.urlopen(req, timeout=1) as resp:
                return resp.status == 200
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": int(self.worker_id) if self.worker_id.isdigit() else self.worker_id,
            "browserId": self.worker_id,
            "pid": self.pid,
            "port": self.port,
            "debuggingPort": self.port,
            "http": self.http_url,
            "ws": self.ws_url,
            "webSocketDebuggerUrl": self.ws_url,
        }


running_browsers: Dict[str, RunningBrowser] = {}


def find_free_port(start_port: int = 9222, max_port: int = 9999) -> int:
    """Find an available TCP port for CDP."""
    occupied = {b.port for b in running_browsers.values()}
    for port in range(start_port, max_port):
        if port in occupied:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("没有可用的调试端口 (9222-9999)")


def clean_dead_browsers() -> None:
    """Periodic cleanup of terminated browser processes."""
    to_remove = []
    for wid, b in running_browsers.items():
        if b.proc.poll() is not None:
            to_remove.append(wid)
    for wid in to_remove:
        running_browsers.pop(wid, None)
        update_browser_running_status_in_dat(wid, False)


def kill_process_tree(pid: int) -> None:
    """Force kill a process and its child processes on Windows."""
    try:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except Exception as e:
        print(f"[Warn] taskkill pid={pid} error: {e}")


# -------------------- Template Generator --------------------
def generate_default_browser_config(new_id: int, name: Optional[str] = None, group_name: str = "默认分组") -> Dict[str, Any]:
    """Generate complete fingerprint configuration for a new environment."""
    mac_parts = [f"{random.randint(0, 255):02X}" for _ in range(6)]
    mac_addr = "-".join(mac_parts)
    computer_name = f"DESKTOP-{random.randint(1000000, 9999999):X}"

    screens = [
        {"width": 1920, "height": 1080, "_value": "1920 x 1080"},
        {"width": 2560, "height": 1440, "_value": "2560 x 1440"},
        {"width": 1536, "height": 864, "_value": "1536 x 864"},
    ]
    chosen_screen = random.choice(screens)

    return {
        "id": new_id,
        "name": name or f"Browser-{new_id}",
        "createdAt": int(time.time() * 1000),
        "group": [group_name],
        "remark": "",
        "os": "Win 11",
        "chrome_version": 146,
        "core_version": "auto",
        "proxy": {
            "mode": 0,
            "value": "",
            "protocol": "HTTP",
            "host": "",
            "port": "",
            "user": "",
            "pass": "",
            "API": "",
        },
        "cookie": {"mode": 0, "value": "", "jsonStr": "[]"},
        "homepage": {"mode": 0, "value": "https://www.google.com"},
        "ua": {
            "mode": 0,
            "value": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        },
        "ua-full-version": {"mode": 1, "value": "146.0.7680.31"},
        "sec-ch-ua": {
            "mode": 0,
            "value": [
                {"brand": "Chromium", "version": 146},
                {"brand": "Not=A?Brand", "version": 99},
            ],
        },
        "ua-language": {"mode": 2, "language": "zh-CN,zh", "value": "zh-CN,zh;q=0.9"},
        "time-zone": {
            "mode": 2,
            "zone": "UTC+8:00",
            "utc": "Asia/Shanghai",
            "locale": "",
            "name": "(UTC+08:00) Asia/Shanghai",
            "value": 8,
        },
        "webrtc": {"mode": 0},
        "location": {"mode": 2, "enable": 1, "precision": 5000},
        "screen": {
            "mode": 0,
            "width": chosen_screen["width"],
            "height": chosen_screen["height"],
            "_value": chosen_screen["_value"],
        },
        "fonts": {
            "mode": 1,
            "value": ["Calibri Light", "Franklin Gothic Medium", "Segoe UI Light", "Microsoft YaHei"],
        },
        "canvas": {"mode": 1, "r": random.randint(-10, 10), "g": random.randint(-10, 10), "b": random.randint(-10, 10), "a": -5},
        "webgl-img": {"mode": 1, "r": random.randint(-5, 5), "g": random.randint(-5, 5), "b": random.randint(-5, 5), "a": -2},
        "webgl": {
            "mode": 1,
            "vendor": "Google Inc. (NVIDIA)",
            "render": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11-27.21.14.5671)",
        },
        "webgpu": {"mode": 1, "vendor": "nvidia", "architecture": "ampere"},
        "audio-context": {"mode": 1, "channel": random.uniform(1e-8, 1e-7), "analyer": random.uniform(0.01, 0.05)},
        "media": {"mode": 1},
        "client-rects": {"mode": 1, "width": random.uniform(0.0001, 0.001), "height": random.uniform(-0.1, -0.01)},
        "speech_voices": {"mode": 1, "value": []},
        "ssl": {"mode": 0, "value": []},
        "cpu": {"mode": 1, "value": random.choice([4, 6, 8, 12, 16])},
        "memory": {"mode": 1, "value": random.choice([8, 16, 32])},
        "device-name": {"mode": 1, "value": computer_name},
        "mac": {"mode": 1, "value": mac_addr},
        "dnt": {"mode": 1, "value": 0},
        "port-scan": {"mode": 1, "value": []},
        "gpu": {"mode": 1, "value": 1},
        "launchArgs": {"mode": 0, "value": ""},
        "accountList": [],
        "enableCloudSync": False,
        "_cloudSyncPending": False,
        "isRunning": False,
        "runLoading": False,
        "remarkPopoverVisible": False,
        "timestamp": int(time.time() * 1000),
    }


# -------------------- Core Launch / Stop Operations --------------------
async def do_launch_browser(
    bid: Union[int, str],
    url: Optional[str] = None,
    headless: bool = False,
    extra_args: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """启动指定环境并返回 CDP 连接信息。"""
    clean_dead_browsers()
    str_id = str(bid).strip()

    # 1. 检查是否已经在运行
    if str_id in running_browsers:
        existing = running_browsers[str_id]
        if existing.is_alive():
            return {
                "success": True,
                "msg": "窗口已在运行中",
                "data": existing.to_dict(),
            }
        else:
            running_browsers.pop(str_id, None)

    # 2. 读取配置
    data = read_virtual_dat()
    target_config: Optional[Dict[str, Any]] = None
    for u in data.get("users", []):
        if str(u.get("id")).strip() == str_id:
            target_config = u
            break

    if not target_config:
        return {"success": False, "msg": f"未找到环境 ID={bid}", "data": None}

    # 3. 准备 profile 目录并同步配置
    sync_worker_profile_files(str_id)
    worker_dir = VB_WORKERS_DIR / str_id

    # 4. 分配调试端口
    port = find_free_port()

    # 5. 查找 Chromium 可执行文件
    try:
        browser_exe = find_browser_executable()
    except FileNotFoundError as e:
        return {"success": False, "msg": str(e), "data": None}

    # 6. 组装启动参数
    cmd = [
        str(browser_exe),
        f"--user-data-dir={worker_dir}",
        f"--worker-id={str_id}",
        f"--remote-debugging-port={port}",
        "--no-first-run",
        "--no-default-browser-check",
    ]

    # 无头模式
    if headless is True or target_config.get("headless") is True:
        cmd.append("--headless=new")
    else:
        cmd.append("--start-maximized")

    # 代理
    proxy = target_config.get("proxy") or {}
    if isinstance(proxy, dict) and proxy.get("mode", 0) != 0:
        host = proxy.get("host")
        pport = proxy.get("port")
        proto = proxy.get("protocol", "http").lower()
        if host and pport:
            cmd.append(f"--proxy-server={proto}://{host}:{pport}")

    # 自定义附加参数
    if extra_args and isinstance(extra_args, list):
        for arg in extra_args:
            s_arg = str(arg).strip()
            if s_arg and s_arg not in cmd:
                cmd.append(s_arg)

    # 插件
    exts = read_extensions_dat()
    enabled_ext_paths = [e["path"] for e in exts if e.get("enabled", True) and Path(e.get("path", "")).exists()]
    if enabled_ext_paths:
        cmd.append(f"--load-extension={','.join(enabled_ext_paths)}")

    # 启动 URL
    target_url = url
    if not target_url:
        homepage = target_config.get("homepage", {})
        if isinstance(homepage, dict) and homepage.get("value"):
            target_url = homepage["value"]
    if target_url:
        cmd.append(str(target_url))

    # 清理残留锁
    cleanup_profile_locks(str_id)

    # 7. 启动子进程
    try:
        proc = subprocess.Popen(cmd)
    except Exception as e:
        return {"success": False, "msg": f"启动浏览器进程失败: {e}", "data": None}

    # 8. 轮询等待 CDP 就绪
    ws_url = ""
    for _ in range(40):  # 最多等待 20 秒
        await asyncio.sleep(0.5)
        if proc.poll() is not None:
            return {"success": False, "msg": f"浏览器进程异常退出 (exit_code={proc.returncode})", "data": None}
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/json/version")
            with urllib.request.urlopen(req, timeout=1) as resp:
                if resp.status == 200:
                    cdp_info = json.loads(resp.read().decode())
                    ws_url = cdp_info.get("webSocketDebuggerUrl", "")
                    break
        except Exception:
            continue

    if not ws_url:
        kill_process_tree(proc.pid)
        return {"success": False, "msg": "等待浏览器 CDP 端口就绪超时 (20s)", "data": None}

    browser_instance = RunningBrowser(
        worker_id=str_id,
        pid=proc.pid,
        port=port,
        ws_url=ws_url,
        proc=proc,
    )
    running_browsers[str_id] = browser_instance
    update_browser_running_status_in_dat(str_id, True)

    return {"success": True, "msg": "启动成功", "data": browser_instance.to_dict()}


async def do_stop_browser(bid: Union[int, str]) -> Dict[str, Any]:
    """关闭指定的浏览器环境。"""
    clean_dead_browsers()
    str_id = str(bid).strip()

    if str_id in running_browsers:
        instance = running_browsers.pop(str_id)
        kill_process_tree(instance.pid)
        update_browser_running_status_in_dat(str_id, False)
        return {"success": True, "msg": "关闭成功"}

    update_browser_running_status_in_dat(str_id, False)

    # 兜底：检测外部是否有携带 --worker-id=bid 的遗留进程
    try:
        out = subprocess.check_output(
            f'wmic process where "CommandLine like \'%-worker-id={str_id}%\'" get ProcessId',
            shell=True,
            text=True,
            stderr=subprocess.DEVNULL,
        )
        for line in out.splitlines():
            pid_str = line.strip()
            if pid_str.isdigit():
                kill_process_tree(int(pid_str))
    except Exception:
        pass

    return {"success": True, "msg": "关闭成功"}


# -------------------- Automation with Playwright --------------------
async def do_navigate(bid: Union[int, str], url: str, wait_seconds: float = 3.0) -> Dict[str, Any]:
    """确保环境已启动，并通过 Playwright/CDP 导航到指定网址。"""
    str_id = str(bid).strip()

    # 1. 确保启动
    launch_res = await do_launch_browser(str_id, url=url)
    if not launch_res.get("success"):
        return launch_res

    port = launch_res["data"]["port"]

    # 2. 使用 Playwright 连接 CDP
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()

            # 导航
            if page.url != url:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)

            title = await page.title()
            current_url = page.url
            return {
                "success": True,
                "msg": f"已成功导航至 {current_url}",
                "data": {
                    "id": str_id,
                    "title": title,
                    "url": current_url,
                    "port": port,
                },
            }
    except Exception as e:
        return {"success": False, "msg": f"CDP 页面导航失败: {e}", "data": None}


async def do_screenshot(bid: Union[int, str], save_path: Optional[str] = None) -> Dict[str, Any]:
    """通过 Playwright/CDP 截取当前浏览器页面。"""
    str_id = str(bid).strip()
    if str_id not in running_browsers or not running_browsers[str_id].is_alive():
        return {"success": False, "msg": f"浏览器 ID={bid} 尚未运行，请先启动", "data": None}

    port = running_browsers[str_id].port
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()

            if not save_path:
                screenshot_bytes = await page.screenshot(full_page=False)
                b64 = base64.b64encode(screenshot_bytes).decode()
                return {
                    "success": True,
                    "msg": "截图成功",
                    "data": {"base64": b64, "url": page.url, "title": await page.title()},
                }
            else:
                out_path = Path(save_path)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(out_path), full_page=False)
                return {
                    "success": True,
                    "msg": f"截图已保存至 {out_path}",
                    "data": {"path": str(out_path), "url": page.url, "title": await page.title()},
                }
    except Exception as e:
        return {"success": False, "msg": f"截图失败: {e}", "data": None}


async def do_eval_js(bid: Union[int, str], script: str) -> Dict[str, Any]:
    """在运行中的浏览器页面上下文执行 JavaScript 代码。"""
    str_id = str(bid).strip()
    if str_id not in running_browsers or not running_browsers[str_id].is_alive():
        return {"success": False, "msg": f"浏览器 ID={bid} 尚未运行，请先启动", "data": None}

    port = running_browsers[str_id].port
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = context.pages[0] if context.pages else await context.new_page()
            result = await page.evaluate(script)
            return {"success": True, "msg": "执行成功", "data": {"result": result}}
    except Exception as e:
        return {"success": False, "msg": f"执行 JavaScript 失败: {e}", "data": None}
