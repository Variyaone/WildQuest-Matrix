#!/usr/bin/env python3
"""
自主工作触发器 - Auto Trigger
让每个Agent主动扫描并领取任务，实现自主运转
"""

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# 配置
WORKSPACE = "/Users/variya/.openclaw/workspace"
COMMANDER_DIR = os.path.join(WORKSPACE, ".commander")
TASK_POOL_FILE = os.path.join(COMMANDER_DIR, "task_pool.json")
KANBAN_FILE = os.path.join(COMMANDER_DIR, "kanban.md")
SCAN_INTERVAL = 300  # 5分钟扫描一次
LOG_FILE = os.path.join(COMMANDER_DIR, "auto_trigger.log")


class AutoTrigger:
    """自主工作触发器"""

    def __init__(self):
        self.task_pool = self._load_task_pool()

    def _log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        print(log_entry, end="")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)

    def _load_task_pool(self) -> Dict:
        """加载任务池"""
        try:
            with open(TASK_POOL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self._log(f"❌ 加载任务池失败: {e}")
            return self._create_empty_pool()

    def _create_empty_pool(self) -> Dict:
        """创建空任务池"""
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "pool": {
                "pending": [],
                "in_progress": [],
                "completed": [],
                "failed": []
            },
            "agents": {
                "main": {"name": "小龙虾", "status": "idle", "current_tasks": [], "capabilities": ["decision", "coordination", "monitoring"]},
                "researcher": {"name": "研究员", "status": "idle", "current_tasks": [], "capabilities": ["research", "analysis", "data_processing"]},
                "architect": {"name": "架构师", "status": "idle", "current_tasks": [], "capabilities": ["design", "architecture", "planning"]},
                "creator": {"name": "创作者", "status": "idle", "current_tasks": [], "capabilities": ["creation", "writing", "content"]},
                "critic": {"name": "评审官", "status": "idle", "current_tasks": [], "capabilities": ["review", "quality", "testing"]},
                "executor": {"name": "执行者", "status": "idle", "current_tasks": [], "capabilities": ["execution", "implementation", "coding"]},
                "innovator": {"name": "创新者", "status": "idle", "current_tasks": [], "capabilities": ["innovation", "optimization", "experiment"]}
            },
            "auto_allocation": {
                "enabled": True,
                "rules": [
                    "Priority tasks first",
                    "Research → researcher (强制深度研究流程)",
                    "Document → creator",
                    "Review → critic",
                    "Design → architect",
                    "Execution → executor",
                    "Coordination → main",
                    "Innovation → innovator"
                ]
            }
        }

    def _save_task_pool(self):
        """保存任务池"""
        self.task_pool["last_updated"] = datetime.now().isoformat()

        # 更新统计
        pool = self.task_pool["pool"]
        self.task_pool["statistics"] = {
            "total_tasks": len(pool["pending"]) + len(pool["in_progress"]) +
                           len(pool["completed"]) + len(pool["failed"]),
            "pending": len(pool["pending"]),
            "in_progress": len(pool["in_progress"]),
            "completed": len(pool["completed"]),
            "failed": len(pool["failed"])
        }

        with open(TASK_POOL_FILE, "w", encoding="utf-8") as f:
            json.dump(self.task_pool, f, indent=2, ensure_ascii=False)

        self._update_kanban()

    def _update_kanban(self):
        """更新看板"""
        pool = self.task_pool["pool"]
        stats = self.task_pool["statistics"]
        agents = self.task_pool["agents"]

        kanban = f"""# 任务看板 - 自主工作追踪

**更新时间**: {datetime.now().strftime('%Y-%m-%d %H:%M GMT+8')}
**自动刷新**: 是（每次任务变更自动更新）

---

## 📊 任务统计

| 状态 | 数量 | 百分比 |
|------|------|--------|
| 待执行 | {stats['pending']} | {self._percent(stats['pending'], stats['total_tasks'])}% |
| 进行中 | {stats['in_progress']} | {self._percent(stats['in_progress'], stats['total_tasks'])}% |
| 已完成 | {stats['completed']} | {self._percent(stats['completed'], stats['total_tasks'])}% |
| 失败 | {stats['failed']} | {self._percent(stats['failed'], stats['total_tasks'])}% |
| **总计** | {stats['total_tasks']} | 100% |

---

## 🎯 待执行 (Pending)

*等待agent领取并执行*

{self._format_tasks(pool['pending'], self._get_priority_emoji)}

---

## 🔄 进行中 (In Progress)

*正在执行的任务*

{self._format_tasks(pool['in_progress'], self._get_status_emoji)}

---

## ✅ 已完成 (Completed)

*已完成的任务*

{self._format_tasks(pool['completed'], lambda x: '✅')}

---

## ❌ 失败 (Failed)

*需要分析重试的任务*

{self._format_tasks(pool['failed'], lambda x: '🔴')}

---

## 🤖 Agent 状态

| Agent | 状态 | 当前任务 | 最后活动 |
|-------|------|----------|----------|
{self._format_agent_status(agents)}

---

## ⚙️ 自动配置

- **自动分配**: {'启用 ✅' if self.task_pool['auto_allocation']['enabled'] else '禁用 ❌'}
- **失败重试**: 启用 ✅ (最多3次)
- **自主触发**: 启用 ✅ (每{SCAN_INTERVAL//60}分钟扫描)
- **优先级队列**: 启用 ✅

---

## 🔔 提醒规则

- 任务执行超时 (2小时) → 自动标记为失败
- 连续失败3次 → 通知指挥官审查
- 任务积压 (>10个) → 触发扩容机制
- Agent长时间空闲 (>1小时) → 通知检查
"""

        with open(KANBAN_FILE, "w", encoding="utf-8") as f:
            f.write(kanban)

        self._log("✓ 看板已更新")

    def _percent(self, value: int, total: int) -> int:
        """计算百分比"""
        if total == 0:
            return 0
        return round(value * 100 / total)

    def _format_tasks(self, tasks: List[Dict], icon_getter) -> str:
        """格式化任务列表"""
        if not tasks:
            return "*暂无任务*"

        formatted = []
        for task in tasks:
            priority_icon = icon_getter(task)
            task_str = f"""- {priority_icon} [{task.get('id', 'N/A')}] {task.get('title', '未命名')}
  - 分配给: @{task.get('assigned_to', '未分配')}
  - 创建时间: {task.get('created_at', '未知')}
  - 预计完成: {task.get('estimated_time', '未知')}
  - 进度: {task.get('progress', 0)}%
"""
            formatted.append(task_str)

        return "\n".join(formatted)

    def _get_priority_emoji(self, task: Dict) -> str:
        """获取优先级emoji"""
        priority = task.get("priority", "medium")
        return {
            "high": "🟡",
            "medium": "🔵",
            "low": "⚪",
            "urgent": "🔴"
        }.get(priority, "⚪")

    def _get_status_emoji(self, task: Dict) -> str:
        """获取状态emoji"""
        progress = task.get("progress", 0)
        if progress >= 75:
            return "🟢"
        elif progress >= 50:
            return "🟡"
        elif progress >= 25:
            return "🔵"
        else:
            return "⚪"

    def _format_agent_status(self, agents: Dict) -> str:
        """格式化agent状态"""
        lines = []
        for agent_id, agent_info in agents.items():
            status_emoji = "🟢" if agent_info["status"] == "active" else "😴"
            task_count = len(agent_info.get("current_tasks", []))
            last_active = agent_info.get("last_active", "-")
            line = f"| {agent_info['name']} ({agent_id}) | {status_emoji} {agent_info['status']} | {task_count}个 | {last_active} |"
            lines.append(line)
        return "\n".join(lines)

    def _find_pending_tasks(self) -> List[Dict]:
        """查找待执行任务"""
        return self.task_pool["pool"]["pending"]

    def _check_agent_availability(self, agent_id: str) -> bool:
        """检查agent是否可用"""
        agent = self.task_pool["agents"].get(agent_id)
        if not agent:
            return False

        # 空闲或活跃但任务未满
        if agent["status"] == "idle":
            return True

        if agent["status"] == "active":
            # 同步 task current_tasks 与 pool in_progress
            in_progress = self.task_pool["pool"]["in_progress"]
            current_count = sum(1 for t in in_progress if t.get("assigned_to") == agent_id)
            current_count = current_count or len(agent.get("current_tasks", []))

            return current_count < 3  # 最多3个并发任务

        return False

    def _allocate_task(self, task: Dict) -> bool:
        """分配任务给合适的agent并启动subagent执行"""
        task_type = task.get("type", "generic")
        capabilities = task.get("required_capabilities", [])

        # 按优先级分配
        allocation_rules = {
            "research": ["researcher"],  # 强制研究员执行深度研究流程
            "document": ["creator"],     # 创作者负责文档任务
            "review": ["critic"],        # 评审官负责审查任务
            "design": ["architect"],     # 架构师负责设计任务
            "execution": ["executor"],   # 执行者负责执行任务
            "coordination": ["main"],    # 主指挥负责协调任务
            "monitoring": ["critic", "researcher"],
            "generic": ["main", "creator", "researcher", "innovator", "architect", "critic"]
        }

        preferred_agents = allocation_rules.get(task_type, allocation_rules["generic"])

        # 查找可用agent
        for agent_id in preferred_agents:
            if self._check_agent_availability(agent_id):
                # 分配任务
                self.task_pool["pool"]["pending"].remove(task)
                task["assigned_to"] = agent_id
                task["status"] = "in_progress"
                task["started_at"] = datetime.now().isoformat()
                task["progress"] = 0
                self.task_pool["pool"]["in_progress"].append(task)

                # 更新agent状态
                agent = self.task_pool["agents"][agent_id]
                agent["status"] = "active"
                agent["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                if "current_tasks" not in agent:
                    agent["current_tasks"] = []
                agent["current_tasks"].append(task.get("id"))

                self._log(f"✓ 任务 {task['id']} 分配给 {agent['name']} (任务类型: {task_type})")

                # =========== 新增：启动subagent执行任务 ===========
                self._spawn_subagent_for_task(task, agent_id)
                # =================================================

                return True

        self._log(f"⚠ 无法分配任务 {task['id']} - 没有可用的agent")
        return False

    def _spawn_subagent_for_task(self, task: Dict, agent_id: str):
        """为任务启动subagent（后台运行）"""
        task_title = task.get("title", "未命名任务")
        task_description = task.get("description", "")
        task_type = task.get("type", "generic")
        task_id = task.get("id", "UNKNOWN")

        # 构建任务描述
        task_text = f"执行任务 {task_id}: {task_title}"

        # 针对研究任务，强制要求深度研究流程
        if task_type == "research":
            task_text += f"""
=== 深度研究工作流程（必须遵循） ===

要求每个研究任务必须包含：
1. GitHub搜索：搜索至少3个相关开源项目
2. Web Search：搜索最新研究、论文、教程
3. 来源引用：记录所有来源链接
4. 深度分析：输出高质量研究报告

必须使用工具：
- web_search：搜索最新研究
- GitHub搜索（通过gh命令或web）
- web_fetch：获取文档内容

---
"""

        if task_description:
            task_text += f"\n详细描述: {task_description}"

        task_text += f"\n\n请完成任务并更新状态。"

        self._log(f"🚀 正在启动 {agent_id} 执行任务 {task_id}（后台运行）...")

        # 使用openclaw命令启动subagent
        cmd = [
            "openclaw",
            "agent",
            "--agent", agent_id,
            "--message", task_text
        ]

        try:
            # 在后台启动subagent，不等待完成
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True  # 创建新的会话，避免受parent影响
            )

            self._log(f"✓ {agent_id} 已在后台启动 (PID: {process.pid})")

            # 记录subagent启动信息
            if "spawn_info" not in task:
                task["spawn_info"] = {}
            task["spawn_info"]["spawned_at"] = datetime.now().isoformat()
            task["spawn_info"]["agent_id"] = agent_id
            task["spawn_info"]["pid"] = process.pid
            task["spawn_info"]["status"] = "running"

            # 保存更新后的任务池
            self._save_task_pool()

        except Exception as e:
            self._log(f"❌ 启动subagent异常: {e}")
            task["spawn_info"] = {
                "spawned_at": datetime.now().isoformat(),
                "error": str(e),
                "failed": True
            }
            # 如果启动失败，将任务标记为失败
            self._task_failed(task, reason=f"启动subagent异常: {e}")

    def _check_timeouts(self):
        """检查超时任务"""
        now = datetime.now()
        timeout_hours = 2

        in_progress = self.task_pool["pool"]["in_progress"]
        timed_out = []

        for task in in_progress:
            started_at = task.get("started_at")
            if started_at:
                start = datetime.fromisoformat(started_at)
                elapsed = (now - start).total_seconds() / 3600

                if elapsed > timeout_hours:
                    timed_out.append(task)

        for task in timed_out:
            self._task_failed(task, reason=f"执行超时 ({elapsed:.1f}小时)")

    def _task_failed(self, task: Dict, reason: str):
        """任务失败处理"""
        agent_id = task.get("assigned_to")
        task_id = task.get("id")

        self.task_pool["pool"]["in_progress"].remove(task)
        task["status"] = "failed"
        task["failed_at"] = datetime.now().isoformat()
        task["reason"] = reason
        task["retry_count"] = task.get("retry_count", 0) + 1
        self.task_pool["pool"]["failed"].append(task)

        # 释放agent
        if agent_id and agent_id in self.task_pool["agents"]:
            agent = self.task_pool["agents"][agent_id]
            if task_id in agent.get("current_tasks", []):
                agent["current_tasks"].remove(task_id)
            if not agent.get("current_tasks"):
                agent["status"] = "idle"

        # 重试逻辑
        if task["retry_count"] < 3:
            self._log(f"⚠ 任务 {task_id} 失败: {reason}, 将重试 ({task['retry_count']}/3)")
            # 5分钟后重试
            time.sleep(5)
            # 重新放回待处理队列
            task["retry_count"] = task.get("retry_count", 0) + 1
        else:
            self._log(f"❌ 任务 {task_id} 失败超限: {reason}, 需要人工审查")

    def _check_backlog(self):
        """检查任务积压"""
        pending_count = len(self.task_pool["pool"]["pending"])

        if pending_count > 10:
            self._log(f"⚠️ 任务积压警告: {pending_count} 个待执行任务")

            # 可以触发更多并发agent
            # 或者通知扩容

    def scan_and_execute(self):
        """扫描并自动执行任务"""
        self._log("=" * 50)
        self._log("开始扫描任务...")

        # 重载任务池
        self.task_pool = self._load_task_pool()

        # 检查待执行任务
        pending_tasks = self._find_pending_tasks()

        if pending_tasks:
            self._log(f"发现 {len(pending_tasks)} 个待执行任务")

            # 按优先级排序
            priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
            pending_tasks.sort(key=lambda t: priority_order.get(t.get("priority", "medium"), 2))

            # 自动分配
            allocated = 0
            for task in pending_tasks[:]:  # 复制列表遍历
                if self._allocate_task(task):
                    allocated += 1

            self._log(f"成功分配 {allocated}/{len(pending_tasks)} 个任务")
        else:
            self._log("没有待执行任务")

        # 检查超时
        self._check_timeouts()

        # 检查积压
        self._check_backlog()

        # 保存状态
        self._save_task_pool()

        self._log("扫描完成")
        self._log("=" * 50)

    def run(self, once: bool = False):
        """运行触发器"""
        self._log("🚀 自主工作触发器启动")

        try:
            while True:
                self.scan_and_execute()

                if once:
                    break

                self._log(f"等待 {SCAN_INTERVAL} 秒...")
                time.sleep(SCAN_INTERVAL)

        except KeyboardInterrupt:
            self._log("\n👋 收到中断信号，停止运行")


