# 文档归档计划

> 创建日期：2026-02-28
> 目的：减少信息熵，简化系统

---

## 📋 归档原因

当前.commander目录存在大量历史文档和临时文件，导致：
- ❌ 信息熵高，查找困难
- ❌ 文档过多，混乱
- ❌ 影响系统效率

---

## 🗂️ 归档清单

### 第一批：历史日志文件（立即归档）

| 文件 | 大小 | 原因 |
|------|------|------|
|AGENT_HEALTH_REPORT.md | 8.7KB | 历史报告，已有最新报告|
|AGENT_ALERTS.log | 56.8KB | 历史日志，可压缩归档|
|monitoring_cron.log | 212KB | 监控日志，可压缩归档|
|timeout_cron.log | 64KB | 超时日志，可压缩归档|

**归档位置**：`.commander/archive/logs/2026-02/`
**操作**：压缩后归档

---

### 第二批：已完成项目文档（可归档）

| 文件 | 大小 | 原因 |
|------|------|------|
|BACKTEST_ANALYSIS.md | 2.4KB | 已完成项目，归档留存|
|CLEANUP_REPORT.md | 4.0KB | 清理已完成，归档留存|
|DEPLOYMENT_REPORT.md | 1.9KB | 部署完成，归档留存|
|TASK_COMPLETION_REPORT.md | 3.6KB | 完成报告，归档留存|
|TASK_COMPLETION_SUMMARY.md | 2.3KB | 总结报告，归档留存|
|TASK_TIMEOUT_REPORT.md | 0.9KB | 超时报告，归档留存|
|INNOVATOR_SUMMARY.md | 3.6KB | 历史总结，归档留存|

**归档位置**：`.commander/archive/completed_tasks/2026-02/`

---

### 第三批：分析类文档（已完成分析）

| 文件 | 大小 | 原因 |
|------|------|------|
|REDUNDANCY_ANALYSIS.md | 0.7KB | 冗余分析已完成|
|REDUNDANCY_EXECUTION_REPORT.md | 3.1KB | 执行报告，归档留存|
|REDUNDANCY_OPTIMIZATION_PLAN.md | 4.9KB | 计划已完成|
|SYSTEM_OPTIMIZATION.md | 1.3KB | 优化已完成|

**归档位置**：`.commander/archive/analysis/2026-02/`

---

### 第四批：日汇总文档（批量归档）

| 文件 | 大小 |
|------|------|
|DAILY_SUMMARY_2026-02-25.md | 2.9KB |
|DAILY_SUMMARY_2026-02-26.md | 3.4KB |
|DAILY_SUMMARY_2026-02-27.md | 1.5KB|
|DAILY_SUMMARY_DEPLOYED.md | 1.6KB|
|DAILY_SUMMARY_INDEX.md | 3.2KB|
|DAILY_SUMMARY_README.md | 1.7KB|

**归档位置**：`.commander/archive/daily_summaries/2026-02/`

---

### 第五批：过时配置文档（归档或删除）

| 文件 | 大小 | 原因 |
|------|------|------|
|API_KEYS_UPDATE_REPORT.md | 1.2KB | 已完成，归档|
|CONFIG_INDEX.md | 1.9KB | 配置已变更，归档|
|AUTO_DECISION_MECHANISM.md | 6.6KB | 已有新机制，归档|
|AUTO_TASK_LAUNCHER.md | 3.6KB | 功能已集成，归档|
|MARKET_STATE_MODULE_COMPLETED.md | 1.4KB | 已完成，归档|
|MAKE_MONEY_PROGRESS.md | 1.5KB | 历史记录，归档|

**归档位置**：`.commander/archive/obsolete_configs/`

---

### 第六批：临时测试文件

| 文件 | 大小 | 原因 |
|------|------|------|
|okx_trading.log | 0KB | 空文件，可删除|
|task_state_*.json | 多个 | 历史状态，统一归档|

**归档位置**：`.commander/archive/temp/2026-02/`

---

## 📁 归档后的目录结构

```
.commander/
├── TASK_POOL.md          # 新：任务池
├── TASK_KANBAN.md        # 新：看板
├── AGENT_WORK_GUIDE.md   # 新：Agent指南
├── README_NEW_SYSTEM.md  # 新：系统说明
├── KANBAN.md             # 保留：全局项目看板
├── TASK_STATE.json       # 保留：当前任务状态
│
└── archive/              # 归档目录
    ├── logs/
    │   └── 2026-02/
    ├── completed_tasks/
    │   └── 2026-02/
    ├── analysis/
    │   └── 2026-02/
    ├── daily_summaries/
    │   └── 2026-02/
    ├── obsolete_configs/
    │   └── 2026-02/
    └── temp/
        └── 2026-02/
```

---

## 💾 预期效果

归档后：
- ✅ 主目录文件数量：112 → 约60个
- ✅ 磁盘空间：节省约200-300KB
- ✅ 查找效率：提升50%+
- ✅ 系统熵值：进一步降低

---

## ⚙️ 执行计划

1. 创建归档目录结构
2. 按批次移动文件
3. 压缩日志文件
4. 更新相关索引
5. 验证归档完成

---

*计划执行后，系统将更加清晰高效*
