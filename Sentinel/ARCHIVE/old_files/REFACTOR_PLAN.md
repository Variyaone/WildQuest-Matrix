# 哨兵引擎重构方案 v4.0

## 设计目标

### 核心改进
1. **会话职责分离**：心跳session vs 普通用户会话
2. **任务状态机制**：完整的任务生命周期
3. **自动推进机制**：心跳session自动推进可推进任务
4. **避免重复执行**：任务认领锁机制

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                      用户系统                            │
├─────────────────────────────────────────────────────────┤
│ 用户会话 (User Session)                                  │
│ ├─ 处理用户对话                                           │
│ ├─ 创建任务 (写TASK_POOL,状态=PENDING)                   │
│ ├─ 领取任务 (认领后状态=CLAIMED/IN_PROGRESS)             │
│ ├─ 执行任务                                               │
│ └─ 提交结果 (状态=AWAITING_REVIEW)                       │
└─────────────────────────────────────────────────────────┘
                         ↓ 写入
┌─────────────────────────────────────────────────────────┐
│                    任务系统 (TASK_POOL)                   │
├─────────────────────────────────────────────────────────┤
│ 任务状态机：                                             │
│ PENDING → CLAIMED → IN_PROGRESS → AWAITING_REVIEW       │
│     ↓              ↓               ↓                    │
│ ┌───┘              ↓               ↓                    │
│ ↓                 BLOCKED        FAILED                 │
│ COMPLETED                                      ↑        │
│   ↓                                            │        │
│ ARCHIVED                                      重试      │
│                                                        │
│ 数据结构：                                             │
│ - id: 任务唯一标识                                       │
│ - status: 当前状态                                     │
│ - claimed_by: 认领的session                              │
│ - claimed_at: 认领时间                                   │
│ - updated_at: 更新时间                                   │
│ - priority: 优先级 (T0/P1/P2)                           │
│ - assigned_to: 指定agent (可选)                          │
│ - deadline: 截止时间 (可选)                              │
│ - dependencies: 依赖任务ID数组 (可选)                    │
└─────────────────────────────────────────────────────────┘
                         ↑ 检查/推进
┌─────────────────────────────────────────────────────────┐
│                   哨兵系统 (Sentinel)                     │
├─────────────────────────────────────────────────────────┤
│ 哨兵心跳 Session (独立心跳系统)                           │
│ ├─ 触发：每10分钟定时                                   │
│ ├─ 职责：                                               │
│   1. 检查TASK_POOL中的任务状态                          │
│   2. 推进可自动推进的任务                                │
│   3. 检测异常情况                                         │
│   4. 更新心跳统计                                         │
│ ├─ 推进规则：                                           │
│   - PENDING任务 → 自动分配给合适的agent                  │
│   - BLOCKED任务 → 检查依赖是否满足                       │
│   - IN_PROGRESS > 2h → 标记为STALLED                    │
│   - STALLED → 重新分配或升级P1                           │
│ ├─ 警报条件：                                           │
│   - 有T0待认领任务                                       │
│   - 有STALLED任务 > 3个                                  │
│   - 有IN_PROGRESS > 4h的任务                            │
│   - 模式非normal                                         │
│ └─ 输出：                                               │
│   - 正常：HEARTBEAT_OK                                   │
│   - 异常：警报详情                                       │
└─────────────────────────────────────────────────────────┘
                         ↓ 审核
┌─────────────────────────────────────────────────────────┐
│                   审核系统 (Critic)                       │
├─────────────────────────────────────────────────────────┤
│ Critic Session                                           │
│ ├─ 接收AWAITING_REVIEW任务                               │
│ ├─ 测试验证                                               │
│ ├─ 状态流转：                                           │
│   - 通过 → COMPLETED → ARCHIVED                         │
│   - 不通过 → 重新IN_PROGRESS（附加问题说明）            │
│ └─ 更新ARCHIVE.md归档记录                               │
└─────────────────────────────────────────────────────────┘
```

## 文件结构

### HEARTBEAT.md (哨兵心跳配置)

```markdown
# HEARTBEAT.md - 哨兵心跳系统

## 触发条件
- **自动触发**: 每10分钟，由独立哨兵session执行
- **手动触发**: 用户发送心跳prompt时（仅限调试）

