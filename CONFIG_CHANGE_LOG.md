# 配置变更日志 - 2026-03-24

## 变更内容

### 1. 创建架构师2独立配置
- ✅ 创建 Agent 配置目录：`/Users/variya/.openclaw/agents/architect2/`
- ✅ 创建独立环境文件：`architect2/.env` (nvidia-key3)
- ✅ 创建独立模型配置：`architect2/agent/models.json` (使用环境变量)
- ✅ 创建角色定义：`architect2/agent/SOUL.md`
- ✅ 工作区：`workspace-architect2` (已存在)

### 2. API密钥分离（环境变量化）
**之前**: 所有硬编码在 models.json 中，多个 key 混在一起
**现在**: 每个 Agent 独立 `.env` 文件

| Agent | NVIDIA API Key | 配额 | .env 路径 |
|-------|----------------|------|-----------|
| researcher | nvidia-key1 | 40 RPM | /Users/variya/.openclaw/agents/researcher/.env |
| architect1 | nvidia-key2 | 40 RPM | /Users/variya/.openclaw/agents/architect/.env |
| architect2 | nvidia-key3 | 40 RPM | /Users/variya/.openclaw/agents/architect2/.env |
| critic | nvidia-key4 | 40 RPM | /Users/variya/.openclaw/agents/critic/.env |
| creator | nvidia-key5 | 40 RPM | /Users/variya/.openclaw/agents/creator/.env |

### 3. 清理废弃 Agent
✅ 删除配置：`/Users/variya/.openclaw/agents/curator/`
✅ 删除配置：`/Users/variya/.openclaw/agents/innovator/`
✅ 删除工作区：`workspace-curator`

### 4. 更新配置文档
✅ 更新：`IDENTITY.md` (任务分配路由、工作区路径)
✅ 更新：`MEMORY.md` (Agent团队、API密钥分配)
✅ 更新：`TOOLS.md` (API密钥分配表).
✅ 更新：`AGENTS.md` (工作区速查表、Subagent规则)

### 5. models.json 简化
**之前**: 包含所有5个nvidia provider + qclaw provider
**现在**: 仅包含 `nvidia` provider，apiKey 使用环境变量 `NVIDIA_API_KEY`

示例：
```json
{
  "providers": {
    "nvidia": {
      "baseUrl": "https://integrate.api.nvidia.com/v1",
      "api": "openai-completions",
      "models": [...],
      "apiKey": "NVIDIA_API_KEY"
    }
  }
}
```

---

## 验证清单

- [x] 5个活跃 Agent 配置完整（architect, architect2, researcher, critic, creator）
- [x] 每个 Agent 有独立的 `.env` 文件
- [x] 每个 Agent 的 `models.json` 使用环境变量
- [x] 废弃 Agent（curator, innovator）已删除
- [x] 配置文件已更新（IDENTITY, MEMORY, TOOLS, AGENTS）
- [x] 架构师1和2使用独立的 API key（不共用）

---

## 当前Agent团队

| Agent | 工作区 | API Key | 配额 |
|-------|--------|---------|------|
| 🏗️ 架构师1 | workspace-architect | nvidia-key2 | 40 RPM |
| 🏗️ 架构师2 | workspace-architect2 | nvidia-key3 | 40 RPM |
| 🕵️ 研究员 | workspace-researcher | nvidia-key1 | 40 RPM |
| 🔍 评审官 | workspace-critic | nvidia-key4 | 40 RPM |
| ✍️ DevOps | (主工作区) | nvidia-key5 | 40 RPM |

**总配额**: 200 RPM | **利用率目标**: ~95%
