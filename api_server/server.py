"""VirtualBrowser Local API & MCP Server (完全免费 / 免 VIP)
=============================================================
同时提供完整的 VirtualBrowser HTTP REST API 服务以及标准 Model Context Protocol (MCP) 服务。

- REST API 端口: 默认 9000 (支持 /api/* 接口)
- MCP SSE 端点: http://127.0.0.1:9000/sse
- API 在线文档: http://127.0.0.1:9000/docs
- Web 控制看板: http://127.0.0.1:9000/
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

# Ensure local import
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import core
from mcp_server import mcp

# -------------------- FastAPI App --------------------
app = FastAPI(
    title="VirtualBrowser Local API & MCP Service",
    description="免VIP开放的 VirtualBrowser 本地自动化控制与指纹环境管理接口",
    version="2.0.0",
)

# CORS 支持跨域调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载 FastMCP SSE 协议应用
mcp_sse_app = mcp.sse_app()
app.mount("/mcp", mcp_sse_app)
app.mount("/sse", mcp_sse_app)


def api_success(data: Any = None, msg: str = "success") -> Dict[str, Any]:
    return {
        "success": True,
        "code": 0,
        "msg": msg,
        "data": data if data is not None else {},
    }


def api_error(msg: str = "error", code: int = -1) -> Dict[str, Any]:
    return {
        "success": False,
        "code": code,
        "msg": msg,
        "error": msg,
        "data": {},
    }


# ============================================================
# 0. 首页控制看板与文档
# ============================================================


@app.get("/", response_class=HTMLResponse)
async def index_page():
    """提供本地可视化服务看板与配置引导页面"""
    core.clean_dead_browsers()
    running_count = len(core.running_browsers)
    total_browsers = len(core.read_virtual_dat().get("users", []))
    core_versions = core.get_core_versions()
    core_versions_str = ", ".join(core_versions)
    mcp_script_path = str(CURRENT_DIR / "mcp_server.py").replace("\\", "\\\\")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>VirtualBrowser 本地 API & MCP 服务控制台</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background: #0f172a; color: #f1f5f9; padding: 24px; }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    .header {{ display: flex; align-items: center; justify-content: space-between; padding-bottom: 20px; border-bottom: 1px solid #334155; margin-bottom: 24px; }}
    .title {{ font-size: 24px; font-weight: 700; color: #38bdf8; display: flex; align-items: center; gap: 10px; }}
    .badge {{ background: #10b981; color: #fff; padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-bottom: 24px; }}
    .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; }}
    .card-title {{ font-size: 13px; color: #94a3b8; text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.5px; }}
    .card-value {{ font-size: 24px; font-weight: 700; color: #f8fafc; }}
    .card-desc {{ font-size: 12px; color: #64748b; margin-top: 6px; }}
    .section {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 24px; margin-bottom: 24px; }}
    .section-title {{ font-size: 18px; font-weight: 600; color: #e2e8f0; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between; }}
    .link-btn {{ background: #0284c7; color: white; padding: 6px 14px; border-radius: 6px; text-decoration: none; font-size: 13px; font-weight: 500; transition: background 0.2s; }}
    .link-btn:hover {{ background: #0369a1; }}
    pre {{ background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 14px; font-size: 13px; color: #a5f3fc; overflow-x: auto; font-family: Consolas, Monaco, monospace; }}
    table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }}
    th {{ background: #0f172a; padding: 12px; color: #94a3b8; border-bottom: 1px solid #334155; }}
    td {{ padding: 12px; border-bottom: 1px solid #1e293b; color: #cbd5e1; }}
    tr:hover td {{ background: #26334d; }}
    .method-get {{ background: #0369a1; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; }}
    .method-post {{ background: #059669; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; }}
    .tag {{ background: #334155; color: #93c5fd; padding: 2px 8px; border-radius: 4px; font-size: 11px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="title">
        <span>🌐 VirtualBrowser 本地 API & MCP 服务</span>
        <span class="badge">运行正常 (免 VIP)</span>
      </div>
      <div>
        <a class="link-btn" href="/docs" target="_blank">📖 Swagger API 在线交互文档</a>
      </div>
    </div>

    <div class="cards">
      <div class="card">
        <div class="card-title">已配置环境总数</div>
        <div class="card-value">{total_browsers}</div>
        <div class="card-desc">位于本地 User Data\virtual.dat</div>
      </div>
      <div class="card">
        <div class="card-title">正在运行窗口</div>
        <div class="card-value" style="color: #34d399;">{running_count}</div>
        <div class="card-desc">可通过 CDP 远程自动化操作</div>
      </div>
      <div class="card">
        <div class="card-title">已安装内核版本</div>
        <div class="card-value" style="font-size: 18px; line-height: 32px;">{core_versions_str}</div>
        <div class="card-desc">Chromium Core Path</div>
      </div>
      <div class="card">
        <div class="card-title">服务监听端口</div>
        <div class="card-value" style="color: #38bdf8;">9000</div>
        <div class="card-desc">HTTP REST + MCP SSE 服务</div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">
        <span>🤖 MCP (Model Context Protocol) 服务配置</span>
        <span class="tag">支持 Cursor / Claude Desktop / Antigravity</span>
      </div>
      <p style="color: #94a3b8; font-size: 14px; margin-bottom: 12px;">
        已提供 13 项标准 MCP 工具（包含环境查询、指纹配置、多开启动、关闭、以及基于 Playwright/CDP 的网页导航和截屏）。可以直接在您的 AI 客户端中配置使用：
      </p>

      <div style="margin-bottom: 14px;">
        <strong style="color: #38bdf8; font-size: 13px;">方式 1：标准 Stdio 模式（推荐，直接执行 Python 脚本）</strong>
        <pre>{{
  "mcpServers": {{
    "virtual-browser": {{
      "command": "python",
      "args": ["{mcp_script_path}"]
    }}
  }}
}}</pre>
      </div>

      <div>
        <strong style="color: #38bdf8; font-size: 13px;">方式 2：HTTP / SSE 模式（直连本地运行的服务端口）</strong>
        <pre>MCP SSE Endpoint: http://127.0.0.1:9000/sse</pre>
      </div>
    </div>

    <div class="section">
      <div class="section-title">
        <span>⚡ HTTP REST API 接口清单 (全 16 项接口)</span>
        <a class="link-btn" href="/docs" target="_blank">在 Swagger 中调试测试</a>
      </div>
      <table>
        <thead>
          <tr>
            <th>分类</th>
            <th>接口路径</th>
            <th>方法</th>
            <th>说明</th>
          </tr>
        </thead>
        <tbody>
          <tr><td>浏览器管理</td><td><code>/api/getBrowserList</code></td><td><span class="method-get">GET</span> <span class="method-post">POST</span></td><td>获取环境列表（支持分页、关键词搜索、分组筛选）</td></tr>
          <tr><td>浏览器管理</td><td><code>/api/getBrowserFullParameters</code></td><td><span class="method-get">GET</span></td><td>获取环境完整参数（所有指纹项）</td></tr>
          <tr><td>浏览器管理</td><td><code>/api/getBrowserRunningList</code></td><td><span class="method-get">GET</span></td><td>获取当前正在运行的窗口及 CDP 调试端口</td></tr>
          <tr><td>浏览器管理</td><td><code>/api/getCoreVersions</code></td><td><span class="method-get">GET</span></td><td>获取本机已安装的 Chromium 内核版本</td></tr>
          <tr><td>浏览器管理</td><td><code>/api/addBrowser</code></td><td><span class="method-post">POST</span></td><td>创建浏览器环境（自动生成逼真指纹）</td></tr>
          <tr><td>浏览器管理</td><td><code>/api/updateBrowser</code></td><td><span class="method-post">POST</span></td><td>更新指定环境配置</td></tr>
          <tr><td>浏览器管理</td><td><code>/api/deleteBrowser</code></td><td><span class="method-post">POST</span></td><td>删除指定环境（自动关闭运行窗口）</td></tr>
          <tr><td>浏览器管理</td><td><code>/api/launchBrowser</code></td><td><span class="method-post">POST</span></td><td>启动指定环境窗口并返回 debuggingPort 和 ws</td></tr>
          <tr><td>浏览器管理</td><td><code>/api/stopBrowser</code></td><td><span class="method-post">POST</span></td><td>关闭指定环境窗口</td></tr>
          <tr><td>分组管理</td><td><code>/api/getGroupList</code></td><td><span class="method-get">GET</span></td><td>获取所有分组列表</td></tr>
          <tr><td>分组管理</td><td><code>/api/addGroup</code></td><td><span class="method-post">POST</span></td><td>创建新环境分组</td></tr>
          <tr><td>分组管理</td><td><code>/api/updateGroup</code></td><td><span class="method-post">POST</span></td><td>更新分组名称</td></tr>
          <tr><td>分组管理</td><td><code>/api/deleteGroup</code></td><td><span class="method-post">POST</span></td><td>删除指定分组</td></tr>
          <tr><td>插件管理</td><td><code>/api/getCrxList</code></td><td><span class="method-get">GET</span></td><td>获取已注册插件列表</td></tr>
          <tr><td>插件管理</td><td><code>/api/addCrx</code></td><td><span class="method-post">POST</span></td><td>注册/安装扩展插件</td></tr>
          <tr><td>插件管理</td><td><code>/api/deleteCrx</code></td><td><span class="method-post">POST</span></td><td>卸载扩展插件</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>"""
    return HTMLResponse(content=html)


