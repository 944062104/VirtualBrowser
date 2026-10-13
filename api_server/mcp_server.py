"""VirtualBrowser MCP (Model Context Protocol) Server
===================================================
Exposes VirtualBrowser management, fingerprint configuration, and Playwright CDP
automation as standard Model Context Protocol (MCP) tools for AI assistants
(Cursor, Claude Desktop, Antigravity, Cline, etc.).

Supports both:
1. Standard Stdio transport (run directly: `python mcp_server.py`)
2. SSE transport (mounted in FastAPI at `/sse` and `/mcp/sse`)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import FastMCP

# Ensure local import
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import core

# Initialize FastMCP Server
mcp = FastMCP(
    name="VirtualBrowser",
    instructions="VirtualBrowser指纹浏览器管理及自动化工具集。支持多环境隔离、指纹配置、窗口启动/停止、以及CDP网页自动化操作。",
)


# ============================================================
# 1. 浏览器环境查询与管理工具
# ============================================================


@mcp.tool()
def list_browsers(group: str = "", keyword: str = "") -> Dict[str, Any]:
    """获取所有配置的指纹浏览器环境列表。

    参数:
        group: 可选，按分组名称筛选
        keyword: 可选，按环境名称或ID关键词筛选
    返回:
        环境列表（包含ID、名称、分组、是否正在运行等信息）
    """
    core.clean_dead_browsers()
    data = core.read_virtual_dat()
    users: List[Dict[str, Any]] = data.get("users", [])

    running_ids = set(core.running_browsers.keys())

    results = []
    for u in users:
        uid = str(u.get("id"))
        is_running = uid in running_ids

        # 筛选分组
        if group and group not in [str(g) for g in u.get("group", [])]:
            continue

        # 筛选关键词
        name = str(u.get("name", ""))
        if keyword and keyword.lower() not in name.lower() and keyword != uid:
            continue

        results.append({
            "id": u.get("id"),
            "name": name,
            "group": u.get("group", []),
            "isRunning": is_running,
            "os": u.get("os", "Win 11"),
            "core_version": u.get("core_version", "auto"),
            "createdAt": u.get("createdAt"),
            "remark": u.get("remark", ""),
        })

    return {
        "total": len(results),
        "browsers": results,
    }


@mcp.tool()
def get_browser_detail(browser_id: int) -> Dict[str, Any]:
    """获取指定浏览器环境的完整指纹参数及配置详情。

    参数:
        browser_id: 环境ID (例如 1)
    """
    str_id = str(browser_id).strip()
    data = core.read_virtual_dat()
    for u in data.get("users", []):
        if str(u.get("id")).strip() == str_id:
            return {"success": True, "browser": u}
    return {"success": False, "error": f"未找到环境 ID={browser_id}"}


@mcp.tool()
def get_running_browsers() -> List[Dict[str, Any]]:
    """获取当前所有处于运行打开状态的浏览器实例（包含进程PID、CDP调试端口及WS连接地址）。"""
    core.clean_dead_browsers()
    return [b.to_dict() for b in core.running_browsers.values()]


# ============================================================
# 2. 浏览器启动与生命周期控制
# ============================================================


@mcp.tool()
async def launch_browser(browser_id: int, url: str = "", headless: bool = False) -> Dict[str, Any]:
    """启动指定的浏览器环境窗口，并返回 CDP 远程调试连接信息。

    参数:
        browser_id: 要启动的环境ID (例如 1)
        url: 可选，启动后直接打开的目标网址 (例如 'https://chatgpt.com')
        headless: 是否使用无头后台模式（默认为 false，显示可视化窗口）
    """
    res = await core.do_launch_browser(bid=browser_id, url=url or None, headless=headless)
    return res


@mcp.tool()
async def stop_browser(browser_id: int) -> Dict[str, Any]:
    """关闭指定的浏览器环境窗口。

    参数:
        browser_id: 要关闭的环境ID (例如 1)
    """
    res = await core.do_stop_browser(bid=browser_id)
    return res


# ============================================================
# 3. 浏览器环境创建与修改
# ============================================================


@mcp.tool()
def create_browser(
    name: str = "",
    group: str = "默认分组",
    homepage: str = "https://www.google.com",
    proxy_protocol: str = "HTTP",
    proxy_host: str = "",
    proxy_port: str = "",
) -> Dict[str, Any]:
    """创建全新的指纹浏览器环境（未指定参数将自动生成高度逼真的硬件指纹）。

    参数:
        name: 环境名称（为空则自动命名为 Browser-{id}）
        group: 环境所属分组名（默认 '默认分组'）
        homepage: 默认主页
        proxy_protocol: 代理协议（HTTP / SOCKS5）
        proxy_host: 代理服务器IP或域名（为空表示不使用代理）
        proxy_port: 代理端口
    """
    data = core.read_virtual_dat()
    users: List[Dict[str, Any]] = data.get("users", [])

    max_id = 0
    for u in users:
        try:
            max_id = max(max_id, int(u.get("id", 0)))
        except (ValueError, TypeError):
            pass
    new_id = max_id + 1

    item = core.generate_default_browser_config(new_id=new_id, name=name, group_name=group)

    if homepage:
        item["homepage"] = {"mode": 0, "value": homepage}

    if proxy_host and proxy_port:
        item["proxy"] = {
            "mode": 1,
            "value": f"{proxy_host}:{proxy_port}",
            "protocol": proxy_protocol.upper(),
            "host": proxy_host,
            "port": proxy_port,
            "user": "",
            "pass": "",
            "API": "",
        }

    users.append(item)
    data["users"] = users
    core.write_virtual_dat(data)
    core.sync_worker_profile_files(new_id)

    return {"success": True, "id": new_id, "name": item["name"], "group": group}


@mcp.tool()
def update_browser(
    browser_id: int,
    name: str = "",
    remark: str = "",
    proxy_host: str = "",
    proxy_port: str = "",
    proxy_protocol: str = "HTTP",
) -> Dict[str, Any]:
    """修改现有环境的名称、备注或代理设置。

    参数:
        browser_id: 环境ID
        name: 新名称（不填则保持不变）
        remark: 备注信息（不填则保持不变）
        proxy_host: 新代理地址
        proxy_port: 新代理端口
        proxy_protocol: 代理协议
    """
    str_id = str(browser_id).strip()
    data = core.read_virtual_dat()
    users: List[Dict[str, Any]] = data.get("users", [])

    found = False
    for u in users:
        if str(u.get("id")).strip() == str_id:
            if name:
                u["name"] = name
            if remark:
                u["remark"] = remark
            if proxy_host and proxy_port:
                u["proxy"] = {
                    "mode": 1,
                    "value": f"{proxy_host}:{proxy_port}",
                    "protocol": proxy_protocol.upper(),
                    "host": proxy_host,
                    "port": proxy_port,
                    "user": "",
                    "pass": "",
                    "API": "",
                }
            u["timestamp"] = int(time.time() * 1000)
            found = True
            break

    if not found:
        return {"success": False, "error": f"未找到环境 ID={browser_id}"}

    data["users"] = users
    core.write_virtual_dat(data)
    core.sync_worker_profile_files(str_id)
    return {"success": True, "msg": f"环境 ID={browser_id} 更新成功"}


@mcp.tool()
async def delete_browser(browser_id: int) -> Dict[str, Any]:
    """删除指定的浏览器环境，并自动关闭运行中的窗口。

    参数:
        browser_id: 环境ID
    """
    str_id = str(browser_id).strip()
    await core.do_stop_browser(str_id)

    data = core.read_virtual_dat()
    users = [u for u in data.get("users", []) if str(u.get("id")).strip() != str_id]
    data["users"] = users
    core.write_virtual_dat(data)

    return {"success": True, "msg": f"环境 ID={browser_id} 删除成功"}


# ============================================================
# 4. 分组管理工具
# ============================================================


@mcp.tool()
def list_groups() -> List[Dict[str, Any]]:
    """获取所有浏览器环境分组列表。"""
    g_data = core.read_global_dat()
    return g_data.get("group", [])


@mcp.tool()
def create_group(name: str) -> Dict[str, Any]:
    """创建新的环境分组。

    参数:
        name: 分组名称
    """
    group_name = str(name).strip()
    if not group_name:
        return {"success": False, "error": "分组名称不能为空"}

    g_data = core.read_global_dat()
    groups: List[Dict[str, Any]] = g_data.get("group", [])

    max_id = 0
    for g in groups:
        try:
            max_id = max(max_id, int(g.get("id", 0)))
        except (ValueError, TypeError):
            pass
    new_id = max_id + 1

    item = {"id": new_id, "name": group_name, "timestamp": int(time.time() * 1000)}
    groups.append(item)
    g_data["group"] = groups
    core.write_global_dat(g_data)

    return {"success": True, "group": item}


# ============================================================
# 5. Playwright / CDP 自动化页面交互工具
# ============================================================


@mcp.tool()
async def browser_navigate(browser_id: int, url: str, wait_seconds: float = 3.0) -> Dict[str, Any]:
    """在指定环境中打开网页（如果环境未启动将自动启动窗口），并返回页面标题和加载结果。

    参数:
        browser_id: 环境ID (例如 1)
        url: 目标网址 (例如 'https://chatgpt.com', 'https://www.baidu.com')
        wait_seconds: 页面加载后额外等待秒数（默认 3 秒）
    """
    res = await core.do_navigate(bid=browser_id, url=url, wait_seconds=wait_seconds)
    return res


@mcp.tool()
async def browser_screenshot(browser_id: int, save_path: str = "") -> Dict[str, Any]:
    """对指定环境中正在运行的浏览器当前页面进行截屏。

    参数:
        browser_id: 环境ID (例如 1)
        save_path: 可选，保存图片的本地磁盘路径（为空则返回图片的 Base64 编码）
    """
    res = await core.do_screenshot(bid=browser_id, save_path=save_path or None)
    return res


@mcp.tool()
async def browser_eval_js(browser_id: int, script: str) -> Dict[str, Any]:
    """在指定环境的当前网页上下文中执行 JavaScript 脚本并返回计算结果。

    参数:
        browser_id: 环境ID (例如 1)
        script: 要执行的 JavaScript 代码字符串 (例如 'document.title' 或 'window.location.href')
    """
    res = await core.do_eval_js(bid=browser_id, script=script)
    return res


# ============================================================
# CLI Entry Point (Stdio Mode)
# ============================================================

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass
    # Run in stdio mode for MCP clients like Cursor, Claude Desktop, Antigravity
    mcp.run()
