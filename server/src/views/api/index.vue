<template>
  <div class="api-container">
    <!-- 顶部状态卡片 -->
    <el-card class="status-card" shadow="hover">
      <div slot="header" class="clearfix">
        <span class="card-title">
          <i class="el-icon-connection" style="color: #409eff; margin-right: 8px;"></i>
          VirtualBrowser 本地 API 与 MCP 服务 (完全免费 / 永久开放)
        </span>
        <el-tag :type="serverOnline ? 'success' : 'danger'" effect="dark" size="small" style="float: right;">
          {{ serverOnline ? '服务运行中 (端口 9000)' : '未检测到服务 (请先启动服务)' }}
        </el-tag>
      </div>

      <el-row :gutter="20">
        <el-col :span="8">
          <div class="info-block">
            <div class="label">HTTP REST API 基础地址</div>
            <div class="value-row">
              <span class="code-text">{{ apiUrl }}</span>
              <el-button type="text" icon="el-icon-document-copy" @click="handleCopy(apiUrl)">复制</el-button>
            </div>
            <div class="sub-tip">可用于 Playwright、Python、Node.js 自动化调度与环境管理</div>
          </div>
        </el-col>

        <el-col :span="8">
          <div class="info-block">
            <div class="label">MCP (Model Context Protocol) 端点</div>
            <div class="value-row">
              <span class="code-text">{{ mcpUrl }}</span>
              <el-button type="text" icon="el-icon-document-copy" @click="handleCopy(mcpUrl)">复制</el-button>
            </div>
            <div class="sub-tip">适用于 Cursor、Claude Desktop、Antigravity 等 AI 智能体接入</div>
          </div>
        </el-col>

        <el-col :span="8">
          <div class="info-block">
            <div class="label">快捷操作</div>
            <div style="margin-top: 10px;">
              <el-button type="primary" size="small" icon="el-icon-document" @click="openDocs">Swagger 接口文档</el-button>
              <el-button type="success" size="small" icon="el-icon-refresh" @click="checkServerStatus">刷新状态</el-button>
            </div>
            <div class="sub-tip">本地服务启动脚本：api_server/start_api.bat</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 标签页：MCP 配置指南 / API 接口列表 -->
    <el-tabs v-model="activeTab" type="border-card" style="margin-top: 20px;">
      <!-- Tab 1: MCP 智能体接入配置 -->
      <el-tab-pane label="🤖 MCP (AI 智能体) 接入配置" name="mcp">
        <el-alert
          title="无需付费 VIP，本地 MCP 服务已完整封装指纹浏览器管理及 Playwright CDP 自动化控制能力！"
          type="success"
          :closable="false"
          show-icon
          style="margin-bottom: 20px;"
        />

        <h3>1. Cursor / Claude Desktop / Antigravity 配置方法</h3>
        <p class="desc-text">在 AI 编辑器或客户端的 MCP 配置文件（如 <code>claude_desktop_config.json</code>）中填入以下配置即可：</p>

        <div class="code-box">
          <div class="code-header">
            <span>Stdio 模式配置代码（推荐）</span>
            <el-button type="text" size="mini" icon="el-icon-document-copy" @click="handleCopy(mcpConfigJson)">复制配置</el-button>
          </div>
          <pre><code>{{ mcpConfigJson }}</code></pre>
        </div>

        <h3 style="margin-top: 24px;">2. MCP 提供的工具列表 (已实现 13 项工具)</h3>
        <el-table :data="mcpTools" border stripe size="small" style="width: 100%; margin-top: 12px;">
          <el-table-column prop="name" label="工具名称 (Tool Name)" width="220">
            <template slot-scope="scope">
              <code>{{ scope.row.name }}</code>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="功能说明" min-width="260" />
          <el-table-column prop="params" label="主要参数" min-width="220" />
        </el-table>
      </el-tab-pane>

      <!-- Tab 2: HTTP REST API 列表 -->
      <el-tab-pane label="⚡ HTTP REST API 接口清单 (全 16 项)" name="api">
        <el-alert
          title="所有接口返回统一 JSON 结构：{ success: true, code: 0, msg: '...', data: { ... } }"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 20px;"
        />

        <el-table :data="apiList" border stripe size="small" style="width: 100%;">
          <el-table-column prop="category" label="分类" width="130">
            <template slot-scope="scope">
              <el-tag size="mini">{{ scope.row.category }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="path" label="接口路径" width="280">
            <template slot-scope="scope">
              <code>{{ scope.row.path }}</code>
            </template>
          </el-table-column>
          <el-table-column prop="method" label="请求方式" width="120">
            <template slot-scope="scope">
              <el-tag :type="scope.row.method.includes('POST') ? 'success' : 'primary'" size="mini" effect="plain">
                {{ scope.row.method }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="接口描述" min-width="240" />
          <el-table-column prop="params" label="请求参数示例" min-width="220" />
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script>
export default {
  name: 'ApiService',
  data() {
    return {
      serverOnline: false,
      apiUrl: 'http://127.0.0.1:9000',
      mcpUrl: 'http://127.0.0.1:9000/sse',
      activeTab: 'mcp',
      mcpConfigJson: JSON.stringify(
        {
          mcpServers: {
            'virtual-browser': {
              command: 'python',
              args: ['E:\\openProject\\VirtualBrowser\\api_server\\mcp_server.py']
            }
          }
        },
        null,
        2
      ),
      mcpTools: [
        { name: 'list_browsers', description: '获取所有配置的环境列表及实时运行状态', params: 'group (可选), keyword (可选)' },
        { name: 'get_browser_detail', description: '获取指定环境的完整指纹项与配置详情', params: 'browser_id (必需)' },
        { name: 'get_running_browsers', description: '获取当前所有运行中的窗口、PID、CDP 端口及 WebSocket 地址', params: '无' },
        { name: 'launch_browser', description: '启动指定环境窗口，返回 CDP 远程调试连接信息', params: 'browser_id (必需), url, headless' },
        { name: 'stop_browser', description: '安全关闭指定的浏览器窗口', params: 'browser_id (必需)' },
        { name: 'create_browser', description: '创建全新指纹环境（自动生成高度真实的软硬件指纹）', params: 'name, group, homepage, proxy_*' },
        { name: 'update_browser', description: '修改指定环境的名称、备注或代理', params: 'browser_id (必需), name, remark, proxy_*' },
        { name: 'delete_browser', description: '删除环境并自动回收运行中的窗口', params: 'browser_id (必需)' },
        { name: 'list_groups', description: '获取所有浏览器分组', params: '无' },
        { name: 'create_group', description: '创建新的分组', params: 'name (必需)' },
        { name: 'browser_navigate', description: '在环境中打开网址（未启动时自动启动），返回页面标题与加载状态', params: 'browser_id (必需), url (必需), wait_seconds' },
        { name: 'browser_screenshot', description: '对当前活动页面截屏（支持保存本地或返回 Base64）', params: 'browser_id (必需), save_path' },
        { name: 'browser_eval_js', description: '在当前页面上下文中执行 JavaScript 脚本并返回结果', params: 'browser_id (必需), script (必需)' }
      ],
      apiList: [
        { category: '浏览器管理', path: '/api/getBrowserList', method: 'GET / POST', description: '获取浏览器列表（支持分页、关键词搜索、分组筛选）', params: 'page, pageSize, groupId, keyword' },
        { category: '浏览器管理', path: '/api/getBrowserFullParameters', method: 'GET', description: '获取环境完整参数（所有指纹与配置）', params: 'id (必需)' },
        { category: '浏览器管理', path: '/api/getBrowserRunningList', method: 'GET', description: '获取当前运行中的浏览器列表及 CDP 端口', params: '无' },
        { category: '浏览器管理', path: '/api/getCoreVersions', method: 'GET', description: '获取本机已安装的 Chromium 内核版本号', params: '无' },
        { category: '浏览器管理', path: '/api/addBrowser', method: 'POST', description: '创建浏览器环境（未填写的指纹参数自动生成）', params: '{ name, group, proxy, ... }' },
        { category: '浏览器管理', path: '/api/updateBrowser', method: 'POST', description: '更新指定环境配置', params: '{ id, name, proxy, ... }' },
        { category: '浏览器管理', path: '/api/deleteBrowser', method: 'POST', description: '删除指定环境（自动关闭正在运行的窗口）', params: '{ id }' },
        { category: '浏览器管理', path: '/api/launchBrowser', method: 'POST', description: '启动指定环境并返回 debuggingPort 和 ws 连接', params: '{ id, url, headless, args }' },
        { category: '浏览器管理', path: '/api/stopBrowser', method: 'POST', description: '关闭指定的浏览器窗口', params: '{ id }' },
        { category: '分组管理', path: '/api/getGroupList', method: 'GET', description: '获取所有分组列表', params: '无' },
        { category: '分组管理', path: '/api/addGroup', method: 'POST', description: '创建新环境分组', params: '{ name }' },
        { category: '分组管理', path: '/api/updateGroup', method: 'POST', description: '更新分组名称', params: '{ id, name }' },
        { category: '分组管理', path: '/api/deleteGroup', method: 'POST', description: '删除指定分组', params: '{ id }' },
        { category: '插件管理', path: '/api/getCrxList', method: 'GET', description: '获取已安装扩展插件列表', params: '无' },
        { category: '插件管理', path: '/api/addCrx', method: 'POST', description: '注册/安装扩展插件', params: '{ path, name, enabled }' },
        { category: '插件管理', path: '/api/deleteCrx', method: 'POST', description: '卸载扩展插件', params: '{ id }' }
      ]
    }
  },
  mounted() {
    this.checkServerStatus()
  },
  methods: {
    async checkServerStatus() {
      try {
        const res = await fetch(`${this.apiUrl}/api/getCoreVersions`, { method: 'GET' })
        if (res.ok) {
          this.serverOnline = true
          this.$message.success('本地 API & MCP 服务连接成功 (9000 端口)')
        } else {
          this.serverOnline = false
        }
      } catch (e) {
        this.serverOnline = false
      }
    },
    handleCopy(text) {
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
          this.$message.success('已复制到剪贴板')
        })
      } else {
        const input = document.createElement('input')
        input.value = text
        document.body.appendChild(input)
        input.select()
        document.execCommand('copy')
        document.body.removeChild(input)
        this.$message.success('已复制到剪贴板')
      }
    },
    openDocs() {
      window.open(`${this.apiUrl}/docs`, '_blank')
    }
  }
}
</script>

<style scoped>
.api-container {
  padding: 20px;
  background-color: #f0f2f5;
  min-height: calc(100vh - 84px);
}
.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.info-block {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
}
.label {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 8px;
}
.value-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.code-text {
  font-family: Consolas, Monaco, monospace;
  font-weight: 600;
  color: #0284c7;
  font-size: 14px;
}
.sub-tip {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 8px;
}
.desc-text {
  color: #606266;
  font-size: 14px;
  margin: 10px 0;
}
.code-box {
  background: #1e293b;
  border-radius: 8px;
  padding: 12px 16px;
  margin: 12px 0;
}
.code-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #334155;
  padding-bottom: 8px;
  margin-bottom: 8px;
  color: #94a3b8;
  font-size: 13px;
}
pre {
  margin: 0;
  color: #38bdf8;
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
  line-height: 1.5;
  overflow-x: auto;
}
code {
  font-family: Consolas, Monaco, monospace;
  background: #f1f5f9;
  color: #0369a1;
  padding: 2px 6px;
  border-radius: 4px;
}
pre code {
  background: transparent;
  padding: 0;
}
</style>
