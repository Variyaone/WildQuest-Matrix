# 组织自主机制设计文档

**版本**: 1.0
**创建时间**: 2026-03-01
**负责人**: 创新者 (Innovator)

---

## 📋 目录

1. [核心目标](#核心目标)
2. [问题分析](#问题分析)
3. [架构设计](#架构设计)
4. [任务池机制](#任务池机制)
5. [看板机制](#看板机制)
6. [自主工作触发器](#自主工作触发器)
7. [失败重试机制](#失败重试机制)
8. [Agent角色与职责](#agent角色与职责)
9. [工作流程](#工作流程)
10. [使用指南](#使用指南)
11. [最佳实践](#最佳实践)
12. [未来扩展](#未来扩展)

---

## 核心目标

建立任务池和agent自主工作机制，让组织能够**自主、自动、自发**地行动和改进。

### 关键特性

- ✅ **任务池化**: 所有任务统一管理，全局可见
- ✅ **自主领取**: Agent主动扫描并领取适合自己的任务
- ✅ **自动分配**: 基于能力和优先级智能分配
- ✅ **实时监控**: 看板可视化任务进度
- ✅ **失败重试**: 自动分析并重试失败任务
- ✅ **状态同步**: Agent状态实时同步系统

---

## 问题分析

### 当前痛点

1. **指挥官过载**
   - 做了太多执行工作
   - 瓶颈效应明显
   - 决策处理不及时

2. **Agent闲置**
   - 其他agent利用率低
   - API调用浪费
   - 能力未充分发挥

3. **缺少任务池**
   - 任务分散，无统一管理
   - Agent无法自主领取任务
   - 任务可见性差

4. **缺少触发机制**
   - 所有任务需要人工分配
   - 缺少主动工作机制
   - 响应速度慢

### 解决方案

```
传统模式:
指挥官 → 手动分配 → Agent执行
(单点瓶颈，依赖人工)

自主模式:
任务池 → 自动扫描 → Agent自主领取 → 执行 → 更新状态
(去中心化，自动运转)
```

---

## 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────┐
│                  自主工作系统                         │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────────┐      ┌──────────────────────┐     │
│  │   任务创建    │ ───▶ │    task_pool.json    │     │
│  │  (任何人)    │      │    任务池 (持久化)    │     │
│  └──────────────┘      └──────────┬───────────┘     │
│                                   │                 │
│                                   ▼                 │
│  ┌─────────────────────────────────────────────┐   │
│  │         auto_trigger.py (触发器)            │   │
│  │  - 定时扫描 (5分钟)                         │   │
│  │  - 自动分配任务                             │   │
│  │  - 检查超时                                 │   │
│  │  - 更新看板                                 │   │
│  └──────────────────┬──────────────────────────┘   │
│                     │                                │
│          ┌──────────┴──────────┐                     │
│          ▼                     ▼                     │
│    ┌───────────┐        ┌───────────┐               │
│    │  Agent 1  │        │  Agent N  │               │
│    │  研究员   │        │  指挥官   │               │
│    │(自主领取) │        │(自主领取) │               │
│    └───────────┘        └───────────┘               │
│          │                     │                     │
│          └──────────┬──────────┘                     │
│                     ▼                                │
│  ┌─────────────────────────────────────────────┐   │
│  │         kanban.md (看板)                    │   │
│  │  - 实时任务状态                             │   │
│  │  - Agent状态追踪                           │   │
│  │  - 统计数据                                 │   │
│  └─────────────────────────────────────────────┘   │
│                                                       │
└─────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 文件 | 用途 |
|------|------|------|
| **任务池** | `task_pool.json` | 持久化存储任务和Agent状态 |
| **看板** | `kanban.md` | 可视化展示任务进度 |
| **触发器** | `auto_trigger.py` | 自动扫描、分配、监控 |
| **机制文档** | `AUTONOMOUS_MECHANISM.md` | 设计和使用说明 |

---

## 任务池机制

### 文件结构

```json
{
  "version": "1.0",
  "last_updated": "2026-03-01T02:17:00+08:00",
  "pool": {
    "pending": [],      // 待执行任务
    "in_progress": [],  // 进行中任务
    "completed": [],    // 已完成任务
    "failed": []        // 失败任务
  },
  "agents": {
    "commander": {...},
    "researcher": {...},
    "executor": {...},
    "innovator": {...}
  },
  "statistics": {
    "total_tasks": 0,
    "pending": 0,
    "in_progress": 0,
    "completed": 0,
    "failed": 0
  },
  "auto_allocation": {
    "enabled": true,
    "rules": [...]
  },
  "retry_policy": {
    "max_retries": 3,
    "backoff_seconds": 300
  }
}
```

### 任务对象结构

```json
{
  "id": "TASK-1709266620",           // 唯一ID
  "title": "任务标题",
  "description": "详细描述",
  "type": "research",                 // 任务类型
  "priority": "high",                 // 优先级: urgent/high/medium/low
  "status": "pending",                // 状态
  "created_at": "2026-03-01T02:17:00+08:00",
  "assigned_to": "researcher",        // 分配给谁
  "started_at": null,
  "completed_at": null,
  "progress": 0,                      // 进度 0-100
  "estimated_time": "2h",             // 预计时间
  "retry_count": 0,                   // 重试次数
  "reason": null                      // 失败原因
}
```

### 任务类型与能力映射

| 任务类型 | 优先分配 | 备选分配 | 说明 |
|---------|---------|---------|------|
| `research` | researcher | innovator | 研究、分析 |
| `analysis` | researcher | innovator | 数据分析 |
| `execution` | executor | commander | 执行、自动化 |
| `automation` | executor | - | 自动化脚本 |
| `design` | innovator | commander | 设计、架构 |
| `coordination` | commander | - | 协调、决策 |
| `monitoring` | executor | researcher | 监控、报告 |
| `generic` | executor | researcher/innovator/commander | 通用任务 |

### 优先级规则

触发器按以下顺序分配任务：

1. **urgent (紧急)** 🔴 - 最高优先级，立即分配
2. **high (高)** 🟡 - 高优先级，优先处理
3. **medium (中)** 🔵 - 普通优先级，正常处理
4. **low (低)** ⚪ - 低优先级，稍后处理

---

## 看板机制

### 看板作用

1. **可视化**: 清晰展示所有任务状态
2. **实时更新**: 任务变更自动同步
3. **进度追踪**: 实时了解项目进展
4. **Agent监控**: 查看每个Agent的工作状态

### 看板内容

| 板块 | 说明 |
|------|------|
| 任务统计 | 总览：待执行、进行中、已完成、失败的数量和百分比 |
| 待执行 | 等待分配的任务列表 |
| 进行中 | 正在执行的任务，显示进度 |
| 已完成 | 已完成的历史任务 |
| 失败 | 失败的任务，显示失败原因 |
| Agent状态 | 每个Agent的状态、当前任务数、最后活动时间 |
| 自动配置 | 系统自动配置的状态 |
| 提醒规则 | 系统提醒和警告规则 |

### 自动更新

看板由 `auto_trigger.py` 自动维护，**不要手动编辑**。

每次任务状态变更时：
1. 触发器读取 `task_pool.json`
2. 生成新的看板内容
3. 写入 `kanban.md`

---

## 自主工作触发器

### 工作原理

```
启动触发器
    │
    ▼
每隔5分钟扫描一次
    │
    ▼
1. 读取 task_pool.json
2. 查找待执行任务
3. 按优先级排序
4. 检查可用Agent
5. 自动分配任务
6. 检查超时任务
7. 检查任务积压
8. 保存任务池
9. 更新看板
    │
    ▼
继续循环...
```

### 核心功能

#### 1. 扫描待任务

```python
def scan_and_execute(self):
    # 查找到待执行任务
    pending_tasks = self._find_pending_tasks()

    # 按优先级排序
    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    pending_tasks.sort(key=lambda t: priority_order.get(t.get("priority", "medium"), 2))

    # 自动分配
    for task in pending_tasks:
        self._allocate_task(task)
```

#### 2. 智能分配

```python
def _allocate_task(self, task: Dict) -> bool:
    # 根据任务类型选择合适的Agent
    task_type = task.get("type")
    preferred_agents = allocation_rules.get(task_type)

    # 查找空闲的Agent
    for agent_id in preferred_agents:
        if self._check_agent_availability(agent_id):
            # 分配任务
            assign_task_to_agent(task, agent_id)
            return True
```

#### 3. 检查Agent可用性

```python
def _check_agent_availability(self, agent_id: str) -> bool:
    agent = self.task_pool["agents"].get(agent_id)

    # 空闲 = 可用
    if agent["status"] == "idle":
        return True

    # 活跃但任务未满 = 可用
    if agent["status"] == "active":
        current_tasks = len(agent.get("current_tasks", []))
        return current_tasks < 3

    return False
```

#### 4. 超时检查

```python
def _check_timeouts(self):
    # 检查执行超过2小时的任务
    for task in in_progress:
        elapsed = (now - started_at).total_seconds() / 3600
        if elapsed > 2:
            self._task_failed(task, reason="执行超时")
```

#### 5. 积压检查

```python
def _check_backlog(self):
    # 任务积压超过10个 → 警告
    if len(pending_tasks) > 10:
        self._log("⚠️ 任务积压警告")
```

### 运行方式

#### 方式1: 持续运行 (推荐)

```bash
cd /Users/variya/.openclaw/workspace/.commander
python3 auto_trigger.py
```

#### 方式2: 单次扫描

```bash
python3 auto_trigger.py --once
```

#### 方式3: 添加任务

```bash
python3 auto_trigger.py add "研究新技术" research high
```

#### 方式4: 后台运行

```bash
nohup python3 auto_trigger.py > auto_trigger.log 2>&1 &
```

### 日志记录

所有操作记录到 `auto_trigger.log`:

```
[2026-03-01 02:17:00] ==================================================
[2026-03-01 02:17:00] 开始扫描任务...
[2026-03-01 02:17:01] 发现 3 个待执行任务
[2026-03-01 02:17:02] ✓ 任务 TASK-1709266620 分配给 研究员 (任务类型: research)
[2026-03-01 02:17:03] ✓ 任务 TASK-1709266621 分配给 执行者 (任务类型: execution)
[2026-03-01 02:17:04] ✓ 任务 TASK-1709266622 分配给 指挥官 (任务类型: coordination)
[2026-03-01 02:17:05] 成功分配 3/3 个任务
[2026-03-01 02:17:06) ✓ 看板已更新
[2026-03-01 02:17:07] 扫描完成
[2026-03-01 02:17:08] ==================================================
[2026-03-01 02:17:09] 等待 300 秒...
```

---

## 失败重试机制

### 重试策略

```python
{
  "max_retries": 3,        # 最多重试3次
  "backoff_seconds": 300   # 重试间隔5分钟
}
```

### 失败处理流程

```
任务失败
    │
    ▼
1. 记录失败原因
2. 重试次数 +1
3. 检查重试次数
    │
    ├─ < 3 次重试 → 重新放回待执行队列
    │
    └─ ≥ 3 次重试 → 移入失败列表，通知人工审查
```

### 失败原因类型

| 原因 | 处理方式 |
|------|---------|
| 执行超时 | 重试，可能需要调整时间估算 |
| 资源不足 | 重试，或暂停等待资源 |
| Agent错误 | 切换Agent重试 |
| 依赖缺失 | 创建依赖任务，完成后重试 |
| 持续失败 | 标记为需要人工审查 |

### 超时设置

- **执行超时**: 2小时
- **重试间隔**: 5分钟
- **最大重试**: 3次

---

## Agent角色与职责

### Agent列表

| Agent ID | 名称 | 主要职责 | 能力 |
|----------|------|---------|------|
| `commander` | 指挥官 | 协调、决策、监控 | decision, coordination, monitoring |
| `researcher` | 研究员 | 研究、分析、数据处理 | research, analysis, data_processing |
| `executor` | 执行者 | 执行、自动化、监控 | execution, automation, monitoring |
| `innovator` | 创新者 | 设计、优化、架构 | design, optimization, architecture |

### Agent状态

- **idle** - 空闲，可以领取新任务
- **active** - 活跃，正在执行任务
- **busy** - 忙碌，任务已满（最多3个并发）

### Agent工作模式

#### 传统模式 (被动)

```
指挥官
  │
  ├─ 分析任务
  ├─ 选择合适的Agent
  ├─ 手动分配任务
  ├─ 等待执行完成
  └─ 收集结果
```

**问题**: 指挥官成为瓶颈，所有任务都要经过指挥官

#### 自主模式 (主动)

```
任务池
  │
  ├─ auto_trigger.py 每5分钟扫描
  ├─ 找到待执行任务
  ├─ Agent主动领取
  ├─ 立即执行
  └─ 更新状态
```

**优势**: 去中心化，自动运转，响应快

---

## 工作流程

### 完整生命周期

```
1. 创建任务
   用户/Agent → task_pool.json

2. 任务入池
   status: "pending"

3. 触发器扫描
   auto_trigger.py 每5分钟扫描

4. 自动分配
   根据类型和优先级分配给合适的Agent

5. Agent领取并执行
   status: "in_progress"
   progress: 0 → 100%

6. 正常完成
   status: "completed"

   失败则:
   status: "failed"
   retry_count +1

7. 重试逻辑
   retry_count < 3 → 重新分配
   retry_count ≥ 3 → 需要人工审查

8. 看板更新
   每次状态变更 → kanban.md 更新
```

### 示例流程

```
02:00 - 用户创建任务："研究新技术"
         → task_pool.json: pending

02:05 - trigger扫描，找到任务
         → 分配给 researcher
         → status: in_progress

02:06 - researcher开始研究
         → progress: 25%

02:30 - researcher继续执行
         → progress: 50%

03:00 - researcher执行中
         → progress: 75%

03:30 - 研究完成
         → status: completed
         → kanban.md 更新

04:00 - trigger再次扫描
         → 检查到已完成的任务
         → 统计更新
```

---

## 使用指南

### 快速开始

#### 1. 启动触发器

```bash
cd /Users/variya/.openclaw/workspace/.commander
python3 auto_trigger.py
```

#### 2. 创建任务

**方式A: 修改 task_pool.json**

```json
{
  "pool": {
    "pending": [
      {
        "id": "TASK-1",
        "title": "研究Alpha因子",
        "type": "research",
        "priority": "high",
        "status": "pending",
        "created_at": "2026-03-01T02:17:00+08:00",
        "progress": 0,
        "estimated_time": "2h"
      }
    ]
  }
}
```

**方式B: 使用Python脚本**

```python
from auto_trigger import add_task

add_task(
    title="研究Alpha因子",
    task_type="research",
    priority="high",
    description="探索新的Alpha因子策略"
)
```

**方式C: 使用命令行**

```bash
python3 auto_trigger.py add "研究Alpha因子" research high
```

#### 3. 查看看板

```bash
cat kanban.md
# 或在编辑器中打开
```

#### 4. Agent领取并执行

Agent读取任务池，找到分配给自己的任务，执行并更新进度。

#### 5. 任务完成

Agent将任务标记为完成：

```json
{
  "id": "TASK-1",
  "status": "completed",
  "progress": 100,
  "completed_at": "2026-03-01T04:30:00+08:00"
}
```

### Agent自主工作流程

**Agent应该遵循的工作模式:**

1. **启动时**: 读取任务池，找到分配给自己的任务
2. **执行中**: 每完成一个阶段，更新进度 (25%, 50%, 75%, 100%)
3. **完成后**: 将任务移入 `completed`
4. **失败时**: 记录失败原因，触发重试机制
5. **定期扫描**: 每隔一段时间检查是否有新任务分配给自己

**伪代码:**

```python
# Agent 主循环
while True:
    # 1. 读取任务池
    task_pool = load_task_pool()

    # 2. 找到分配给自己的任务
    my_tasks = [
        task for task in task_pool["pool"]["in_progress"]
        if task["assigned_to"] == AGENT_ID
    ]

    # 3. 如果有任务，执行
    if my_tasks:
        for task in my_tasks:
            execute_task(task)
            update_progress(task, progress)

    # 4. 如果没有任务，进入空闲
    if not my_tasks:
        update_agent_status("idle")
        sleep(60)  # 等待1分钟

    # 5. 检查是否有新任务
    new_tasks = check_new_tasks()
    if new_tasks:
        auto_claim(new_tasks)
```

### 任务管理命令

| 命令 | 说明 |
|------|------|
| `python3 auto_trigger.py` | 启动触发器 (持续运行) |
| `python3 auto_trigger.py --once` | 单次扫描 |
| `python3 auto_trigger.py add "标题" 类型 优先级` | 添加任务 |
| `cat task_pool.json` | 查看任务池 |
| `cat kanban.md` | 查看看板 |
| `tail -f auto_trigger.log` | 查看实时日志 |

---

## 最佳实践

### 任务创建

1. **明确任务类型** - 确保能分配给正确的Agent
2. **设置合理优先级** - 避免所有任务都是高优先级
3. **提供详细描述** - 帮助Agent理解任务目标
4. **估算完成时间** - 便于超时检测

### Agent执行

1. **及时更新进度** - 让看板反映真实状态
2. **记录关键信息** - 便于后续分析和改进
3. **处理失败异常** - 提供详细错误信息
4. **不修改任务ID** - 保持追踪一致性

### 监控和维护

1. **定期查看看板** - 了解整体进度
2. **检查失败任务** - 分析根本原因
3. **优化分配规则** - 根据实际情况调整
4. **备份任务池** - 定期保存快照

### 故障排除

| 问题 | 可能原因 | 解决方法 |
|------|---------|---------|
| 任务一直没有执行 | Agent忙碌或离线 | 检查Agent状态，重启触发器 |
| 任务频繁失败 | 任务描述不清或能力不匹配 | 调整任务类型或优先级 |
| 看板不更新 | 触发器未运行 | 启动auto_trigger.py |
| 任务积压严重 | 任务创建过快或Agent不足 | 增加触发频率或扩容Agent |

---

## 未来扩展

### 短期改进 (1-2周)

- [ ] 添加任务依赖管理 (任务A完成才能开始任务B)
- [ ] 支持任务标签和分类
- [ ] 增加任务历史记录
- [ ] 支持子任务嵌套

### 中期优化 (1个月)

- [ ] 智能负载均衡 (Agent能力评估和动态分配)
- [ ] 并发控制 (不同优先级的并发策略)
- [ ] Web界面 (图形化任务管理)
- [ ] 通知机制 (Slack/Telegram集成)

### 长期规划 (3个月+)

- [ ] 自学习能力 (根据历史分配优化策略)
- [ ] 跨组织协作 (多个工作空间协同)
- [ ] Agent市场 (动态加载和卸载Agent)
- [ ] AI决策 (GPT驱动的任务分解和分配)

---

## 附录

### 文件清单

```
.commander/
├── task_pool.json              # 任务池 (核心)
├── kanban.md                   # 看板 (可视化)
├── auto_trigger.py             # 触发器 (引擎)
├── auto_trigger.log            # 触发器日志
└── AUTONOMOUS_MECHANISM.md     # 本文档
```

### 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `SCAN_INTERVAL` | 300秒 | 触发器扫描间隔 |
| `MAX_RETRIES` | 3次 | 最大重试次数 |
| `TIMEOUT_HOURS` | 2小时 | 任务执行超时时间 |
| `BACKLOG_THRESHOLD` | 10个 | 任务积压警告阈值 |
| `MAX_CONCURRENT_TASKS` | 3个 | Agent最大并发任务数 |

### 联系方式

如有问题或建议，请联系：
- **负责人**: 创新者 (Innovator)
- **工作空间**: /Users/variya/.openclaw/workspace
- **文档位置**: .commander/AUTONOMOUS_MECHANISM.md

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-03-01 | 初始版本，完整自主机制 |

---

**🎯 核心理念**: 让组织自主运转，而不是依赖手动分配。
