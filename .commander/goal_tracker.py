#!/usr/bin/env python3
"""
长脚追踪与常态化任务执行器
"""

import json
import os
from datetime import datetime, timedelta

class GoalTracker:
    def __init__(self):
        self.goals_file = '.commander/LONG_TERM.goals'
        self.agents = {
            'researcher': '🕵️ 研究员',
            'architect': '🏗️ 架构师',
            'creator': '✍️ 创作者',
            'critic': '🔍 评审官',
            'innovator': '🚀 创新者'
        }

    def check_routine_tasks(self):
        """检查并触发agent常态化任务"""
        now = datetime.now()

        print(f"\n{'='*50}")
        print(f"常态化任务检查 - {now.strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*50}\n")

        for agent_id, agent_name in self.agents.items():
            tasks = self.get_routine_tasks(agent_id)

            if tasks:
                print(f"{agent_name} ({agent_id}):")
                for task in tasks:
                    if self.should_trigger(task, now):
                        print(f"  ✅ 触发: {task['name']}")
                    else:
                        print(f"  ⏸️  等待: {task['name']}")
                print()

    def get_routine_tasks(self, agent_id):
        """获取agent的常态化任务"""
        routine_tasks = {
            'researcher': [
                {'name': '数据质量检查', 'frequency': 'daily', 'time': '08:00'},
                {'name': '每日研究速递', 'frequency': 'daily', 'time': '12:00'},
                {'name': '策略评估', 'frequency': 'weekly', 'day': 'monday', 'time': '09:00'},
            ],
            'architect': [
                {'name': '系统健康检查', 'frequency': 'daily', 'time': '15:00'},
                {'name': '性能优化', 'frequency': 'weekly', 'day': 'monday', 'time': '09:00'},
            ],
            'creator': [
                {'name': '代码质量审查', 'frequency': 'daily', 'time': '18:00'},
                {'name': '文档同步', 'frequency': 'weekly', 'day': 'friday', 'time': '14:00'},
            ],
            'critic': [
                {'name': '每日代码审查', 'frequency': 'daily', 'time': '18:00'},
                {'name': '风险评估', 'frequency': 'weekly', 'day': 'monday', 'time': '09:00'},
            ],
            'innovator': [
                {'name': '系统熵值清理', 'frequency': 'daily', 'time': '00:00'},
                {'name': '流程优化', 'frequency': 'weekly', 'day': 'monday', 'time': '09:00'},
            ]
        }

        return routine_tasks.get(agent_id, [])

    def should_trigger(self, task, now):
        """判断是否应该触发任务"""
        hour = now.hour
        minute = now.minute
        current_time = f"{hour:02d}:{minute:02d}"

        if task['frequency'] == 'daily':
            # 简化：只要时间到了就触发
            return current_time >= task['time']

        elif task['frequency'] == 'weekly':
            weekday = now.strftime('%A').lower()
            day_match = weekday == task['day'].lower()
            time_match = current_time >= task['time']
            return day_match and time_match

        return False

    def progress_goals(self):
        """推进长期目标"""
        print(f"\n{'='*50}")
        print("长期目标推进检查")
        print(f"{'='*50}\n")

        goals = self.load_goals()

        for goal in goals:
            print(f"🎯 {goal['name']}")
            print(f"   进度: {goal.get('progress', 0)}%")
            print(f"   截止: {goal.get('deadline', 'N/A')}")
            print()

    def load_goals(self):
        """加载长期目标"""
        if os.path.exists(self.goals_file):
            with open(self.goals_file, 'r') as f:
                return json.load(f)
        return []

    def save_goals(self, goals):
        """保存长期目标"""
        with open(self.goals_file, 'w') as f:
            json.dump(goals, f, indent=2)

if __name__ == "__main__":
    tracker = GoalTracker()

    # 检查常态化任务
    tracker.check_routine_tasks()

    # 推进长期目标
    tracker.progress_goals()

    print("\n常态化任务检查完成")
