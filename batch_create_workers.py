"""VirtualBrowser 批量环境创建与 FPBrowser2API 同步脚本
=============================================================
支持自定义：创建数量、命名规则、统一代理/独立代理列表、默认主页，
并在创建完成后自动同步到 FPBrowser2API 调度池。
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error

VB_BASE = "http://127.0.0.1:9000"
FPB_BASE = "http://127.0.0.1:8000"

def http_post(url, data=None, headers=None):
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=json.dumps(data or {}).encode(), headers=h)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())

def batch_create(
    count: int = 5,
    name_prefix: str = "ChatGPT-Worker",
    group_name: str = "默认分组",
    proxy_mode: int = 1,
    proxy_host: str = "127.0.0.1",
    proxy_port: str = "7890",
    proxy_proto: str = "HTTP",
    proxy_list: list = None,
    homepage: str = "https://chatgpt.com",
    sync_to_fpb: bool = True,
):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 65)
    print(f"[*] 开始批量创建 {count} 个 VirtualBrowser 环境...")
    print(f"[*] 命名格式: {name_prefix}-<序号> | 分组: {group_name}")
    print(f"[*] 默认主页: {homepage or '(空)'}")
    print("=" * 65)

    created_ids = []

    for i in range(1, count + 1):
        # 确定代理配置
        cur_proxy = {"mode": 0, "value": "", "protocol": "HTTP", "host": "", "port": "", "user": "", "pass": "", "API": ""}
        if proxy_list and len(proxy_list) >= i:
            p_item = proxy_list[i - 1]
            # p_item 格式支持 "host:port" 或 "host:port:user:pass"
            parts = str(p_item).strip().split(":")
            if len(parts) >= 2:
                h, p = parts[0], parts[1]
                u = parts[2] if len(parts) > 2 else ""
                pwd = parts[3] if len(parts) > 3 else ""
                cur_proxy = {
                    "mode": 1,
                    "value": f"{h}:{p}",
                    "protocol": proxy_proto,
                    "host": h,
                    "port": p,
                    "user": u,
                    "pass": pwd,
                    "API": "",
                }
        elif proxy_mode != 0 and proxy_host and proxy_port:
            cur_proxy = {
                "mode": proxy_mode,
                "value": f"{proxy_host}:{proxy_port}",
                "protocol": proxy_proto,
                "host": proxy_host,
                "port": proxy_port,
                "user": "",
                "pass": "",
                "API": "",
            }

        payload = {
            "name": f"{name_prefix}-{i}",
            "group": [group_name],
            "homepage": {"mode": 0 if not homepage else 1, "value": homepage},
            "proxy": cur_proxy,
        }

        try:
            res = http_post(f"{VB_BASE}/api/addBrowser", payload)
            if res.get("success"):
                new_id = res["data"]["id"]
                created_ids.append(new_id)
                proxy_str = f"{cur_proxy['host']}:{cur_proxy['port']}" if cur_proxy.get("mode") else "直连"
                print(f"  [+] 成功创建环境 ID={new_id:<3} | 名称: {payload['name']} | 代理: {proxy_str}")
            else:
                print(f"  [-] 创建环境 {payload['name']} 失败: {res.get('msg')}")
        except Exception as e:
            print(f"  [-] 请求 /api/addBrowser 异常: {e}")

    print("\n" + "-" * 65)
    print(f"[+] 批量创建完成，共成功创建 {len(created_ids)} 个环境: {created_ids}")

    # 同步至 FPBrowser2API
    if sync_to_fpb and created_ids:
        print("\n[*] 正在自动同步至 FPBrowser2API 任务调度池...")
        try:
            login_res = http_post(f"{FPB_BASE}/api/admin/login", {"username": "admin", "password": "admin"})
            token = login_res.get("token")
            headers = {"Authorization": f"Bearer {token}"}
            sync_res = http_post(f"{FPB_BASE}/api/admin/spaces/5/sync-windows", {}, headers=headers)
            print(f"  [+] FPBrowser2API 同步成功: {sync_res.get('message')}")
        except Exception as e:
            print(f"  [!] 同步至 FPBrowser2API 提示: {e}（请确保 FPBrowser2API 服务处于启动状态）")

    print("=" * 65)
    return created_ids

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量创建 VirtualBrowser 浏览器环境")
    parser.add_argument("-n", "--count", type=int, default=5, help="创建数量 (默认: 5)")
    parser.add_argument("-p", "--prefix", type=str, default="ChatGPT-Worker", help="名称前缀 (默认: ChatGPT-Worker)")
    parser.add_argument("-g", "--group", type=str, default="默认分组", help="所属分组 (默认: 默认分组)")
    parser.add_argument("--proxy-host", type=str, default="127.0.0.1", help="代理IP (默认: 127.0.0.1)")
    parser.add_argument("--proxy-port", type=str, default="7890", help="代理端口 (默认: 7890)")
    parser.add_argument("--direct", action="store_true", help="不使用代理 (直连)")
    parser.add_argument("--url", type=str, default="https://chatgpt.com", help="默认主页 (默认: https://chatgpt.com)")
    parser.add_argument("--no-sync", action="store_true", help="不同步至 FPBrowser2API")
    args = parser.parse_args()

    batch_create(
        count=args.count,
        name_prefix=args.prefix,
        group_name=args.group,
        proxy_mode=0 if args.direct else 1,
        proxy_host="" if args.direct else args.proxy_host,
        proxy_port="" if args.direct else args.proxy_port,
        homepage=args.url,
        sync_to_fpb=not args.no_sync,
    )