# ============================================================
# 1. 浏览器管理接口
# ============================================================


@app.get("/api/getBrowserList")
@app.post("/api/getBrowserList")
async def get_browser_list(request: Request):
    """获取浏览器环境列表（兼容 GET 与 POST）"""
    core.clean_dead_browsers()
    params: Dict[str, Any] = {}
    if request.method == "POST":
        try:
            params = await request.json()
        except Exception:
            params = {}
    else:
        params = dict(request.query_params)

    data = core.read_virtual_dat()
    users: List[Dict[str, Any]] = data.get("users", [])

    # Filter by group
    group_filter = str(params.get("groupId") or params.get("group") or "").strip()
    if group_filter and group_filter.lower() not in ("all", "*", "0", ""):
        filtered = []
        for u in users:
            u_groups = [str(g).strip() for g in u.get("group", [])]
            if group_filter in u_groups or group_filter in [str(u.get("groupId")), str(u.get("group_id"))]:
                filtered.append(u)
        users = filtered

    # Filter by name/keyword
    kw = str(params.get("name") or params.get("keyword") or params.get("title") or "").strip().lower()
    if kw:
        users = [u for u in users if kw in str(u.get("name", "")).lower() or kw in str(u.get("id", ""))]

    # Augment running state
    running_ids = set(core.running_browsers.keys())
    for u in users:
        uid = str(u.get("id"))
        u["isRunning"] = uid in running_ids

    # Pagination
    page = int(params.get("page", 1))
    page_size = int(params.get("pageSize") or params.get("limit") or 0)
    total = len(users)

    if page_size > 0:
        start = (page - 1) * page_size
        users = users[start : start + page_size]

    res = api_success(users)
    res["total"] = total
    return res


