# MCP服务器安装研究

## 目标
安装以下MCP服务器：
1. Tavily搜索（API: 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）
2. Google Gemini搜索（API: AIzaSyBH2ODy9TQ2y2RRQ8kqh7z5o3wfh109sNk）

## 当前搜索能力
- ✅ Brave搜索（web_search内置工具） - 已测试工作正常
- ✅ DuckDuckGo（multi-search-engine skill）
- ✅ 其他16个搜索引擎（multi-search-engine已安装）

## 待配置
- ⏳ Tavily MCP服务器
- ⏳ Google Gemini搜索API

## API密钥（环境变量）
```
TAVILY_API_KEY=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
GOOGLE_GEMINI_API_KEY=AIzaSyBH2ODy9TQ2y2RRQ8kqh7z5o3wfh109sNk
```

## 下一步
1. 研究OpenClaw的MCP服务器配置机制
2. 安装并配置Tavily和Gemini
3. 更新MEMORY.md记录配置
