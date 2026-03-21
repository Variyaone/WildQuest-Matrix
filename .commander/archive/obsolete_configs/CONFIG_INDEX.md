# 👁️ 配置目录 - 快速查找

**目的**: 所有重要配置的索引，避免混乱遗忘

---

## 🔑 API密钥索引

### OKX模拟盘密钥 ✅
**位置**: `okx-temp/okx_config.json`
**用途**: 资金费套利模拟盘测试
**备注**: 这是模拟盘密钥，直接用API调用

```json
{
  "api_key": "d97acda8-2983-4295-95a4-09424b0f780b",
  "secret": "116FC7791BEEF0DD0229CCB995752D8F",
  "passphrase": "S2yCfpg!NjyLwHs",
  "simulated": true,
  "sandbox": true
}
```

### NVIDIA API密钥
**位置**: `TOOLS.md`
**用途**: 模型调用
**数量**: 6个密钥，240 RPM

### Brave Search
**位置**: `TOOLS.md`
**API Key**: BSAinVhD0j_u0q-JBa1LKq1VQ6QqpHy

---

## 📋 项目状态索引

### A股量化项目
**最终报告**: `projects/a-stock-advisor/.commander/a_stock_final_factors_report.md`
**当前状态**: 重新设计中（过拟合问题）
**数据源**: AkShare（真实A股数据）

### 资金费套利项目
**策略代码**: `backtest/funding_rate_arbitrage.py`
**优化报告**: `backtest/results/funding_optimization_simple_report.md`
**最优参数**: 开仓0.01%，平仓50%，仓位25%，杠杆3x
**年化**: 22%

---

## 📁 重要文件索引

### 心跳与任务管理
- `HEARTBEAT.md` - 心跳检查规则
- `TASK_STATE.json` - 任务状态
- `AUTO_TASK_LAUNCHER.md` - 自主任务启动规则

### 规则与指南
- `OKX_SIMULATION_GUIDE.md` - OKX使用规则（回测可本地，模拟盘必须用API）

### 内存与记忆
- `MEMORY.md` - 长期记忆
- `memory/YYYY-MM-DD.md` - 每日笔记

---

## 🔍 快速查找命令

```bash
# 查找OKX密钥
cat(okx-temp/okx_config.json)

# 查找NVIDIA密钥
grep "nvapi-" TOOLS.md

# 查找项目状态
cat TASK_STATE.json

# 查找今日工作日志
cat(memory/$(date +%Y-%m-%d).md)
```

---

**使用原则**:
1. 需要密钥 → 先查这个目录
2. 需要项目状态 → 查相关报告链接
3. 需要规则 → 查规则指南

---
*由小龙虾建立，解决混乱问题*
