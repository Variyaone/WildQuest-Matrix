# Web Search 配置状态报告

## ✅ 已配置内容

### 1. 环境变量
```bash
~/.zshrc:
export BRAVE_SEARCH_API_KEY=BSAinVhD0j_u0q-JBa1LKq1VQ6QqpHy
```

### 2. OpenClaw 配置
```json
~/.openclaw/openclaw.json:
{
  "plugins": {
    "brave": {
      "enabled": true,
      "config": {
        "webSearch": {
          "apiKey": "BSAinVhD0j_u0q-JBa1LKq1VQ6QqpHy"
        }
      }
    }
  }
}
```

## ⚠️ 当前状态

| 工具 | 配置 | 验证状态 |
|------|------|----------|
| **web_search** | ✅ 已配置 | ❌ 调用失败: fetch failed |
| **web_fetch** | ✅ 默认可用 | ✅ 工作正常 |

## 问题诊断

web_search 工具返回 `fetch failed` 错误，可能原因：
1. Brave API Key 无效或已过期
2. Brave API 服务暂时不可用
3. API 调用频率限制超出

## 推荐解决方案

### 方案1: 使用 web_fetch（推荐 - 立即可用）
web_fetch 工具完全可用，研究员 agent 已使用此工具进行技术研究。

### 方案2: 验证 Brave API Key
```bash
# 手动测试 API key
curl -X POST "https://api.search.brave.com/res/v1/web/search" \
  -H "X-Subscription-Token: BSAinVhD0j_u0q-JBa1LKq1VQ6QqpHy" \
  -H "Content-Type: application/json" \
  -d '{"q": "test"}'
```

### 方案3: 更新 API Key
如果验证失败，需要：
1. 获取新的 Brave Search API Key
2. 更新 ~/.zshrc 和 ~/.openclaw/openclaw.json 中的配置

## 当前工作流程

研究员 agent 使用 web_fetch 工具进行技术研究，流程正常。

---

*最后更新: 2026-03-24*
