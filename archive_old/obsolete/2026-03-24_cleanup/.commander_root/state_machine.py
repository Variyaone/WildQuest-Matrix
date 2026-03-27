#!/usr/bin/env python3
"""
任务状态机管理器
- 持久化任务状态到文件
- 支持任务中断恢复
- 依赖检查
- 检查点管理
"""

import json
import os
import time
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Step:
    """任务步骤"""
    step_id: str
    status: str  # pending, in_progress, done, failed
    dependencies: List[str]
    output_path: Optional[str] = None
    input_path: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    verified: bool = False
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    context: Optional[Dict] = None


@dataclass
class TaskState:
    """任务状态"""
    task_id: str
    status: str  # pending, in_progress, done, failed, paused
    steps: List[Dict]
    checkpoints: Dict[str, Any]
    context: Dict[str, Any]
    error_recovery: Dict[str, Any]
    created_at: float
    last_updated: float
    current_step: Optional[str] = None


class TaskStateMachine:
    """任务状态机"""

    def __init__(self, task_id: str, commander_dir: str = ".commander"):
        self.task_id = task_id
        self.commander_dir = Path(commander_dir)
        self.state_file = self.commander_dir / f"task_state_{task_id}.json"
        self.logger = ExecutionLogger()

        # 确保目录存在
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # 加载或创建状态
        self.state = self._load_state()

    def _load_state(self) -> TaskState:
        """加载任务状态"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                data = json.load(f)
            return TaskState(**data)
        else:
            # 创建新状态
            now = time.time()
            return TaskState(
                task_id=self.task_id,
                status="pending",
                steps=[],
                checkpoints={"last_checkpoint": None},
                context={},
                error_recovery={"last_error": None, "retry_count": 0, "max_retries": 3},
                created_at=now,
                last_updated=now
            )

    def _save_state(self):
        """保存状态到文件"""
        self.state.last_updated = time.time()
        with open(self.state_file, "w") as f:
            json.dump(asdict(self.state), f, indent=2, ensure_ascii=False)

    def add_steps(self, steps: List[Dict[str, Any]]):
        """添加任务步骤"""
        for step_data in steps:
            step_id = step_data["step_id"]
            if not self._find_step(step_id):
                new_step = {
                    "step_id": step_id,
                    "status": "pending",
                    "dependencies": step_data.get("dependencies", []),
                    "output_path": step_data.get("output_path"),
                    "input_path": step_data.get("input_path"),
                    "verified": False,
                    "retry_count": 0,
                    "max_retries": step_data.get("max_retries", 3)
                }
                self.state.steps.append(new_step)
        self._save_state()

    def _find_step(self, step_id: str) -> Optional[Dict]:
        """查找步骤"""
        for step in self.state.steps:
            if step["step_id"] == step_id:
                return step
        return None

    def _dependencies_met(self, step: Dict) -> bool:
        """检查依赖是否满足"""
        for dep_id in step.get("dependencies", []):
            dep_step = self._find_step(dep_id)
            if not dep_step or dep_step["status"] != "done":
                return False
        return True

    def get_current_step(self) -> Optional[Dict]:
        """获取当前要执行的步骤"""
        # 优先返回正在进行的步骤
        for step in self.state.steps:
            if step["status"] == "in_progress":
                self.state.current_step = step["step_id"]
                return step

        # 返回第一个可以开始的步骤
        for step in self.state.steps:
            if step["status"] == "pending" and self._dependencies_met(step):
                self.state.current_step = step["step_id"]
                return step

        return None

    def start_step(self, step_id: str, context: Dict = None):
        """开始一个步骤"""
        step = self._find_step(step_id)
        if not step:
            raise ValueError(f"Step {step_id} not found")

        if step["status"] != "pending":
            raise ValueError(f"Step {step_id} is not pending, current status: {step['status']}")

        step["status"] = "in_progress"
        step["started_at"] = time.time()
        if context:
            step["context"] = context

        self.state.status = "in_progress"
        self.state.current_step = step_id
        self._save_state()

        # 记录日志
        self.logger.log(
            task_id=self.task_id,
            step=step_id,
            agent="system",
            action="start",
            context=context
        )

    def complete_step(self, step_id: str, output: Dict, verified: bool = True):
        """完成一个步骤"""
        step = self._find_step(step_id)
        if not step:
            raise ValueError(f"Step {step_id} not found")

        step["status"] = "done"
        step["completed_at"] = time.time()
        step["output"] = output
        step["verified"] = verified

        self._save_state()

        # 检查是否所有步骤都完成
        if all(s["status"] == "done" for s in self.state.steps):
            self.state.status = "done"

        # 记录日志
        self.logger.log(
            task_id=self.task_id,
            step=step_id,
            agent="system",
            action="complete",
            output=output,
            verified=verified
        )

    def fail_step(self, step_id: str, error: str):
        """步骤失败"""
        step = self._find_step(step_id)
        if not step:
            raise ValueError(f"Step {step_id} not found")

        step["status"] = "failed"
        step["error"] = error
        step["retry_count"] += 1
        step["failed_at"] = time.time()

        # 更新错误恢复信息
        self.state.error_recovery["last_error"] = error
        self.state.error_recovery["retry_count"] += 1

        # 检查是否超过最大重试次数
        if step["retry_count"] >= step["max_retries"]:
            self.state.status = "failed"
        else:
            # 重置为pending以便重试
            step["status"] = "pending"

        self._save_state()

        # 记录日志
        self.logger.log(
            task_id=self.task_id,
            step=step_id,
            agent="system",
            action="fail",
            error=error,
            retry_count=step["retry_count"]
        )

    def pause_step(self, step_id: str, reason: str = None):
        """暂停一个步骤"""
        step = self._find_step(step_id)
        if not step:
            raise ValueError(f"Step {step_id} not found")

        step["status"] = "pending"  # 暂停=重置为pending
        self.state.status = "paused"

        self._save_state()

        # 记录日志
        self.logger.log(
            task_id=self.task_id,
            step=step_id,
            agent="system",
            action="pause",
            reason=reason
        )

    def create_checkpoint(self, name: str, data: Dict):
        """创建检查点"""
        checkpoint = {
            "task_id": self.task_id,
            "checkpoint_name": name,
            "timestamp": time.time(),
            "current_step": self.state.current_step,
            "data_snapshot": data
        }

        # 保存到单独的文件
        checkpoints_dir = self.commander_dir / "checkpoints"
        checkpoints_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_file = checkpoints_dir / f"{self.task_id}_{name}_{int(time.time())}.json"
        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint, f, indent=2, ensure_ascii=False)

        # 更新状态中的检查点引用
        self.state.checkpoints["last_checkpoint"] = name
        self.state.checkpoints["last_checkpoint_file"] = str(checkpoint_file)
        self._save_state()

        # 记录日志
        self.logger.log(
            task_id=self.task_id,
            step=self.state.current_step,
            agent="system",
            action="checkpoint",
            checkpoint_name=name,
            checkpoint_file=str(checkpoint_file)
        )

    def restore_checkpoint(self, checkpoint_path: str):
        """从检查点恢复"""
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)

        # 恢复数据快照
        # 注意：这里只是恢复状态引用，实际数据需要根据 checkpoint.data_snapshot 重新加载
        self.logger.log(
            task_id=self.task_id,
            step=checkpoint.get("current_step"),
            agent="system",
            action="restore_checkpoint",
            checkpoint_path=checkpoint_path
        )

        return checkpoint["data_snapshot"]

    def get_task_summary(self) -> Dict:
        """获取任务摘要"""
        total_steps = len(self.state.steps)
        done_steps = sum(1 for s in self.state.steps if s["status"] == "done")
        failed_steps = sum(1 for s in self.state.steps if s["status"] == "failed")

        return {
            "task_id": self.task_id,
            "status": self.state.status,
            "total_steps": total_steps,
            "done_steps": done_steps,
            "failed_steps": failed_steps,
            "progress": f"{done_steps}/{total_steps}",
            "current_step": self.state.current_step,
            "created_at": self.state.created_at,
            "last_updated": self.state.last_updated
        }


class ExecutionLogger:
    """执行日志记录器"""

    def __init__(self, commander_dir: str = ".commander"):
        self.commander_dir = Path(commander_dir)
        logs_dir = self.commander_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # 使用日期命名日志文件
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
        self.log_file = logs_dir / f"task_{date_str}.jsonl"

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
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_history(self, task_id: str) -> List[Dict]:
        """获取任务的历史记录"""
        history = []
        if not self.log_file.exists():
            return history

        with open(self.log_file) as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if entry["task_id"] == task_id:
                        history.append(entry)

        return history


def test_state_machine():
    """测试状态机"""
    # 创建状态机
    sm = TaskStateMachine("test_task")

    # 添加步骤
    steps = [
        {"step_id": "step1", "dependencies": [], "output_path": "/tmp/step1.txt"},
        {"step_id": "step2", "dependencies": ["step1"], "output_path": "/tmp/step2.txt"},
        {"step_id": "step3", "dependencies": ["step2"], "output_path": "/tmp/step3.txt"},
    ]
    sm.add_steps(steps)

    # 测试流程
    print("=== 测试状态机 ===")
    print(sm.get_task_summary())

    step = sm.get_current_step()
    print(f"\n当前步骤: {step}")
    sm.start_step("step1")
    sm.complete_step("step1", {"result": "done"}, verified=True)

    step = sm.get_current_step()
    print(f"\n当前步骤: {step}")
    sm.start_step("step2")
    sm.complete_step("step2", {"result": "done"}, verified=True)

    step = sm.get_current_step()
    print(f"\n当前步骤: {step}")
    sm.start_step("step3")
    sm.create_checkpoint("before_finish", {"data": "snapshot"})
    sm.complete_step("step3", {"result": "done"}, verified=True)

    print(f"\n最终状态: {sm.get_task_summary()}")
    print(f"\n历史记录:")
    history = sm.logger.get_history("test_task")
    for entry in history:
        print(f"  {entry}")

    # 清理
    sm.state_file.unlink(missing_ok=True)


if __name__ == "__main__":
    test_state_machine()