@app.get("/api/getBrowserFullParameters")
async def get_browser_full_parameters(id: Union[int, str] = Query(...)):
    """获取环境完整参数"""
    target_id = str(id).strip()
    data = core.read_virtual_dat()
    for u in data.get("users", []):
        if str(u.get("id")).strip() == target_id:
            return api_success(u)
    return api_error(f"未找到环境 ID={id}", code=404)


@app.get("/api/getBrowserRunningList")
async def get_browser_running_list():
    """获取当前运行中的浏览器列表"""
    core.clean_dead_browsers()
    running_list = [b.to_dict() for b in core.running_browsers.values()]
    return api_success(running_list)


@app.get("/api/getCoreVersions")
async def get_core_version_list():
    """获取已有内核版本"""
    try:
        versions = core.get_core_versions()
        return api_success(versions)
    except Exception as e:
        return api_error(str(e))


@app.post("/api/addBrowser")
async def add_browser(request: Request):
    """创建浏览器环境"""
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    data = core.read_virtual_dat()
    users: List[Dict[str, Any]] = data.get("users", [])

    max_id = 0
    for u in users:
        try:
            max_id = max(max_id, int(u.get("id", 0)))
        except (ValueError, TypeError):
            pass
    new_id = max_id + 1

    name = payload.get("name")
    group_name = "默认分组"
    if payload.get("group") and isinstance(payload.get("group"), list) and payload["group"]:
        group_name = str(payload["group"][0])

    item = core.generate_default_browser_config(new_id=new_id, name=name, group_name=group_name)

    # Merge user overrides
    for k, v in payload.items():
        if k not in ("id", "createdAt"):
            item[k] = v
    item["id"] = new_id

    users.append(item)
    data["users"] = users
    core.write_virtual_dat(data)
    core.sync_worker_profile_files(new_id)

    return api_success({"id": new_id, "name": item["name"]}, msg="创建成功")


