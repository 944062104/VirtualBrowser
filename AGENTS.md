# VirtualBrowser Agent Guide

## 1. 项目定位
- 针对 VirtualBrowser 指纹浏览器的本地开放 API、MCP 服务与自动化管理框架（完全免费、免 VIP 限制）。

## 2. 服务与接口
- **核心服务入口**：`api_server/server.py`（FastAPI + Uvicorn）。
- **REST API 端口**：`http://127.0.0.1:9000`。
- **MCP SSE 端点**：`http://127.0.0.1:9000/sse`（可直接接入 Antigravity / Claude 等 AI Agent）。
- **Web 控制台**：`http://127.0.0.1:9000/`，接口文档 `http://127.0.0.1:9000/docs`。

## 3. 开发与运维约定
- 启动：`python api_server/server.py`。
- 关闭窗口/浏览器时必须通过 CDP `Browser.close` 优雅退出，确保 Chromium SQLite Cookies 与会话文件刷盘落盘。
- 数据根目录优先使用环境变量 `VB_DATA_DIR`，默认位于系统的 `%LOCALAPPDATA%/VirtualBrowser`。
- ChatGPT 账号池自动化统一 Skill 位于 `D:\code\github\fpbrowser2api\skills\chatgpt-account-pool`（支持 TOTP 2FA 与微软 OAuth 邮件接码双模入池）。
