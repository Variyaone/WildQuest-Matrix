# 🛡️ 可靠性架构 - 解决大模型记忆缺陷

> **核心理念**: 把状态存在外部，让代码控制流程，而不是让LLM"记住"

## 问题本质

### 大模型的致命缺陷
1. **上下文会话隔离** - 每次 session 重启，上下文清零
2. **执行不可靠** - 容易"忘记"指令，跳过步骤
3. **幻觉** - 自信地编造不存在的信息
4. **注意力分散** - 在长任务中容易跑偏

### 当前痛点
- ❌ Agent 执行到一半被中断，需要重来
- ❌ 任务状态全靠 LLM "记得"，实际不存在
- ❌ 关键配置分散在对话中，不可追溯
- ❌ 多个 Agent 协作时，状态不一致

---

## 解决方案: 外部状态机架构

### 核心原则

```
1. 所有状态 → 存到文件 (不在 LLM 记忆中)
2. 所有关键信息 → 写到文档 (不在对话中)
3. 所有流程 → 由代码控制 (不由 LLM 自由发挥)
4. 所有步骤 → 有验证标准 (可检查可追溯)
```

### 架构层次

```
┌─────────────────────────────────────────────────┐
│  LLM Layer (大脑)                                 │
│  - 理解意图、生成策略、处理异常                    │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│  State Machine Layer (控制器)⭐                   │
│  - 定义状态转移                                   │
│  - 执行原子步骤                                   │
│  - 验证每个输出                                   │
│  - 异常恢复                                       │
└────────────────┬────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────┐
│  Memory Layer (外部记忆)⭐⭐                      │
│  - 任务状态 (JSON持久化)                          │
│  - 执行日志 (不可修改)                            │
│  - 检查点 (可恢复)                                │
│  - 配置文件 (版本控制)                            │
└─────────────────────────────────────────────────┘
```

---

## 核心组件设计

### 1️⃣ 任务状态机 (Task State Machine)

**文件位置**: `.commander/task_state.json`

```json
{
  "task_id": "quant-research-phase1",
  "status": "in_progress",  // pending, in_progress, done, failed, paused
  "current_step": "factor_ic_test",
  "steps": [
    {
      "step_id": "data_fetch",
      "status": "done",
      "output_path": ".commander/cache/data_20260227.csv",
      "completed_at": 1772205937566,
      "verified": true
    },
    {
      "step_id": "factor_ic_test",
      "status": "in_progress",
      "input_path": ".commander/cache/data_20260227.csv",
      "output_path": ".commander/output/ic_results.pkl",
      "started_at": 1772206000000,
      "dependencies": ["data_fetch"]
    }
  ],
  "checkpoints": {
    "last_checkpoint": "data_fetch",
    "checkpoint_data": {
        "factor_list": [...],
        "date_range": {...}
    }
  },
  "context": {
    "original_goal": "A股多因子研究 - 阶段1因子有效性检验",
    "created_by": "researcher",
    "created_at": 1772205937566,
    "total_estimated_time": "4h"
  },
  "error_recovery": {
    "last_error": null,
    "retry_count": 0,
    "max_retries": 3
  }
}
```

**关键特性**:
- ✅ **状态持久化** - 任何时候中断都可以从文件恢复
- ✅ **依赖追踪** - 知道哪些步骤依赖哪些前置条件
- ✅ **检查点** - 重要节点保存快照
- ✅ **可验证** - 每个步骤都有输出路径和验证标志
- ✅ **错误恢复** - 记录重试次数和错误信息

---

### 2️⃣ 执行日志 (Execution Log)

**文件位置**: `.commander/logs/task_<date>.jsonl`

每行一个JSON对象，追加写入，不可修改：

```json
{
  "timestamp": 1772205937566,
  "task_id": "quant-research-phase1",
  "step": "data_fetch",
  "agent": "researcher",
  "action": "start",
  "context": {"source": "akshare", "symbols": ["000001", "000002"]}
}
```

```json
{
  "timestamp": 1772205950000,
  "task_id": "quant-research-phase1",
  "step": "data_fetch",
  "agent": "researcher",
  "action": "complete",
  "output": {
    "path": ".commander/cache/data_20260227.csv",
    "records": 1250,
    "size": "2.3MB"
  }
}
```

**关键特性**:
- ✅ **不可篡改** - JSONL格式，只追加
- ✅ **可追溯** - 完整的执行历史
- ✅ **可分析** - 容易用脚本分析性能
- ✅ **可审计** - 知道谁在什么时候做了什么

---

### 3️⃣ 检查点系统 (Checkpoint System)

**文件位置**: `.commander/checkpoints/<task_id>_<timestamp>.json`

