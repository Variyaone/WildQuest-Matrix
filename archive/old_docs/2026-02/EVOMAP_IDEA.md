# 🦞 任务管理器

简易任务管理工具，供指挥官和agent团队使用。

## 任务状态

| 状态 | 含义 |
|------|------|
| `pending` | 等待分配 |
| `assigned` | 已分配agent |
| `running` | 执行中 |
| `blocked` | 阻塞中 |
| `review` | 待评审 |
| `completed` | 已完成 |
| `failed` | 失败 |

## 任务优先级

| 优先级 | 含义 |
|--------|------|
| `critical` | 紧急，立即处理 |
| `high` | 高优先级 |
| `medium` | 中等优先级 |
| `low` | 低优先级 |

## 任务结构

```json
{
  "id": "TASK-001",
  "title": "任务标题",
  "description": "任务描述",
  "priority": "high",
  "status": "pending",
  "assignedTo": ["researcher", "architect"],
  "createdBy": "main",
  "createdAt": "2026-02-25T05:00:00+08:00",
  "updatedAt": "2026-02-25T05:00:00+08:00",
  "dueDate": "2026-02-25T10:00:00+08:00",
  "dependencies": [],
  "deliverables": [],
  "notes": []
}
```

## 工作流程

```
[pending] → [assigned] → [running] → [review] → [completed]
                ↓            ↓          ↓
            [blocked]    [failed]   [revision]
```

## 指挥官职责

1. 创建任务并分配优先级
2. 指派合适的agent组合
3. 监控执行进度
4. 处理阻塞和异常
5. 验收最终交付

---

*小龙虾🦞 指挥官*
