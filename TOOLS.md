# TOOLS.md - 工具配置记录

## API密钥

### NVIDIA API (6个密钥， total 240 RPM)
- 🦞 小龙虾: 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 (40 RPM)
- 🕵️ 研究员: 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 (40 RPM)
- 🏗️ 架构师: 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 (40 RPM)
- ✍️ 创作者: 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 (40 RPM) → **独立密钥**
- 🔍 评审官: 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 (40 RPM)
- 🚀 创新者: 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 (40 RPM) → **独立密钥**
- **总容量**: 240 RPM

### Brave Search
- API Key: BSAinVhD0j_u0q-JBa1LKq1VQ6QqpHy
- 限制: 10结果/次

### 飞书 (Feishu/Lark)
- App ID: cli_a90e4d460be1dbd3
- App Secret: R9QeZDhEDRhJLF4XwkzpRhFHd06EMUjT

### Gitee
- 用户名: variyaone
- Token: 47deef8061cc35a362e63f0ace24b8e9
- 认证方式: HTTPS (GIT_ASKPASS)
- 配置位置: ~/.git-credentials

### Tushare (新添加)
- Token: 14423f1b4d5af6dc47dd1dc8d9d5994dc05d10dbb86cc2d0da753d25
- 限制: 免费版每日200次调用
- 用途: A股真实数据获取
- 添加时间: 2026-03-02 01:17

### AKShare (新添加)
- GitHub: https://github.com/akfamily/akshare/
- 特点: 完全免费，开源，覆盖面广
- 用途: A股真实数据获取（辅助数据源）
- 添加时间: 2026-03-02 01:24

### 智投API (新添加)
- API文档: https://www.zhituapi.com/hsstockapi.html
- Token: 37171346-847B-47D5-91F8-BCABDDF3C845
- 用途: A股真实数据获取（补充数据源）
- 添加时间: 2026-03-02 01:45

### Baostock (新添加)
- 官网: http://www.baostock.com
- 特点: 免费、开源、无需注册
- 优势: 数据质量高、无调用限制、支持本地存储
- 劣势: 数据不全、只支持Python 3.5+
- 用途: A股真实数据获取（主力数据源）
- 添加时间: 2026-03-02 01:53

### Ashare (新添加)
- 特点: 极简、高效、开源
- 用途: A股实时行情数据（补充数据源）
- 添加时间: 2026-03-02 01:53

## 数据源优先级策略
1. **主力**：AKShare + Baostock（无限制）
2. **备用**：Tushare Pro（积分制）+ 智投API（Token）
3. **补充**：Ashare + 东方财富
4. **策略**：多数据源交叉验证，确保数据质量

---

## 环境配置

### Git
- Credential helper: store
- Gitee服务: https://gitee.com

### OpenClaw配置
- Gateway端口: 18789
- 绑定: loopback (127.0.0.1)
- Auth token: 41fe6c903830374b98014a959074b1cc494f2112157fe78e

---

## Agent团队分配

| Agent | API | 工具权限 |
|-------|-----|----------|
| 🦞 小龙虾 | nvidia (独占) | full |
| 🕵️ 研究员 | nvidia-key1 | full (web tools) |
| 🏗️ 架构师 | nvidia-key2 | coding |
| ✍️ 创作者 | nvidia-key5 (独立) | coding |
| 🔍 评审官 | nvidia-key3 | coding |
| 🧩 整理者 | nvidia-key4 (独立) | full |

**更新时间**: 2026-02-27 ✅ 每个Agent独立密钥

---



---
*由小龙虾🦞维护*