## 流程

### 1. 检查模式
```bash
读取 TASK_POOL.md 头部确认 mode
```
- mode != normal → 返回HEARTBEAT_OK

### 2. 检查任务状态
```bash
遍历 TASK_POOL.md 中的所有任务
```
按优先级排序: T0 > P1 > P2
按状态分组:
  - PENDING: 待认领
  - CLAIMED/IN_PROGRESS: 进行中
  - AWAITING_REVIEW: 等待审核
  - BLOCKED: 阻塞
  - STALLED: 停滞

### 3. 推进任务
#### 推进规则

| 当前状态 | 条件 | 推进 | 新状态 |
|---------|------|------|--------|
| PENDING | 优先级T0 | 立即报警 | - |
| PENDING | 优先级P1 | 检查依赖 | CLAIMED/IN_PROGRESS/BLOCKED |
| PENDING | 优先级P2 | 检查静默时段 | CLAIMED/IN_PROGRESS/BLOCKED |
| CLAIMED | 认领时间>30min | 超时重置 | PENDING |
| IN_PROGRESS | 持续时间>2h | 标记停滞 | STALLED |
| IN_PROGRESS | 持续时间>4h | 紧急报警 | - |
| BLOCKED | 依赖满足 | 重新推进 | PENDING |
| STALLED | 停滞<24h | 重新分配 | IN_PROGRESS |
| STALLED | 停滞>24h | 升级P1 | - |

#### 任务分配

| 任务类型 | 分配Agent | 说明 |
|---------|----------|------|
| 代码/算法 | architect/architect2 | 优先使用空闲的 |
| 研究/数据 | researcher | 数据挖掘、因子研究 |
| 测试/审查 | critic | 代码审查、系统测试 |
| 运维/推送 | creator | 部署、维护、推送 |
| 协调分配 | main | 复杂任务拆解 |

### 4. 检测异常
#### 警报条件 (任一满足即报警)
- [ ] 有T0任务状态=PENDING
- [ ] 有STALLED任务数 >= 3
- [ ] 有IN_PROGRESS任务持续时间 > 4h
- [ ] 有BLOCKED任务停滞 > 48h
- [ ] mode != normal

#### 静默时段
- 23:00-08:00 GMT+8: 只检查T0和IN_PROGRESS，不启动新P2任务

### 5. 更新统计
```markdown
> **Sentinel状态** `mode:normal` | `last:时间` | `beats:总数` | `done:完成数` | `t0:T0数` | `stalled:停滞数`
```

### 6. 输出
```markdown
HEARTBEAT_OK  # 无异常
或           # 有异常
⚠️ 哨兵警报（详述问题）
```

## 会话职责

| 会话类型 | 职责 | 读取 | 写入 | 输出 |
|---------|------|------|------|------|
| **哨兵心跳** | 自动推进、异常检测 | TASK_POOL | TASK_POOL | HEARTBEAT_OK/警报 |
| **普通会话** | 用户交互、任务执行 | TASK_POOL | TASK_POOL/ARCHIVE | 用户回复 |
| **Critic会话** | 审核归档 | TASK_POOL | ARCHIVE | 审核结果 |

## 配置

静默时段: 23:00-08:00 GMT+8
心跳间隔: 10分钟
停滞阈值: 2小时
紧急阈值: 4小时
```

### TASK_POOL.md (任务清单模板)

```markdown
> **Sentinel状态** `mode:normal` | `last:时间` | `beats:总数` | `done:完成数` | `t0:T0数` | `stalled:停滞数`

# 待办事项汇总 - YYYY-MM-DD

## 🔴 T0任务

### TASK-YYYYMMDD-001: [任务标题]
- **状态**: PENDING
- **描述**: [任务描述]
- **创建时间**: YYYY-MM-DD HH:MM
- **认领**: 无
- **依赖**: TASK-YYYYMMDD-002
- **截止**: YYYY-MM-DD

---

## 🔴 P1任务

### TASK-YYYYMMDD-002: [任务标题]
- **状态**: IN_PROGRESS
- **描述**: [任务描述]
- **创建时间**: YYYY-MM-DD HH:MM
- **认领**: researcher (session: xxx)
- **认领时间**: YYYY-MM-DD HH:MM
- **更新时间**: YYYY-MM-DD HH:MM
- **分配**: researcher
- **依赖**: [任务ID数组]

