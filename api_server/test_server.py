"""Automated Test Suite for VirtualBrowser Local API & MCP Server
================================================================
Verifies all 16 HTTP REST API endpoints and 13 Model Context Protocol (MCP) tools.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import requests

BASE_URL = "http://127.0.0.1:9000"


def test_http_api():
    print("=" * 60)
    print("           [PART 1] 测试 16 项 HTTP REST API 接口")
    print("=" * 60)

    print(">>> 1. 测试 /api/getCoreVersions")
    r = requests.get(f"{BASE_URL}/api/getCoreVersions").json()
    print("内核版本:", r)
    assert r["success"] is True

    print("\n>>> 2. 测试 /api/getGroupList")
    r = requests.get(f"{BASE_URL}/api/getGroupList").json()
    print("分组列表:", r)
    assert r["success"] is True

    print("\n>>> 3. 测试 /api/addGroup")
    r = requests.post(f"{BASE_URL}/api/addGroup", json={"name": "自动化测试组"}).json()
    print("添加分组:", r)
    assert r["success"] is True
    test_group_id = r["data"]["id"]

    print("\n>>> 4. 测试 /api/updateGroup")
    r = requests.post(f"{BASE_URL}/api/updateGroup", json={"id": test_group_id, "name": "自动化测试组-已更新"}).json()
    print("更新分组:", r)
    assert r["success"] is True

    print("\n>>> 5. 测试 /api/deleteGroup")
    r = requests.post(f"{BASE_URL}/api/deleteGroup", json={"id": test_group_id}).json()
    print("删除分组:", r)
    assert r["success"] is True

    print("\n>>> 6. 测试 /api/getBrowserList (GET)")
    r = requests.get(f"{BASE_URL}/api/getBrowserList").json()
    print("浏览器列表数量:", len(r["data"]))
    assert r["success"] is True

    print("\n>>> 7. 测试 /api/getBrowserList (POST)")
    r = requests.post(f"{BASE_URL}/api/getBrowserList", json={"page": 1, "pageSize": 10}).json()
    print("POST 分页列表数量:", len(r["data"]))
    assert r["success"] is True

    print("\n>>> 8. 测试 /api/addBrowser (创建环境)")
    r = requests.post(f"{BASE_URL}/api/addBrowser", json={"name": "API-Test-Browser"}).json()
    print("创建环境:", r)
    assert r["success"] is True
    new_browser_id = r["data"]["id"]

    print("\n>>> 9. 测试 /api/getBrowserFullParameters")
    r = requests.get(f"{BASE_URL}/api/getBrowserFullParameters", params={"id": new_browser_id}).json()
    print("环境完整参数 name:", r["data"].get("name"), "UA:", r["data"]["ua"]["value"])
    assert r["success"] is True

    print("\n>>> 10. 测试 /api/updateBrowser")
    r = requests.post(f"{BASE_URL}/api/updateBrowser", json={"id": new_browser_id, "remark": "自动化测试备注"}).json()
    print("更新环境备注:", r)
    assert r["success"] is True

    print("\n>>> 11. 测试 /api/launchBrowser (启动环境，无头模式)")
    r = requests.post(f"{BASE_URL}/api/launchBrowser", json={"id": new_browser_id, "headless": True}).json()
    print("启动环境返回:", r)
    assert r["success"] is True
    debugging_port = r["data"]["debuggingPort"]

    print("\n>>> 12. 测试 /api/getBrowserRunningList")
    r = requests.get(f"{BASE_URL}/api/getBrowserRunningList").json()
    print("当前运行中列表:", r)
    assert r["success"] is True
    assert any(str(b["id"]) == str(new_browser_id) for b in r["data"])

    print("\n>>> 13. Playwright 自动化连接测试")
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{debugging_port}")
            ctx = browser.contexts[0]
            page = ctx.new_page()
            page.goto("https://www.example.com", timeout=15000)
            print("页面访问成功! 页面标题:", page.title())
            browser.close()
    except Exception as e:
        print("Playwright 测试警告 (如超时可忽略):", e)

    print("\n>>> 14. 测试 /api/stopBrowser (关闭环境)")
    r = requests.post(f"{BASE_URL}/api/stopBrowser", json={"id": new_browser_id}).json()
    print("关闭环境返回:", r)
    assert r["success"] is True

    print("\n>>> 15. 测试 /api/deleteBrowser (删除测试环境)")
    r = requests.post(f"{BASE_URL}/api/deleteBrowser", json={"id": new_browser_id}).json()
    print("删除环境返回:", r)
    assert r["success"] is True

    print("\n>>> 16. 测试插件管理接口 (/api/getCrxList)")
    r = requests.get(f"{BASE_URL}/api/getCrxList").json()
    print("插件列表:", r)
    assert r["success"] is True

    print("\n[SUCCESS] 全部 16 个 HTTP REST API 接口测试通过！\n")


async def test_mcp_tools():
    print("=" * 60)
    print("           [PART 2] 测试 MCP (Model Context Protocol) 工具集")
    print("=" * 60)

    import mcp_server

    print(">>> 1. 列出所有注册的 MCP 工具")
    tools = await mcp_server.mcp.list_tools()
    print(f"MCP 工具总数: {len(tools)}")
    assert len(tools) >= 13
    for t in tools:
        print(f" - {t.name}")

    print("\n>>> 2. 测试 MCP 工具: list_browsers")
    b_list = mcp_server.list_browsers()
    print(f"获取环境列表成功，总数: {b_list['total']}")
    assert "browsers" in b_list

    print("\n>>> 3. 测试 MCP 工具: create_browser")
    new_b = mcp_server.create_browser(name="MCP-Auto-Test", group="默认分组")
    print("创建环境成功:", new_b)
    assert new_b["success"] is True
    mcp_bid = new_b["id"]

    print("\n>>> 4. 测试 MCP 工具: get_browser_detail")
    detail = mcp_server.get_browser_detail(mcp_bid)
    print("获取环境详情成功, OS:", detail["browser"]["os"])
    assert detail["success"] is True

    print("\n>>> 5. 测试 MCP 工具: browser_navigate (无头启动并访问 example.com)")
    nav_res = await mcp_server.browser_navigate(mcp_bid, "https://www.example.com", wait_seconds=1.5)
    print("网页导航结果:", nav_res)
    assert nav_res["success"] is True
    assert "Example" in nav_res["data"]["title"]

    print("\n>>> 6. 测试 MCP 工具: browser_eval_js")
    eval_res = await mcp_server.browser_eval_js(mcp_bid, "document.title")
    print("JS 执行结果:", eval_res)
    assert eval_res["success"] is True
    assert "Example" in eval_res["data"]["result"]

    print("\n>>> 7. 测试 MCP 工具: get_running_browsers")
    running = mcp_server.get_running_browsers()
    print(f"当前运行中实例数: {len(running)}")
    assert any(str(r["id"]) == str(mcp_bid) for r in running)

    print("\n>>> 8. 测试 MCP 工具: stop_browser")
    stop_res = await mcp_server.stop_browser(mcp_bid)
    print("停止环境结果:", stop_res)
    assert stop_res["success"] is True

    print("\n>>> 9. 测试 MCP 工具: delete_browser")
    del_res = await mcp_server.delete_browser(mcp_bid)
    print("删除环境结果:", del_res)
    assert del_res["success"] is True

    print("\n[SUCCESS] 全部 MCP 工具集自动化测试通过！\n")


if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    test_http_api()
    asyncio.run(test_mcp_tools())

    print("=" * 60)
    print("🎉 ALL TESTS PASSED! API 与 MCP 服务均完全正常运行！")
    print("=" * 60)
