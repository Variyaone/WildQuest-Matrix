#!/usr/bin/env python3
"""
周报生成脚本
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path


class WeeklyReportGenerator:
    def __init__(self, commander_dir=".commander"):
        self.dir = Path(commander_dir)

    def load_tasks(self):
        """加载任务状态"""
        task_file = self.dir / "TASK_STATE.json"
        if task_file.exists():
            with open(task_file) as f:
                return json.load(f)
        return {}

    def load_daily_summaries(self):
        """加载每日总结"""
        summaries = []
        for file in self.dir.glob("DAILY_SUMMARY_*.md"):
            summaries.append(file.read_text())
        return summaries

    def generate_report(self):
        """生成周报"""
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())

        print(f"\n{'='*60}")
        print(f"📅 周报")
        print(f"{'='*60}\n")

        print(f"时间范围: {week_start.strftime('%Y-%m-%d')} 至 {today.strftime('%Y-%m-%d')}")

        # 任务统计
        tasks = self.load_tasks()
        completed = tasks.get('completedTasks', [])
        print(f"\n📊 任务统计:")
        print(f"  本周完成: {len(completed)} 个任务")

        # 最近完成的任务
        print(f"\n✅ 最近完成的任务:")
        for task in completed[:5]:
            completed_at = task.get('completedAt', 'N/A')
            name = task.get('name', 'Unknown')
            agent = task.get('agent', 'unknown')
            print(f"  - [{agent}] {name}")
            print(f"    完成时间: {completed_at}")

        # 关键事件
        print(f"\n🔑 关键事件:")
        print("  - A股量化系统启动")
        print("  - 可靠性架构设计完成")
        print("  - 系统熵值优化完成")

        print(f"\n{'='*60}\n")

        return f"""
# 📅 周报

时间范围: {week_start.strftime('%Y-%m-%d')} — {today.strftime('%Y-%m-%d')}

## 📊 任务统计

本周完成: {len(completed)} 个任务

## ✅ 最近完成任务

{chr(10).join([f"- [{task.get('agent', 'unknown')}] {task.get('name', 'Unknown')} ({task.get('completedAt', 'N/A')})" for task in completed[:5]])}

## 🔑 关键事件

- A股量化系统启动
- 可靠性架构设计完成
- 系统熵值优化完成

## 📝 备注

报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

def main():
    generator = WeeklyReportGenerator()
    report = generator.generate_report()

    # 保存报告
    output_file = f".commander/WEEKLY_REPORT_{datetime.now().strftime('%Y-%m-%d')}.md"
    with open(output_file, 'w') as f:
        f.write(report)

    print(f"✅ 周报已生成: {output_file}")

if __name__ == "__main__":
    main()
