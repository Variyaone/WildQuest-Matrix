# A股定时任务总览 - 2026-03-24

## 接管时间
2026-03-24 19:06 GMT+8

---

## 📅 定时任务完整清单

| 任务ID | 名称 | 执行时间 | 时区 | 状态 | 备注 |
|--------|------|----------|------|------|------|
| **我创建** |
| 9687dbf9... | A股盘前推送 | 08:45 1-5 | Shanghai | ✅ | 新增，每个交易日盘前 |
| eace211b... | A股盘中监控 | 30 10,12,14 1-5 | Shanghai | ✅ | 新增，盘中3个时段 |
| aa5e50ab... | A股盘后复盘 | 30 15 1-5 | Shanghai | ✅ | 新增，收盘后复盘 |
| **已有任务** |
| task-data-morning-update | 早盘数据更新 | 06:30 1-5 | Shanghai | ✅ | 开盘前数据准备 |
| task-market-open-monitor | 开盘风控监控 | 09:30 1-5 | Shanghai | ✅ | 开盘风险检查 |
| task-monitor-collector | 监控数据收集 | 整点 24h | Shanghai | ⚠️ | 连续4次错误 |
| task-closing-data-update | 收盘数据更新 | 15:10 1-5 | Shanghai | ⚠️ | 昨日失败 |
| task-evening-full-analysis | 盘后完整分析 | 16:00 1-5 | Shanghai | ⚠️ | 昨日超时 |
| task-afternoon-report-push | 盘后报告推送 | 17:00 1-5 | Shanghai | ⚠️ | 昨日失败 |
| task-health-check | 系统健康检查 | 03:00 Daily | Shanghai | ✅ | 每日凌晨3点 |
| task-weekly-innovation-lab | 周度创新实验室 | 02:00 Sat | Shanghai | ✅ | 每周六 |
| task-weekly-backtest | 周度回测 | 02:00 Sun | Shanghai | ✅ | 每周日 |
| task-weekly-factor-review | 周度因子评估 | 03:00 Sun | Shanghai | ✅ | 每周日 |

---

## 🔄 我新增的推送任务

### 1. A股盘前推送 (08:45)
**任务ID**: `9687dbf9-d6fa-4572-9d1e-5f9b7b4e2739`
**执行时间**: 周一至周五 08:45
**内容**:
- 更新市场数据
- 运行策略分析
- 生成今日信号
- 推送到飞书

### 2. A股盘中监控 (10:30, 12:30, 14:30)
**任务ID**: `eace211b-799d-4960-bebd-7c44750f12eb`
**执行时间**: 周一至周五 10:30, 12:30, 14:30
**内容**:
- 检查市场实时数据
- 监控持仓风险
- 追踪重要信号
- 风险预警推送

### 3. A股盘后复盘 (15:30)
**任务ID**: `aa5e50ab-be76-400b-92a2-f70ab352dd`
**执行时间**: 周一至周五 15:30
**内容**:
- 采集当日收盘数据
- 运行回测分析
- 生成盘后报告
- 明日策略规划
- 推送复盘报告

---

## ⚠️ 需要关注的问题

### 执行失败的任务
| 任务 | 错误 | 连续次数 |
|------|------|----------|
| task-monitor-collector | AxiosError 400 | 4次 😨 |
| task-closing-data-update | AxiosError 400 | 1次 |
| task-evening-full-analysis | timeout超时 | 1次 |
| task-afternoon-report-push | AxiosError 400 | 1次 |

**可能原因**：
- API请求参数错误
- 网络问题
- 认证token过期
- 任务执行时间过长

**建议**：
- 检查数据源API配置
- 增加超时时间配置
- 添加错误重试机制

---

## 📊 每日推送时间线

```
06:30 早盘数据更新
  ↓
08:45 🆕 盘前推送 ← 重点
  ↓
09:30 开盘风控监控
  ↓
10:30 🆕 盘中监控（上午）
  ↓
12:30 🆕 盘中监控（午间）
  ↓
14:30 🆕 盘中监控（下午）
  ↓
15:10 收盘数据更新
  ↓
15:30 🆕 盘后复盘 ← 重点
  ↓
16:00 盘后完整分析
  ↓
17:00 盘后报告推送
```

---

## 🎯 推送内容规划

### 盘前推送 (08:45)
- 市场环境分析
- 今日策略信号（5-10只）
- 风险提示
- 操作建议

### 盘中监控 (10:30/12:30/14:30)
- 实时市场数据
- 持仓风险监控
- 重要信号追踪
- 风险预警

### 盘后复盘 (15:30)
- 当日收盘数据
- 回测分析结果
- 明日策略规划
- 操作建议

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `/workspace/scripts/a_stock_pre_market_push_v2.py` | 盘前推送脚本v2（已修复CLI） |
| `/workspace/a-stock-takeover.md` | 接管决策记录 |
| `/workspace/a-stock-checklist.md` | 完成清单 |
| `/workspace/projects/a-stock-advisor 6/` | A股项目目录 |

---

*更新时间：2026-03-24 19:10*
