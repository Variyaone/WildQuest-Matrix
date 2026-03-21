# HEARTBEAT.md - 心跳触发任务清单

**目标**: 通过心跳机制驱动各agent的常态化工作

**检查时机**: 每次收到心跳触发时执行

---

## 🔍 心跳触发条件

当消息匹配到心跳提示时：
- 检查当前时间
- 判断哪些agent有任务需要执行
- 触发对应agent的任务

---

## 📅 日常时间触发任务

### 每日9:00 - 研究员
- [ ] 数据质量检查
- [ ] 数据源更新验证

### 每日12:00 - 研究员 + 创作者
**研究员**:
- [ ] 深度研究速递
  - Web搜索最新研究
  - GitHub搜索相关项目
  - 输出研究简报

**创作者**:
- [ ] 每日文档同步
  - 更新变更日志
  - 同步知识库

### 每日18:00 - 评审官
- [ ] 代码审查
  - 审查今日代码变更
  - 记录质量问题

### 每5分钟 - 评审官
- [ ] 系统监控
  - Agent健康检查
  - 任务状态监控
  - 异常告警

---

## 📆 每周触发任务

**每周一 09:00 - 所有agent**:
- [ ] 🕵️ 研究员：策略评估 + 文献整理
- [ ] ✍️ 创作者：知识库维护
- [ ] 🔍 评审官：风险评估
- [ ] 🏗️ 架构师：性能优化周期开始
- [ ] 🚀 创新者：流程优化周期开始

**每周五 17:00 - 所有agent**:
- [ ] 周总结
- [ ] 下周计划

---

## 🔄 检查逻辑

### 1. 读取心跳状态

```python
# 读取最近检查时间
with open('.commander/heartbeat-state.json', 'r') as f:
    state = json.load(f)
```

### 2. 判断触发条件

```python
current_time = datetime.now()

# 每日9:00 - 研究员
if current_time.hour == 9:
    trigger_agent("researcher", "data_quality_check")

# 每日12:00 - 研究员 + 创作者
if current_time.hour == 12:
    trigger_agent("researcher", "daily_research_brief")
    trigger_agent("creator", "daily_doc_sync")

# 每日18:00 - 评审官
if current_time.hour == 18:
    trigger_agent("critic", "daily_code_review")

# 每周期（5分钟）- 评审官
if need_monitoring():
    trigger_agent("critic", "system_monitoring")

# 每周一 09:00
if current_time.weekday() == 0 and current_time.hour == 9:
    trigger_all_weekly_tasks()

# 每周五 17:00
if current_time.weekday() == 4 and current_time.hour == 17:
    trigger_all_weekly_summary()
```

### 3. 更新状态

```python
state['last_checks'] = {
    agent_id: current_time.isoformat()
}

with open('.commander/heartbeat-state.json', 'w') as f:
    json.dump(state, f, indent=2)
```

---

## 🎯 触发优先级

1. **紧急响应** > 日常监控 > 定期任务
2. 同一时间段的任务可批量触发
3. 避免重复触发（检查上次执行时间）

---

## 📊 状态追踪

使用 `.commander/heartbeat-state.json` 追踪:

```json
{
  "last_checks": {
    "researcher_daily": "2026-03-01T12:00:00",
    "creator_daily": "2026-03-01T12:00:00",
    "critic_daily": "2026-03-01T18:00:00",
    "critic_monitoring": "2026-03-01T03:15:00",
    "weekly_tasks": "2026-03-01T09:00:00"
  },
  "missed_tasks": [],
  "completed_today": []
}
```

---

## 🚀 异常处理

### 任务执行失败
- 记录错误信息
- 标记需要重试
- 通知指挥官

### Agent离线
- 等待下次心跳
- 累积任务
- 超时告警

---

**通过心跳驱动，让agent主动工作！**

---
*由创新者设计*