@app.post("/api/updateBrowser")
async def update_browser(request: Request):
    """更新浏览器配置"""
    try:
        payload = await request.json()
    except Exception:
        return api_error("无效的 JSON 请求体")

    bid = payload.get("id")
    if bid is None:
        return api_error("缺少 id 参数")

    str_id = str(bid).strip()
    data = core.read_virtual_dat()
    users: List[Dict[str, Any]] = data.get("users", [])

    found = False
    for i, u in enumerate(users):
        if str(u.get("id")).strip() == str_id:
            for k, v in payload.items():
                if k != "id":
                    u[k] = v
            u["timestamp"] = int(time.time() * 1000)
            users[i] = u
            found = True
            break

    if not found:
        return api_error(f"未找到环境 ID={bid}")

    data["users"] = users
    core.write_virtual_dat(data)
    core.sync_worker_profile_files(str_id)

    return api_success({"id": bid}, msg="更新成功")


@app.post("/api/deleteBrowser")
async def delete_browser(request: Request):
    """删除浏览器环境"""
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    bid = payload.get("id")
    if bid is None:
        return api_error("缺少 id 参数")

    str_id = str(bid).strip()
    await core.do_stop_browser(str_id)

    data = core.read_virtual_dat()
    users = [u for u in data.get("users", []) if str(u.get("id")).strip() != str_id]
    data["users"] = users
    core.write_virtual_dat(data)

    return api_success({"id": bid}, msg="删除成功")


@app.post("/api/launchBrowser")
async def launch_browser(request: Request):
    """启动浏览器环境并返回调试端口和 WebSocket 连接地址"""
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    bid = payload.get("id")
    if bid is None:
        return api_error("缺少 id 参数")

    res = await core.do_launch_browser(
        bid=bid,
        url=payload.get("url"),
        headless=payload.get("headless", False),
        extra_args=payload.get("args"),
    )

    if res.get("success"):
        return api_success(res["data"], msg=res.get("msg", "启动成功"))
    return api_error(res.get("msg", "启动失败"))


@app.post("/api/stopBrowser")
async def stop_browser(request: Request):
    """关闭指定的浏览器环境"""
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    bid = payload.get("id")
    if bid is None:
        return api_error("缺少 id 参数")

    res = await core.do_stop_browser(bid)
    if res.get("success"):
        return api_success(msg=res.get("msg", "关闭成功"))
    return api_error(res.get("msg", "关闭失败"))


# ============================================================
# 2. 分组管理接口
# ============================================================


@app.get("/api/getGroupList")
async def get_group_list():
    """获取所有环境分组"""
    g_data = core.read_global_dat()
    groups = g_data.get("group", [])
    return api_success(groups)


@app.post("/api/addGroup")
async def add_group(request: Request):
    """创建新分组"""
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    name = str(payload.get("name") or "").strip()
    if not name:
        return api_error("分组名称不能为空")

    g_data = core.read_global_dat()
    groups: List[Dict[str, Any]] = g_data.get("group", [])

    max_id = 0
    for g in groups:
        try:
            max_id = max(max_id, int(g.get("id", 0)))
        except (ValueError, TypeError):
            pass
    new_id = max_id + 1

    new_group = {
        "id": new_id,
        "name": name,
        "timestamp": int(time.time() * 1000),
    }
    groups.append(new_group)
    g_data["group"] = groups
    core.write_global_dat(g_data)

    return api_success(new_group, msg="创建分组成功")


