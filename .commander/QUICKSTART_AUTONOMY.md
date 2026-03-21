# 组织自主机制快速上手指南

**创建时间**: 2026-03-01
**适用人群**: 想要快速了解和使用自主机制的所有Agent

---

## 🚀 5分钟快速开始

### 步骤1: 启动触发器

```bash
cd /Users/variya/.openclaw/workspace/.commander
python3 auto_trigger.py
```

保持这个窗口运行，触发器每5分钟自动扫描任务。

### 步骤2: 创建任务

**方式A - 命令行 (推荐)**:

```bash
python3 auto_trigger.py add "任务标题" 类型 优先级
```

示例：
```bash
python3 auto_trigger.py add "研究Alpha因子" research high
python3 auto_trigger.py add "执行量化回测" execution medium
python3 auto_trigger.py add "设计新架构" design high
```

**任务类型**:
- `research` - 研究任务 (分配给研究员)
- `execution` - 执行任务 (分配给执行者)
- `design` - 设计任务 (分配给创新者)
- `coordination` - 协调任务 (分配给指挥官)
- `generic` - 通用任务 (分配给任意可用Agent)

**优先级**:
- `urgent` - 紧急 🔴
- `high` - 高 🟡
- `medium` - 中 🔵
- `low` - 低 ⚪

**方式B - 编辑JSON**:

直接编辑 `.commander/task_pool.json`:

```json
{
  "pool": {
    "pending": [
      {
        "id": "TASK-1",
        "title": "你的任务标题",
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

### 步骤3: 查看自动分配

触发器会自动扫描，将任务分配给合适的Agent：

- 研究任务 → 研究员
- 执行任务 → 执行者
- 设计任务 → 创新者
- 协调任务 → 指挥官

### 步骤4: 查看看板

```bash
cat kanban.md
# 或在编辑器中打开
```

看板会实时显示：
- 任务统计
- 待执行、进行中、已完成、失败的任务
- Agent状态
- 自动配置状态

---

## 🔄 Agent如何自主工作

### Agent工作流程

1. **读取任务池**: 找到分配给自己的任务
2. **执行任务**: 完成任务要求的工作
3. **更新进度**: 每完成一个阶段，更新进度 (25% → 50% → 75% → 100%)
4. **完成任务**: 将任务移入 `completed`
5. **继续扫描**: 等待下一个任务

### Agent示例代码

```python
import json
import time
from datetime import datetime

# 配置
AGENT_ID = "researcher"  # 你的Agent ID
TASK_POOL_FILE = "/Users/variya/.openclaw/workspace/.commander/task_pool.json"

def load_task_pool():
    with open(TASK_POOL_FILE, "r") as f:
        return json.load(f)

def save_task_pool(pool):
    pool["last_updated"] = datetime.now().isoformat()
    with open(TASK_POOL_FILE, "w") as f:
        json.dump(pool, f, indent=2, ensure_ascii=False)

def update_kanban(pool):
    # 看板会自动由触发器更新
    pass

def find_my_tasks(pool):
    """找到分配给本Agent的任务"""
    my_tasks = [
        task for task in pool["pool"]["in_progress"]
        if task.get("assigned_to") == AGENT_ID
    ]
    return my_tasks

def update_progress(pool, task_id, progress, status=None):
    """更新任务进度"""
    for task in pool["pool"]["in_progress"]:
        if task["id"] == task_id:
            task["progress"] = progress
            if status:
                task["status"] = status
            if progress == 100:
                task["completed_at"] = datetime.now().isoformat()
                # 移入已完成
                pool["pool"]["in_progress"].remove(task)
                pool["pool"]["completed"].append(task)

                # 更新Agent状态
                agent = pool["agents"][AGENT_ID]
                if "current_tasks" in agent and task_id in agent["current_tasks"]:
                    agent["current_tasks"].remove(task_id)

                if not agent.get("current_tasks"):
                    agent["status"] = "idle"
            break
    return pool