---

## 静默时段规则
- 23:00-08:00 GMT+8: 仅检查T0和IN_PROGRESS，不启动探索类任务

```

### ARCHIVE.md (归档记录)

```markdown
# 归档记录 - YYYY-MM

## YYYY-MM-DD

### TASK-YYYYMMDD-001: [任务标题]
- **状态**: COMPLETED → ARCHIVED
- **执行者**: architect (session: xxx)
- **完成时间**: YYYY-MM-DD HH:MM
- **审核者**: critic
- **耗时**: X小时Y分钟
- **成果**: [成果描述或文件]

---

**本月完成**: X个任务
**本月完成率**: XX%
```

## 任务数据结构 (JSON辅助文件)

```json
{
  "TASK-20260326-001": {
    "id": "TASK-20260326-001",
    "title": "配置Tavily搜索",
    "status": "IN_PROGRESS",
    "priority": "P1",
    "description": "安装并配置Tavily MCP插件",
    "created_at": "2026-03-26T02:30:00Z",
    "claimed_by": "architect",
    "claimed_session": "session-uuid",
    "claimed_at": "2026-03-26T02:35:00Z",
    "updated_at": "2026-03-26T03:00:00Z",
    "assigned_to": "architect",
    "deadline": "2026-03-27T00:00:00Z",
    "dependencies": [],
    "metrics": {
      "duration_minutes": 30,
      "attempts": 1
    },
    "result": null
  }
}
```

## 实施计划

### Phase 1: 文件重构 (1小时)
1. ✅ 设计方案 (本文件)
2. ⏳ 重写 HEARTBEAT.md
3. ⏳ 重写 TASK_POOL.md 模板
4. ⏳ 创建 TASK_POOL.json 辅助文件
5. ⏳ 更新 ARCHIVE.md 模板

### Phase 2: 代码逻辑实现 (2小时)
6. ⏳ 创建哨兵心跳session检查逻辑
7. ⏳ 创建任务状态管理逻辑
8. ⏳ 创建任务分配逻辑
9. ⏳ 创建异常检测逻辑

### Phase 3: 配置集成 (30分钟)
10. ⏳ 配置定时心跳触发
11. ⏳ 测试哨兵流程
12. ⏳ 迁移现有任务到新结构

### Phase 4: 验证与优化 (1小时)
13. ⏳ 测试任务分配与推进
14. ⏳ 测试异常报警
15. ⏳ 测试会话职责分离
16. ⏳ 文档与培训agent

### Phase 5: 上线 (30分钟)
17. ⏳ 切换到新哨兵引擎
18. ⏳ 监控24小时
19. ⏳ 收集反馈优化

## 关键改进点总结

| 改进项 | 问题 | 解决方案 |
|--------|------|---------|
| 会话混淆 | 普通会话也处理TASKPOOL | 职责分离：心跳会话专门处理 |
| 推进缺失 | 没有自动推进机制 | 心跳会话自动推进PENDING→IN_PROGRESS |
| 状态不足 | 只有待办/归档 | 完整状态机：6种状态 |
| 任务竞争 | 多session可能重复领取 | 认领锁：claimed_by标记 |
| 异常不可见 | 停滞任务不报警 | 心跳检测：STALLED报警 |
| 依赖丢失 | 任务依赖没管理 | dependencies字段自动检查 |
| 任务丢失 | 03-23→03-26任务堆积 | 定时心跳每10分钟检查推进 |

## 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 心跳session启动失败 | 中 | 高 | 添加降级机制：普通会话也执行心跳 |
| 任务认领死锁 | 低 | 中 | 30分钟超时自动释放 |
| 状态不一致 | 中 | 中 | 添加TASK_POOL.json作为数据源，TASK_POOL.md作为展示 |
| 性能问题 | 低 | 中 | 添加缓存，避免频繁读写 |

## 向后兼容

- 保留原有的TASK_POOL.md格式作为fallback
- 新任务使用新格式
- 旧任务在下次心跳时自动迁移到新格式

---
*设计日期: 2026-03-26*
*版本: v4.0*
*设计者: main agent*
