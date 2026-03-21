#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日大事生成器
每天自动生成当日大事总结
"""

import json
from datetime import datetime
from pathlib import Path

# 路径定义
COMMANDER_DIR = Path.home() / ".openclaw" / "workspace" / ".commander"
TASK_STATE_FILE = COMMANDER_DIR / "TASK_STATE.json"
MEMORY_FILE = Path.home() / ".openclaw" / "workspace" / "memory"


def load_today_memory():
    """加载今日记忆"""
    today = datetime.now().strftime("%Y-%m-%d")
    memory_file = MEMORY_FILE / f"{today}.md"

    if not memory_file.exists():
        return None

    with open(memory_file, 'r', encoding='utf-8') as f:
        return f.read()


def load_task_state():
    """加载任务状态"""
    if not TASK_STATE_FILE.exists():
        return None

    with open(TASK_STATE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_daily_summary():
    """生成每日大事总结"""
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 加载数据
    memory = load_today_memory()
    task_state = load_task_state()

    # 生成摘要
    summary_lines = [
        f"# 📅 每日大事 - {today}\n",
        f"**记录人**: 小龙虾 (main)",
        f"**生成时间**: {now}\n",
        "---\n",
    ]

    # 添加今日主要完成任务
    if task_state:
        summary_lines.append("## ✅ 今日完成任务\n\n")

        completed_tasks = task_state.get('completedTasks', [])
        today_tasks = [t for t in completed_tasks if today in t.get('completedAt', '')]

        if today_tasks:
            for task in today_tasks:
                summary_lines.append(f"### {task.get('name', '未知任务')}\n")
                summary_lines.append(f"- **完成时间**: {task.get('completedAt', '')}\n")
                summary_lines.append(f"- **执行者**: {task.get('agent', '')}\n")
                summary_lines.append("\n")
        else:
            summary_lines.append("今日无新完成任务\n\n")

    # 添加记忆摘要
    if memory and memory.strip():
        summary_lines.append("## 📝 今日记忆摘要\n\n")
        summary_lines.append(f"详见: `memory/{today}.md`\n\n")

    # 添加心跳日志最后几条
    if task_state:
        summary_lines.append("## ⏰ 今日关键事件\n\n")

        heartbeat_log = task_state.get('heartbeatLog', [])
        today_events = [h for h in heartbeat_log if today in h]

        if today_events:
            for event in today_events[-10:]:  # 最后10条
                summary_lines.append(f"- {event}\n")
            summary_lines.append("\n")
        else:
            summary_lines.append("今日无记录事件\n\n")

    # 保存
    output_file = COMMANDER_DIR / f"DAILY_SUMMARY_{today}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary_lines))

    print(f"✅ 每日大事已生成: {output_file}")
    return output_file


def main():
    """主函数"""
    print("=" * 60)
    print("📅 每日大事生成器")
    print("=" * 60)

    generate_daily_summary()

    print("=" * 60)
    print("✅ 生成完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