```json
{
  "task_id": "quant-research-phase1",
  "checkpoint_name": "after_data_cleaning",
  "timestamp": 1772205970000,
  "data_snapshot": {
    "cleaned_data_path": ".commander/cache/data_cleaned.pkl",
    "factor_list": ["pe_ratio", "pb_ratio", "roe", "momentum_30d"],
    "date_range": {"start": "2019-01-01", "end": "2023-12-31"},
    "universe": "CSI500"
  },
  "environment_snapshot": {
    "python_version": "3.14.3",
    "packages": {"pandas": "2.2.0", "numpy": "2.0.0"},
    "working_dir": "/Users/variya/.openclaw/workspace"
  }
}
```

**关键特性**:
- ✅ **快照恢复** - 可以回滚到任意检查点
- ✅ **环境隔离** - 记录环境和依赖版本
- ✅ **数据引用** - 保存数据路径，不重复存储

---

### 4️⃣ 验证标准 (Validation Standards)

**文件位置**: `.commander/validation/<step>_criteria.json`

```json
{
  "step": "factor_ic_test",
  "success_criteria": [
    {
      "check": "ic_mean_greater_than",
      "params": {"threshold": 0.02},
      "description": "IC均值 > 0.02"
    },
    {
      "check": "ic_ir_greater_than",
      "params": {"threshold": 0.5},
      "description": "ICIR > 0.5"
    },
    {
      "check": "monotonic_test",
      "params": {"p_value": 0.05},
      "description": "分组回测单调性显著"
    }
  ],
  "output_requirements": {
    "ic_result_path": ".commander/output/ic_results.pkl",
    "ir_result_path": ".commander/output/ir_results.pkl",
    "group_returns_path": ".commander/output/group_returns.pkl",
    "report_path": ".commander/reports/ic_test_report.md"
  }
}
```

**关键特性**:
- ✅ **明确标准** - 成功的定义清晰可量化
- ✅ **自动验证** - 可以写脚本自动检查
- ✅ **输出规范** - 每个步骤的输出文件路径预定义

---

## 任务执行流程

### 标准流程

```
1. 任务定义 → 写入 task_state.json (status=pending)

2. 加载状态 → 读取 task_state.json
   - 如果有未完成步骤 → 恢复
   - 如果是暂停任务 → 继续
   - 如果是失败任务 → 根据错误处理策略决定

3. 执行步骤
   - 读取 step 依赖的输入
   - 执行逻辑
   - 验证输出 (按 validation criteria)
   - 更新 task_state.json (step.status=done, verified=true)
   - 写入执行日志
   - 如果是关键节点 → 创建检查点

4. 下一步骤
   - 读取下一个 step
   - 检查依赖是否完成
   - 继续执行

5. 任务完成
   - 更新 status=done
   - 生成完成报告
   - 归档日志
```

### 异常处理

```
异常发生时：
1. 记录错误到 task_state.json (error_recovery)
2. 写入错误日志
3. 判断错误类型
   - 可恢复 → 重试 (最多3次)
   - 需要人工介入 → status=failed，发送通知
4. 如果有最近的检查点 → 恢复到检查点状态
```

---

## 实现工具

### 1. 状态机管理器 (state_machine.py)

```python
class TaskStateMachine:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.state_path = f".commander/task_state_{task_id}.json"
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """加载任务状态，不存在则创建"""
        if os.path.exists(self.state_path):
            with open(self.state_path) as f:
                return json.load(f)
        else:
            return {"task_id": task_id, "status": "pending", "steps": []}

    def get_current_step(self) -> dict:
        """获取当前执行的步骤"""
        for step in self.state.get("steps", []):
            if step["status"] == "in_progress":
                return step
            if step["status"] == "pending" and self._dependencies_met(step):
                return step
        return None

    def start_step(self, step_id: str, context: dict = None):
        """开始一个步骤"""
        step = self._find_step(step_id)
        step["status"] = "in_progress"
        step["started_at"] = time.time()
        if context:
            step["context"] = context
        self._save_state()

    def complete_step(self, step_id: str, output: dict, verified: bool = True):
        """完成一个步骤"""
        step = self._find_step(step_id)
        step["status"] = "done"
        step["completed_at"] = time.time()
        step["output"] = output
        step["verified"] = verified
        self._save_state()

    def fail_step(self, step_id: str, error: str):
        """步骤失败"""
        step = self._find_step(step_id)
        step["status"] = "failed"
        step["error"] = error
        self._increment_retry()
        self._save_state()

    def create_checkpoint(self, name: str, data: dict):
        """创建检查点"""
        checkpoint = {
            "task_id": self.task_id,
            "checkpoint_name": name,
            "timestamp": time.time(),
            "data_snapshot": data
        }
        path = f".commander/checkpoints/{self.task_id}_{name}_{int(time.time())}.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(checkpoint, f, indent=2)
        self.state["checkpoints"]["last_checkpoint"] = name
        self._save_state()

    def _save_state(self):
        """保存状态到文件"""
        with open(self.state_path, "w") as f:
            json.dump(self.state, f, indent=2)
```