@app.post("/api/updateGroup")
async def update_group(request: Request):
    """更新分组名称"""
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    gid = payload.get("id")
    name = str(payload.get("name") or "").strip()
    if gid is None or not name:
        return api_error("缺少 id 或 name 参数")

    str_id = str(gid).strip()
    g_data = core.read_global_dat()
    groups = g_data.get("group", [])

    found = False
    for g in groups:
        if str(g.get("id")).strip() == str_id:
            g["name"] = name
            found = True
            break

    if not found:
        return api_error(f"未找到分组 ID={gid}")

    g_data["group"] = groups
    core.write_global_dat(g_data)
    return api_success({"id": gid, "name": name}, msg="更新分组成功")


@app.post("/api/deleteGroup")
async def delete_group(request: Request):
    """删除分组"""
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    gid = payload.get("id")
    if gid is None:
        return api_error("缺少 id 参数")

    str_id = str(gid).strip()
    g_data = core.read_global_dat()
    groups = [g for g in g_data.get("group", []) if str(g.get("id")).strip() != str_id]
    g_data["group"] = groups
    core.write_global_dat(g_data)

    return api_success({"id": gid}, msg="删除分组成功")


# ============================================================
# 3. 插件管理接口
# ============================================================


@app.get("/api/getCrxList")
async def get_crx_list():
    """获取已安装扩展插件列表"""
    exts = core.read_extensions_dat()
    return api_success(exts)


@app.post("/api/addCrx")
async def add_crx(request: Request):
    """注册或添加扩展插件"""
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    path = str(payload.get("path") or "").strip()
    name = str(payload.get("name") or Path(path).name).strip()
    if not path or not Path(path).exists():
        return api_error(f"插件路径无效或不存在: {path}")

    exts = core.read_extensions_dat()
    ext_id = str(payload.get("id") or abs(hash(path)) % 100000)

    for e in exts:
        if e.get("id") == ext_id or e.get("path") == path:
            e["name"] = name
            e["path"] = path
            e["enabled"] = payload.get("enabled", True)
            core.write_extensions_dat(exts)
            return api_success(e, msg="插件已更新")

    new_ext = {
        "id": ext_id,
        "name": name,
        "path": path,
        "enabled": payload.get("enabled", True),
        "version": payload.get("version", "1.0.0"),
        "createdAt": int(time.time() * 1000),
    }
    exts.append(new_ext)
    core.write_extensions_dat(exts)

    return api_success(new_ext, msg="插件安装成功")


@app.post("/api/deleteCrx")
async def delete_crx(request: Request):
    """卸载扩展插件"""
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    eid = payload.get("id")
    if not eid:
        return api_error("缺少 id 参数")

    str_id = str(eid).strip()
    exts = core.read_extensions_dat()
    new_exts = [e for e in exts if str(e.get("id")).strip() != str_id]
    core.write_extensions_dat(new_exts)

    return api_success({"id": eid}, msg="插件卸载成功")


# ============================================================
# Main Entry Point
# ============================================================

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    host = "0.0.0.0"
    port = int(os.environ.get("VB_API_PORT", 9000))
    print("=" * 65)
    print("   🌐 VirtualBrowser 免 VIP 本地 API & MCP 服务正在启动...")
    print(f"   [*] 监听地址: http://127.0.0.1:{port}")
    print(f"   [*] 接口文档: http://127.0.0.1:{port}/docs")
    print(f"   [*] MCP 端点: http://127.0.0.1:{port}/sse")
    print(f"   [*] 数据目录: {core.VB_USER_DATA_DIR}")
    print(f"   [*] 内核路径: {core.find_browser_executable()}")
    print("=" * 65)
    uvicorn.run(app, host=host, port=port, log_level="info")
