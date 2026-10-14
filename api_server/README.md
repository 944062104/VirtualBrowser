# VirtualBrowser 本地 API 与 MCP 服务 (完全开放 / 免 VIP)

本项目为 **VirtualBrowser** 提供完全开放、无 VIP 限制的本地服务，包括：
1. **全功能 HTTP REST API 服务**（完整覆盖官方 16 个接口，端口默认 `9000`）
2. **标准 Model Context Protocol (MCP) 服务**（内置 13 项环境管理与网页自动化工具，支持 Cursor / Claude Desktop / Antigravity 等 AI 客户端接入）
3. **Web 控制看板与 Swagger 交互式文档**（`http://127.0.0.1:9000/` 与 `http://127.0.0.1:9000/docs`）

---

## 🚀 快速启动

### 方式 1：双击批处理一键启动（推荐）
直接双击运行 `start_api.bat`。

### 方式 2：命令行启动
```bash
cd api_server
python server.py
```

服务就绪后：
- **Web 服务看板**：[http://127.0.0.1:9000/](http://127.0.0.1:9000/)
- **Swagger 交互式文档**：[http://127.0.0.1:9000/docs](http://127.0.0.1:9000/docs)
- **MCP SSE 协议端点**：`http://127.0.0.1:9000/sse`

---

## 🤖 MCP (Model Context Protocol) 接入配置

本服务使用官方 Python MCP 规范开发，提供两种运行连接模式：

### 模式 A：标准 Stdio 模式（推荐）
直接在各大 AI 编辑器与工具的 MCP 配置文件中填入：

```json
{
  "mcpServers": {
    "virtual-browser": {
      "command": "python",
      "args": ["<VirtualBrowser路径>\\api_server\\mcp_server.py"]
    }
  }
}
```

- **Claude Desktop**：编辑 `%APPDATA%\Claude\claude_desktop_config.json`
- **Cursor**：在 Settings -> Features -> MCP 中添加 `virtual-browser`
- **Antigravity / Cline**：在 MCP 配置界面添加 Command 为 `python`，Args 为 `["<VirtualBrowser路径>\\api_server\\mcp_server.py"]`

### 模式 B：HTTP / SSE 模式
启动 `server.py` 后，MCP 客户端直接连接：
```
http://127.0.0.1:9000/sse
```

### 🛠️ 已实现的 13 项 MCP 工具清单

| MCP 工具名 | 说明 | 参数 |
|---|---|---|
| `list_browsers` | 查询所有已配置指纹浏览器及实时运行状态 | `group` (可选), `keyword` (可选) |
| `get_browser_detail` | 获取指定环境完整指纹配置（UA、分辨率、Canvas、WebGL、音频等） | `browser_id` (必需) |
| `get_running_browsers` | 获取当前所有活动窗口、PID、CDP 端口及 WebSocket 调试地址 | 无 |
| `launch_browser` | 启动指定环境窗口，并返回 CDP 调试端口与 WS 地址 | `browser_id` (必需), `url`, `headless` |
| `stop_browser` | 安全关闭指定环境窗口 | `browser_id` (必需) |
| `create_browser` | 创建全新环境（自动生成高度真实的软硬件指纹） | `name`, `group`, `homepage`, `proxy_*` |
| `update_browser` | 修改现有环境名称、备注或代理 | `browser_id` (必需), `name`, `remark`, `proxy_*` |
| `delete_browser` | 删除环境配置，并自动关闭运行中的窗口 | `browser_id` (必需) |
| `list_groups` | 获取所有分组列表 | 无 |
| `create_group` | 创建新的环境分组 | `name` (必需) |
| `browser_navigate` | 打开网页（未启动时自动启动），返回页面标题与加载状态 | `browser_id` (必需), `url` (必需), `wait_seconds` |
| `browser_screenshot` | 对当前页面截图（支持保存文件或返回 Base64 编码） | `browser_id` (必需), `save_path` |
| `browser_eval_js` | 在当前页面上下文执行 JavaScript 代码并返回结果 | `browser_id` (必需), `script` (必需) |

---

## ⚡ HTTP REST API 接口清单 (全 16 项)

所有接口统一返回规范：
```json
{
  "success": true,
  "code": 0,
  "msg": "success",
  "data": { ... }
}
```

### 1. 浏览器环境管理
- **获取浏览器列表**：`GET /api/getBrowserList` 或 `POST /api/getBrowserList`  
  支持参数：`page`, `pageSize`, `groupId`, `keyword`
- **获取环境完整参数**：`GET /api/getBrowserFullParameters?id=1`
- **获取运行中的浏览器列表**：`GET /api/getBrowserRunningList`
- **获取内核版本**：`GET /api/getCoreVersions`
- **创建浏览器**：`POST /api/addBrowser`
- **更新浏览器**：`POST /api/updateBrowser`
- **删除浏览器**：`POST /api/deleteBrowser`
- **启动浏览器**：`POST /api/launchBrowser`  
  请求体：`{"id": 1, "url": "https://chatgpt.com", "headless": false}`  
  返回：`debuggingPort`, `ws`, `pid`
- **关闭浏览器**：`POST /api/stopBrowser`  
  请求体：`{"id": 1}`

### 2. 分组管理
- **获取分组列表**：`GET /api/getGroupList`
- **创建分组**：`POST /api/addGroup`，参数：`{"name": "分组名称"}`
- **更新分组**：`POST /api/updateGroup`，参数：`{"id": 1, "name": "新名称"}`
- **删除分组**：`POST /api/deleteGroup`，参数：`{"id": 1}`

### 3. 插件管理
- **获取插件列表**：`GET /api/getCrxList`
- **安装插件**：`POST /api/addCrx`，参数：`{"path": "D:/ext/demo", "name": "扩展名"}`
- **卸载插件**：`POST /api/deleteCrx`，参数：`{"id": "..."}`

---

## 🧪 自动化测试验证

运行目录下的端到端测试套件：
```bash
python test_server.py
```
一键验证全部 16 个 REST API 接口以及全部 13 个 MCP 工具，包括 Playwright CDP 连接与实际网页导航。