### 2. 执行日志记录器 (execution_logger.py)

```python
class ExecutionLogger:
    def __init__(self, log_file: str = None):
        if log_file is None:
            date = datetime.now().strftime("%Y%m%d")
            log_file = f".commander/logs/task_{date}.jsonl"
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

    def log(self, task_id: str, step: str, agent: str,
            action: str, **kwargs):
        """记录执行日志"""
        entry = {
            "timestamp": time.time(),
            "task_id": task_id,
            "step": step,
            "agent": agent,
            "action": action,
            **kwargs
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_history(self, task_id: str) -> list:
        """获取任务的历史记录"""
        history = []
        with open(self.log_file) as f:
            for line in f:
                entry = json.loads(line)
                if entry["task_id"] == task_id:
                    history.append(entry)
        return history
```

### 3. 验证引擎 (validation_engine.py)

```python
class ValidationEngine:
    def __init__(self, validation_config_path: str):
        with open(validation_config_path) as f:
            self.config = json.load(f)

    def validate(self, step: str, output: dict) -> tuple[bool, list]:
        """验证步骤输出"""
        criteria = self.config.get(step, {}).get("success_criteria", [])
        results = []

        for criterion in criteria:
            check = criterion["check"]
            params = criterion.get("params", {})

            if check == "ic_mean_greater_than":
                ic_mean = output.get("ic_mean", 0)
                passed = ic_mean > params["threshold"]
                results.append({
                    "check": check,
                    "passed": passed,
                    "value": ic_mean,
                    "threshold": params["threshold"]
                })
            # ... 其他检查逻辑

        all_passed = all(r["passed"] for r in results)
        return all_passed, results
```

---

## 在OpenClaw中的集成

### Agent执行模板

每次给Agent分派任务时，包含一个标准模板：

```
任务名称: A股因子研究 - 阶段1

## 任务文件位置
- 状态文件: .commander/task_state_quant_phase1.json
- 验证标准: .commander/validation/factor_ic_test_criteria.json

## 执行要求
1. 加载状态文件，找到当前要执行的步骤
2. 如果是pending状态，从第一个步骤开始
3. 如果是in_progress状态，继续未完成的步骤
4. 每完成一个步骤：
   - 验证输出 (按验证标准)
   - 更新状态文件
   - 写入日志
   - 如果是关键节点，创建检查点
5. 如果遇到错误，记录到状态文件并设置重试次数

## 异常处理
- 最多重试 3 次
- 如果需要人工介入，更新状态为failed并发送通知

## 完成标准
- 所有步骤的 verified=true
- 生成完成报告到 .commander/reports/
```

---

## 心跳监控集成

在 HEARTBEAT.md 中加入：

```markdown
## 任务健康检查
- [ ] 检查 .commander/task_state_*.json 中的活跃任务
- [ ] 识别超过 2 小时没有更新的任务 (可能卡死)
- [ ] 检查错误任务 (status=failed)，发送通知
- [ ] 统计今日完成的任务数量
```

检查脚本：

```python
def check_task_health():
    """检查任务健康状态"""
    active_tasks = []
    for state_file in glob.glob(".commander/task_state_*.json"):
        with open(state_file) as f:
            state = json.load(f)

        if state["status"] == "in_progress":
            last_update = state.get("last_updated", 0)
            if time.time() - last_update > 7200:  # 2小时
                active_tasks.append({
                    "task_id": state["task_id"],
                    "stalled": True,
                    "current_step": state.get("current_step")
                })
            else:
                active_tasks.append({
                    "task_id": state["task_id"],
                    "stalled": False
                })

        if state["status"] == "failed":
            # 发送通知
            send_alert(f"任务 {state['task_id']} 失败: {state.get('error')}")

    return active_tasks
```

---

## 预期效果

### 可靠性提升
- ✅ **中段不丢失** - 任务可随时中断再恢复
- ✅ **状态可追溯** - 完整的执行历史
- ✅ **错误可恢复** - 自动重试 + 检查点恢复
- ✅ **输出可验证** - 每个步骤都有明确标准

### 执行效率
- ✅ **无需重复执行** - 从断点继续
- ✅ **并行安全** - 状态文件自动加锁
- ✅ **监控自动化** - 心跳检查自动发现卡死任务

### 团队协作
- ✅ **状态共享** - 所有Agent看到相同的状态
- ✅ **责任清晰** - 日志记录谁做了什么
- ✅ **交接顺畅** - 任务可由不同Agent继续完成

---

*由小龙虾🦞设计*
*创建时间: 2026-02-27 23:50*