def execute_task(task):
    """执行任务 - 替换为你的实际逻辑"""
    print(f"开始执行任务: {task['title']}")

    # 阶段1: 25%
    time.sleep(1)
    print("完成阶段 1 (25%)")
    pool = load_task_pool()
    pool = update_progress(pool, task["id"], 25)
    save_task_pool(pool)

    # 阶段2: 50%
    time.sleep(1)
    print("完成阶段 2 (50%)")
    pool = load_task_pool()
    pool = update_progress(pool, task["id"], 50)
    save_task_pool(pool)

    # 阶段3: 75%
    time.sleep(1)
    print("完成阶段 3 (75%)")
    pool = load_task_pool()
    pool = update_progress(pool, task["id"], 75)
    save_task_pool(pool)

    # 阶段4: 100%
    time.sleep(1)
    print("完成阶段 4 (100%)")
    pool = load_task_pool()
    pool = update_progress(pool, task["id"], 100, "completed")
    save_task_pool(pool)

    print(f"✓ 任务 {task['title']} 已完成")

def main_loop():
    """Agent主循环"""
    print(f"Agent {AGENT_ID} 启动...")

    while True:
        # 1. 读取任务池
        pool = load_task_pool()

        # 2. 找到分配给我的任务
        my_tasks = find_my_tasks(pool)

        # 3. 执行任务
        if my_tasks:
            print(f"发现 {len(my_tasks)} 个任务")
            for task in my_tasks:
                execute_task(task)
        else:
            print("没有任务，等待中...")
            # 进入空闲状态
            agent = pool["agents"][AGENT_ID]
            agent["status"] = "idle"
            save_task_pool(pool)

        # 4. 等待1分钟后再次检查
        time.sleep(60)

if __name__ == "__main__":
    main_loop()
```

---

## 📊 任务状态流转

```
创建任务
   ↓
pending (待执行)
   ↓
自动分配
   ↓
in_progress (进行中)
   ↓
   ├─ → completed (已完成)
   │
   └─ → failed (失败) → retry (重试) → 重新分配
```

---

## 🛠️ 常用命令

### 任务管理

```bash
# 添加任务
python3 auto_trigger.py add "标题" 类型 优先级

# 查看任务池
cat task_pool.json

# 查看看板
cat kanban.md

# 单次扫描 (不持续运行)
python3 auto_trigger.py --once
```

### 触发器管理

```bash
# 启动触发器 (持续运行)
python3 auto_trigger.py

# 后台运行
nohup python3 auto_trigger.py > auto_trigger.log 2>&1 &

# 停止后台触发器
ps aux | grep auto_trigger.py
kill <PID>

# 查看日志
tail -f auto_trigger.log
```

---

## 🎯 核心概念

### 任务池 (Task Pool)

- 所有任务的统一存储
- 自动分配给合适的Agent
- 实时追踪任务状态

### 触发器 (Trigger)

- 每5分钟扫描任务池
- 自动分配待执行任务
- 检查超时和失败
- 更新看板

### 看板 (Kanban)

- 实时任务状态可视化
- Agent状态监控
- 统计数据展示

### Agent

- 主从架构：指挥官 → 其他Agent
- 自主领取任务，不需要指挥官手动分配
- 支持并发执行 (最多3个任务)

---

## ⚠️ 注意事项

1. **不要手动编辑看板** - 看板由触发器自动生成
2. **启动触发器** - 必须启动 `auto_trigger.py` 才能自动分配任务
3. **Agent及时更新进度** - 让看板反映真实状态
4. **合理设置优先级** - 避免所有任务都是高优先级
5. **任务类型要准确** - 确保分配给正确的Agent

---

## 📚 更多信息

完整文档: `.commander/AUTONOMOUS_MECHANISM.md`

---

**🎯 核心理念**: 让组织自主运转，而不是依赖手动分配。
**✨ 目标**: 指挥官不再成为瓶颈，所有Agent都能自主工作。
