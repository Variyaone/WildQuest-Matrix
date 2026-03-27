# Sentinel 状态机规范 v4.0

> **设计原则**: 去掉"认领锁"，改用"状态标记"
> **目标**: 减少Token消耗，简化协调流程

## 任务状态流转

```
pending → assigned → in_progress → completed → archived
   ↓         ↓          ↓            ↓
stalled   stalled    stalled      failed
```

## 状态定义

| 状态 | 含义 | 谁可以修改 |
|------|------|-----------|
| `pending` | 待分配 | main |
| `assigned:agent_id` | 已分配给agent | main |
| `in_progress` | 执行中 | 被分配的agent |
| `completed` | 完成待归档 | 被分配的agent |
| `archived` | 已归档 | critic（审核通过后） |
| `stalled` | 卡住（>2h无更新） | main（心跳检测） |
| `failed` | 失败（3次重试后） | 被分配的agent |

## Agent行为规范

### main（指挥官）
```
1. 用户消息 → 解析 → 写入TASK_POOL.md（状态: pending）
2. 立即分配 → 标记 assigned:agent_id
3. 心跳检查（30分钟）:
   - 检查 assigned/in_progress 任务
   - >2h无更新 → 标记 stalled → 重新分配
4. 收到critic审核通过 → 从TASK_POOL删除 → 追加到ARCHIVE
```

### 其他agent（执行者）
```
1. 启动时: 读TASK_POOL.md一次
2. 找到 assigned:self 的任务
3. 开始执行 → 更新状态为 in_progress
4. 完成后:
   - 更新状态为 completed
   - 直接回复用户（不经过main）
   - 等待critic审核
```

### critic（评审官）
```
1. 检查 completed 状态的任务
2. 执行审核 → 通过则标记 archived
3. 只有critic可以宣布任务完成并归档
```

## TOKEN消耗优化

### 旧方案（轮询）
```
每个agent每N分钟轮询TASK_POOL
消耗: agent数量 × 轮询频率 × 文件大小
```

### 新方案（状态标记）
```
- main: 用户消息触发分配（无轮询）
- agent: 启动时读1次（无轮询）
- 心跳: 30分钟检查1次（只检查异常）
节省: 50-70% token
```

## 文件格式示例

### TASK_POOL.md
```markdown
## 🔴 P1任务
- [ ] TASK-001: 修复数据源连接
  - 状态: assigned:architect
  - 截止: 2026-03-27
  - 最后更新: 2026-03-26T04:15:00

## 🟡 P2任务  
- [ ] TASK-002: 更新文档
  - 状态: pending
  - 负责人: 待分配
```

## 异常处理

### 任务卡住（>2h）
```
main心跳检测到 → 标记stalled → 重新分配给其他agent
```

### Agent崩溃
```
main心跳检测到 → 任务状态无更新 → 标记stalled → 重新分配
```

### 并发冲突
```
文件锁（简单实用，开销低）
读取时加锁 → 写入时释放
```

## 心跳静默规则

- **时段**: 23:00-08:00 GMT+8
- **行为**: 仅检查T0，不启动探索类任务
- **频率**: 30分钟（OpenClaw默认）

## 消息路由

### 单Channel场景（当前飞书配置）
```
agent完成 → 直接回复用户 → 用户看到agent identity
示例: [🏗️架构师] 完成了xxx
```

### OpenClaw保证
- 消息按顺序发送（queue.mode: collect）
- agent回复带identity.name标识
- 不会混乱

---
*2026-03-26 Sentinel 4.0*