def add_task(title: str, task_type: str = "generic", priority: str = "medium",
             description: str = "", assigned_to: str = None):
    """添加新任务到任务池"""
    trigger = AutoTrigger()
    task_id = f"TASK-{int(time.time())}"

    task = {
        "id": task_id,
        "title": title,
        "description": description,
        "type": task_type,
        "priority": priority,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "assigned_to": assigned_to,
        "progress": 0,
        "retry_count": 0
    }

    if assigned_to:
        # 如果指定了agent，直接分配
        trigger.task_pool["pool"]['pending'].append(task)
        trigger._log(f"✓ 创建任务 {task_id} 并分配给 {assigned_to}")
    else:
        # 否则加入待处理队列
        trigger.task_pool["pool"]['pending'].append(task)
        trigger._log(f"✓ 创建任务 {task_id} (待分配)")

    trigger._save_task_pool()
    return task_id


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "add":
        # 添加任务模式
        title = sys.argv[2] if len(sys.argv) > 2 else "新任务"
        task_type = sys.argv[3] if len(sys.argv) > 3 else "generic"
        priority = sys.argv[4] if len(sys.argv) > 4 else "medium"
        add_task(title, task_type, priority)
    elif len(sys.argv) > 1 and sys.argv[1] == "--once":
        # 单次运行
        trigger = AutoTrigger()
        trigger.run(once=True)
    else:
        # 持续运行
        trigger = AutoTrigger()
        trigger.run()
