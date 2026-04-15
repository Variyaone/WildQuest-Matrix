# 心跳检查清单

## 快速检查（<10秒）

1. 检查模式
   ```bash
   head -n 10 /Users/variya/.openclaw/workspace/Sentinel/TASK_POOL.md
   ```
   - 如果不是`normal` → 返回`HEARTBEAT_OK`

2. 检查待认领任务
   ```bash
   grep "pending" /Users/variya/.openclaw/workspace/Sentinel/TASK_POOL.md
   ```
   - 如果有`pending`任务 → 分配给subagents

3. 检查活跃任务
   ```bash
   openclaw subagents list --recent-minutes 120
   ```
   - 如果有任务停滞>2h → 重新分配

4. 检查T0
   ```bash
   grep "当前T0任务" /Users/variya/.openclaw/workspace/Sentinel/T0.md
   ```
   - 如果有待处理T0 → 通知用户

## 异常处理

- 任务停滞>2h → 重新分配
- TASK_POOL.md为空 → 触发空窗期探索
- 模式非normal → 返回`HEARTBEAT_OK`

## 空窗期探索（TASK_POOL.md为空时）

- 上下文延续（50%）
- T0文档（30%）
- ARCHIVE记录（20%）

## 静默规则

- 静默时段: 23:00-08:00 GMT+8
- 静默时段: 仅检查T0，不启动探索类任务
