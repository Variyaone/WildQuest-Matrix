# HEARTBEAT.md - 心跳流程

## 核心清单
1. 目标解析→任务拆解→资源调度→进度监控→交付验证
2. 读TASK_POOL.md头部确认模式，非normal模式返回HEARTBEAT_OK
3. **TASK_POOL.md - 检查任务状态（必须执行）**
   - 检查是否有completed待审核任务 → 启动critic审核
   - 检查是否有stalled任务（>2h无更新） → 重新分配
   - 检查是否有pending任务（>10min未分配） → 分配给合适agent
4. T0.md - 检查待决T0事项
5. ARCHIVE.md - 检查完成记录

## 核心流程
| 步骤 | 动作 |
|---|---|
| 输入 | 分析消息，生成任务写TASK_POOL.md（检查T0.md） |
| 分配 | 按优先级分配TASK_POOL.md中的任务（标记assigned:agent_id） |
| 执行 | 大任务原地分解（<5分钟，<200行），完成后标记completed |
| **审核** | **critic自动审核completed任务（心跳触发）** |
| 归档 | 审核通过后，从TASK_POOL.md删除，追加到ARCHIVE.md |
| 发散探索 | 深入想法、改进点、T0替代方案写入TASK_POOL.md |
| 上下文管理 | 对话>50轮或>10K token时，压缩已完成摘要到ARCHIVE.md，未完成任务返回TASK_POOL.md |
| 空窗期探索 | TASK_POOL.md为空时探索：上下文(50%) > T0文档(30%) > ARCHIVE记录(20%) |

## 任务状态机
```
pending → assigned → in_progress → completed → [critic审核] → archived
         ↓
      stalled (>2h无更新，重新分配)
```

## 心跳检查清单（必须执行）
1. **检查completed任务** → 启动critic审核
2. **检查stalled任务** → 重新分配
3. **检查pending任务** → 分配给合适agent
4. **检查T0任务** → 优先处理 |

## T0定义
1. 会导致经济损失
2. 会导致设备或系统损坏
3. 会产生其他严重后果

**其他任务自主决策，禁止询问"是否启动"。**

## Agent分工
- main: 协调分配（简单任务直接执行）
- architect/architect2: 代码/算法
- researcher: 研究/数据
- critic: 测试/审查（默认怀疑，必须实测）
- creator: 运维/推送/维护

## 执行规则
- 任务<5分钟，<200行
- 失败：重试→换方案→3次失败升级T0
- 完成：标记completed → critic审核 → 归档
- **状态标记**：不使用"认领锁"，直接标记assigned:agent_id

## Agent职责
- **main**: 协调分配（简单任务直接执行）
- **architect/architect2**: 代码/算法（先调试15分钟再上报）
- **researcher**: 研究/数据
- **critic**: 测试/审查（默认怀疑，必须实测，心跳自动触发审核）
- **creator**: 运维/推送/维护

## 异常处理
- 任务停滞>2h → 标记stalled → 重新分配
- TASK_POOL为空 → 空窗期探索
- 模式非normal → 返回HEARTBEAT_OK
- critic审核失败 → 标记为需要重做 → 重新分配

## 关键功能保留
✅ T0优先级机制
✅ 任务状态追踪
✅ 归档记录
✅ 心跳检查（30分钟）
✅ 异常处理
✅ 空窗期探索
✅ 上下文管理

---
*2026-03-25*
