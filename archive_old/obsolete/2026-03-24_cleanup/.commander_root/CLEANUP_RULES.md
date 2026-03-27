# 🧹 文件清理规则

**维护者**: 创新者 (Innovator)
**版本**: 1.0
**创建时间**: 2026-02-27

---

## 📂 目录结构

```
~/.openclaw/workspace/.commander/
├── cleanup_garbage.py          # 清理脚本
├── cleanup_backups/            # 备份目录
├── archive/                    # 归档目录
│   ├── old_docs/              # 过时文档
│   │   └── 2026-02/           # 按月归档
│   └── old_tasks/             # 旧任务文件
└── CLEANUP_RULES.md           # 本文档

~/.openclaw/agents/*/sessions/
├── *.deleted.*                # 已删除会话（自动清理）
```

---

## 🔍 清理规则

### 1. Deleted Sessions（已删除会话）

**位置**: `~/.openclaw/agents/*/sessions/*.deleted.*`

**规则**:
- **条件**: 文件年龄 > 7天
- **动作**: 删除
- **备份**: 删除前备份到 `cleanup_backups/`

**说明**: OpenClaw自动归档删除的session，7天后可安全删除

---

### 2. Monitoring Logs（监控日志）

**位置**:
- `monitoring_cron.log` - 健康监控日志
- `timeout_cron.log` - 超时检测日志
- `AGENT_ALERTS.log` - 告警日志

**规则**:
- **条件**: 文件年龄 > 3天
- **动作**: 删除
- **备份**: 是

**说明**: 监控日志持续增长，3天后可清理

---

### 3. Old Config Backups（旧配置备份）

**位置**: `~/.openclaw/openclaw.json.bak`

**规则**:
- **条件**: 文件年龄 > 7天
- **动作**: 删除
- **备份**: 否（本身是备份）

**说明**: 权限管理脚本自动备份，7天后可安全删除

---

### 4. Outdated Documents（过时文档）

**位置**: `~/.openclaw/workspace/.commander/*.md`

**规则**:
- **条件**: 文件在过时列表中 && 文件年龄 > 0天
- **动作**: 归档到 `archive/old_docs/YYYY-MM/`
- **保留时间**: 永久归档（可手动删除）

**过时文档列表**:
```python
OUTDATED_DOCS = [
    "COMPLETE_STRATEGY_RESEARCH_PLAN.md",      # 策略研究计划（已执行）
    "OKX_API_RESEARCH.md",                    # OKX API研究（已完成）
    "OKX_API_USAGE_GUIDE.md",                 # OKX使用指南（已完成）
    "OKX_DEMO_API_SOLUTION.md",               # OKX解决方案（已部署）
    "OKX_ISSUE_DIAGNOSIS.md",                 # OKX问题诊断（已解决）
    "OKX_TRADING_MANUAL_STUDY.md",            # OKX手动研究（已完成）
    "COMMANDER_DASHBOARD.md",                 # 指挥仪表板（已被KANBAN替代）
    "COMMANDER_WORKBOARD.md",                 # 指挥看板（已被KANBAN替代）
    "READY_TO_DEPLOY.md",                     # 部署就绪（已部署）
    "SIMULATION_STATUS_REPORT.md",            # 模拟状态报告（已完成）
    "TRADING_FREQUENCY_EXPLANATION.md",        # 交易频率说明（过时）
    "API_KEYS.md",                            # API密钥（已移到TOOLS.md）
    "DECISION_CHECKLIST.md",                  # 决策清单（已过时）
    "EVOMAP_IDEA.md",                         # EVOMAP想法（未实施）
]
```

---

### 5. Old Tasks（旧任务文件）

**位置**: `~/.openclaw/workspace/.commander/team_tasks/`

**规则**:
- **条件**: 任务已完成（根据文件名或TASK_STATE.json）
- **动作**: 归档到 `archive/old_tasks/`
- **保留时间**: 30天

**说明**: 已完成的agent任务归档，便于历史追溯

---

### 6. Temporary Scripts（临时脚本）

**位置**: `~/.openclaw/workspace/.commander/*.py`

**规则**:
- **条件**: 脚本未被使用（可手动判断）
- **动作**: 归档到 `archive/old_scripts/`
- **保留时间**: 30天

**说明**: 临时测试脚本归档，定期清理

---

## 🚀 快速使用

### 预览模式
```bash
python3 cleanup_garbage.py
```

### 执行清理
```bash
python3 cleanup_garbage.py --apply
```

### Cron定期清理
```bash
# 每周日早上5点自动清理
0 5 * * 0 cd /Users/variya/.openclaw/workspace/.commander && python3 cleanup_garbage.py --apply >> cleanup_weekly.log 2>&1
```

---

## 📊 清理效果

**最近清理** (2026-02-27):
- ✅ 归档: 14个过时文档 (59.7 KB)
- ✅ 归档: 4个旧任务文件
- 🔍 保留: 35个deleted会话（<7天）

**预期效果** (每周清理):
- 删除 10-20 个deleted会话
- 归档 5-10 个过时文档
- 清理 3-6 个monitoring日志
- **空间释放**: 约100-200 KB/周

---

## ⚠️ 安全规则

1. **备份优先**: 所有删除操作前必须备份
2. **Dry-run验证**: 执行前用预览模式确认
3. **年龄阈值**: 不删除<7天的文件（除非确认安全）
4. **关键保护**: TASK_STATE.json/KANBAN.md等关键文件不处理
5. **可回滚**: 备份文件支持30天内回滚

---

## 📝 归档索引

### old_docs/2026-02/
- `COMPLETE_STRATEGY_RESEARCH_PLAN.md` (8.4 KB)
- `OKX_API_RESEARCH.md` (5.4 KB)
- `OKX_API_USAGE_GUIDE.md` (6.9 KB)
- `OKX_DEMO_API_SOLUTION.md` (4.1 KB)
- `OKX_ISSUE_DIAGNOSIS.md` (3.5 KB)
- `OKX_TRADING_MANUAL_STUDY.md` (0.9 KB)
- `COMMANDER_DASHBOARD.md` (5.5 KB)
- `COMMANDER_WORKBOARD.md` (8.4 KB)
- `READY_TO_DEPLOY.md` (5.1 KB)
- `SIMULATION_STATUS_REPORT.md` (3.2 KB)
- `TRADING_FREQUENCY_EXPLANATION.md` (3.2 KB)
- `API_KEYS.md` (1.1 KB)
- `DECISION_CHECKLIST.md` (2.6 KB)
- `EVOMAP_IDEA.md` (1.3 KB)

### old_tasks/
- `20260227_005534_architect_tasks.md`
- `20260227_005534_creator_tasks.md`
- `20260227_005534_critic_tasks.md`
- `20260227_005534_researcher_tasks.md`

---

## 🔄 更新日志

### 2026-02-27
- ✅ 创建清理脚本
- ✅ 定义清理规则
- ✅ 首次执行清理（归档14个文档+4个任务）
- ✅ 设置归档结构

---

**维护频率**: 每周自动执行 + 手动清理需求触发
**责任方**: 创新者 (Innovator)
