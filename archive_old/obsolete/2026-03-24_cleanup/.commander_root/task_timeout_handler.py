#!/usr/bin/env python3
"""
任务超时处理器

功能：
1. 监控TASK_STATE.json中的活跃任务
2. 检测停滞的任务（status=in_progress超过阈值时间）
3. 自动将超时任务标记为timeout或failed
4. 生成任务转派建议
5. 记录超时历史

作者: 创新者 (Innovator)
版本: 1.0
日期: 2026-02-27
"""

import json
import os
import sys
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import argparse


class TaskTimeoutHandler:
    """任务超时处理器"""

    def __init__(self, config_path=None):
        """初始化处理器"""
        self.workspace = Path('/Users/variya/.openclaw/workspace/.commander')
        self.task_state_file = self.workspace / 'TASK_STATE.json'
        self.backup_dir = self.workspace / 'task_state_backups'
        self.timeout_log_file = self.workspace / 'TASK_TIMEOUTS.log'

        # 加载配置
        self.config = self._load_config(config_path)
        self.handled_tasks = []

    def _load_config(self, config_path):
        """加载配置文件"""
        default_config = {
            'warning_timeout_minutes': 120,   # 告警超时（2小时）
            'critical_timeout_minutes': 240, # 严重超时（4小时）
            'fatal_timeout_minutes': 480,    # 致命超时（8小时）
            'auto_mark_timeout': True,       # 自动标记为timeout
            'auto_reassign': False,          # 自动重新分配（默认关闭）
            'backup_before_modify': True,    # 修改前备份
            'agent_fallback_map': {          # Agent备用映射
                'researcher': ['architect', 'creator'],
                'architect': ['researcher', 'creator'],
                'creator': ['researcher', 'architect'],
                'critic': ['researcher'],
                'main': ['researcher', 'architect']
            }
        }

        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)

        return default_config

    def load_task_state(self):
        """加载任务状态"""
        if not self.task_state_file.exists():
            print(f"❌ 任务状态文件不存在: {self.task_state_file}")
            return None

        try:
            with open(self.task_state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 读取任务状态失败: {e}")
            return None

    def backup_task_state(self):
        """备份任务状态"""
        if not self.config['backup_before_modify']:
            return True

        # 创建备份目录
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # 生成备份文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f'TASK_STATE_{timestamp}.json'

        # 复制文件
        try:
            shutil.copy2(self.task_state_file, backup_file)
            print(f"💾 任务状态已备份: {backup_file}")
            return True
        except Exception as e:
            print(f"⚠️ 备份失败: {e}")
            return False

    def parse_activity_time(self, time_str):
        """解析时间字符串"""
        if not time_str:
            return None

        try:
            # 尝试ISO格式
            if '+' in time_str:
                dt = datetime.fromisoformat(time_str)
                # 返回naive datetime（移除时区信息）
                return dt.replace(tzinfo=None)

            # 尝试其他格式
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue

            print(f"⚠️ 无法解析时间格式: {time_str}")
            return None
        except Exception as e:
            print(f"⚠️ 解析时间失败: {time_str}, {e}")
            return None

    def check_task_timeouts(self, task_state):
        """检查任务超时"""
        if not task_state or 'activeTasks' not in task_state:
            print("⚠️ 任务状态中没有activeTasks数据")
            return {}

        timeout_report = {}
        now = datetime.now()

        for task in task_state.get('activeTasks', []):
            # 添加类型检查，防止异常数据
            if not isinstance(task, dict):
                print(f"⚠️ 跳过格式错误的任务: {task}")
                continue

            task_id = task.get('id')
            task_name = task.get('name')
            started_at_str = task.get('startedAt')
            assigned_agent = task.get('assignedAgent')
            status = task.get('status')

            if status != 'in_progress':
                continue

            # 解析开始时间
            started_at = self.parse_activity_time(started_at_str)
            if not started_at:
                continue

            # 计算运行时间
            running_duration = now - started_at
            running_minutes = running_duration.total_seconds() / 60

            # 判断超时级别
            timeout_level = None
            if running_minutes > self.config['fatal_timeout_minutes']:
                timeout_level = 'fatal'
            elif running_minutes > self.config['critical_timeout_minutes']:
                timeout_level = 'critical'
            elif running_minutes > self.config['warning_timeout_minutes']:
                timeout_level = 'warning'

            timeout_report[task_id] = {
                'name': task_name,
                'assigned_agent': assigned_agent,
                'status': status,
                'started_at': started_at_str,
                'running_duration': str(running_duration),
                'running_minutes': running_minutes,
                'timeout_level': timeout_level,
                'should_handle': timeout_level in ['critical', 'fatal'],
                'subtasks': task.get('subtasks', []),
                'priority': task.get('priority', 'unknown'),
                'task_obj': task  # 保存原始任务对象
            }

        return timeout_report

    def handle_timeout_task(self, task_id, task_info, task_state):
        """处理超时任务"""
        if not self.config['auto_mark_timeout']:
            print(f"  ⏭️ 自动标记已禁用，跳过: {task_id}")
            return False

        task_name = task_info['name']
        agent = task_info['assigned_agent']

        # 标记任务为timeout
        for task in task_state.get('activeTasks', []):
            # 添加类型检查
            if not isinstance(task, dict):
                continue

            if task.get('id') == task_id:
                task['status'] = 'timeout'
                task['timeoutAt'] = datetime.now().isoformat()
                task['timeoutMessage'] = (
                    f"运行时间超过{task_info['running_minutes']:.0f}分钟，"
                    f"Agent {agent}无响应"
                )
                print(f"  ✅ 已标记为timeout: {task_name}")
                break

        return True

    def generate_reassign_suggestion(self, task_id, task_info):
        """生成任务重新分配建议"""
        agent = task_info['assigned_agent']
        fallback_agents = self.config['agent_fallback_map'].get(agent, [])

        if not fallback_agents:
            return "无备用Agent可用，需人工干预"

        # 选择最佳备用Agent（优先选择最近活跃的）
        # 这里简化处理，直接返回第一个可用Agent
        suggestion = {
            'task_id': task_id,
            'task_name': task_info['name'],
            'current_agent': agent,
            'priority': task_info['priority'],
            'suggested_agents': fallback_agents,
            'primary_suggestion': fallback_agents[0] if fallback_agents else None,
            'reason': f"原Agent {agent} 超时{task_info['running_minutes']:.0f}分钟无响应"
        }

        return suggestion

    def save_timeout_log(self, task_info, action_taken):
        """保存超时日志"""
        if not self.timeout_log_file.exists():
            self.timeout_log_file.parent.mkdir(parents=True, exist_ok=True)

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'task_id': task_info.get('task_id', 'unknown'),
            'task_name': task_info.get('name', 'unknown'),
            'assigned_agent': task_info.get('assigned_agent', 'unknown'),
            'running_minutes': task_info.get('running_minutes', 0),
            'timeout_level': task_info.get('timeout_level', 'unknown'),
            'action_taken': action_taken
        }

        with open(self.timeout_log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    def save_task_state(self, task_state):
        """保存任务状态"""
        try:
            task_state['lastUpdated'] = datetime.now().isoformat()

            with open(self.task_state_file, 'w', encoding='utf-8') as f:
                json.dump(task_state, f, indent=2, ensure_ascii=False)

            print(f"💾 任务状态已更新: {self.task_state_file}")
            return True
        except Exception as e:
            print(f"❌ 保存任务状态失败: {e}")
            return False

    def generate_report(self, timeout_report, reassign_suggestions):
        """生成超时处理报告"""
        report_lines = [
            "# ⏰ 任务超时处理报告",
            "",
            f"**报告时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**活跃任务数量**: {len(timeout_report)}",
            f"**超时任务数量**: {len(timeout_report)}",
            f"**处理任务数量**: {len(self.handled_tasks)}",
            "",
            "---",
            "",
            "## 📋 任务超时检测",
            "",
            "| 任务ID | 任务名称 | 分配给 | 运行时长 | 超时级别 | 处理状态 |",
            "|--------|----------|--------|----------|----------|----------|",
        ]

        count_warning = 0
        count_critical = 0
        count_fatal = 0
        count_handled = 0

        for task_id, info in timeout_report.items():
            # 超时级别图标
            level_icons = {
                'warning': '⚠️',
                'critical': '🔴',
                'fatal': '💀',
                None: '✅'
            }
            icon = level_icons.get(info['timeout_level'], '❓')

            # 处理状态
            handled = task_id in self.handled_tasks
            handled_text = '✅ 已处理' if handled else '⏭️ 未处理'

            report_lines.append(
                f"| {task_id} | {info['name']} | {info['assigned_agent']} | "
                f"{info['running_minutes']:.0f}分钟 | {icon} {info['timeout_level'] or '正常'} | "
                f"{handled_text} |"
            )

            # 统计
            if info['timeout_level'] == 'warning':
                count_warning += 1
            elif info['timeout_level'] == 'critical':
                count_critical += 1
            elif info['timeout_level'] == 'fatal':
                count_fatal += 1

            if handled:
                count_handled += 1

        report_lines.extend([
            "",
            "## 📊 超时统计",
            "",
        ])

        report_lines.append(f"- ⚠️ 告警超时（>2小时）: {count_warning}个")
        report_lines.append(f"- 🔴 严重超时（>4小时）: {count_critical}个")
        report_lines.append(f"- 💀 致命超时（>8小时）: {count_fatal}个")
        report_lines.append(f"- ✅ 已处理: {count_handled}个")

        report_lines.extend([
            "",
            "## 🔄 任务重新分配建议",
            "",
        ])

        if not reassign_suggestions:
            report_lines.append("✅ 无需重新分配的任务")
        else:
            report_lines.append("| 任务名称 | 原Agent | 优先级 | 建议Agent | 原因 |")
            report_lines.append("|----------|---------|--------|----------|------|")

            for suggestion in reassign_suggestions:
                primary = suggestion['primary_suggestion'] or '无'
                report_lines.append(
                    f"| {suggestion['task_name']} | {suggestion['current_agent']} | "
                    f"{suggestion['priority']} | {primary} | {suggestion['reason']} |"
                )

        report_lines.extend([
            "",
            "## 🔧 配置",
            "",
        ])

        report_lines.append(f"- 告警超时: {self.config['warning_timeout_minutes']}分钟")
        report_lines.append(f"- 严重超时: {self.config['critical_timeout_minutes']}分钟")
        report_lines.append(f"- 致命超时: {self.config['fatal_timeout_minutes']}分钟")
        report_lines.append(f"- 自动标记超时: {'启用' if self.config['auto_mark_timeout'] else '禁用'}")
        report_lines.append(f"- 自动重新分配: {'启用' if self.config['auto_reassign'] else '禁用'}")

        report_lines.extend([
            "",
            "## 📝 下一步",
            "",
        ])

        if any(info['should_handle'] for info in timeout_report.values()):
            report_lines.append("1. 查看超时任务详情，确认是否处理正确")
            report_lines.append("2. 根据重新分配建议，手动或自动分配新Agent")
            report_lines.append("3. 监控新Agent的任务执行情况")
            report_lines.append("4. 调查原Agent无响应的原因")
            report_lines.append("")
            report_lines.append("**执行命令**:")
            report_lines.append("```bash")
            report_lines.append("# 重新分配任务（需要手动执行或通过指挥官）")
            for suggestion in reassign_suggestions:
                if suggestion['primary_suggestion']:
                    report_lines.append(
                        f"# python3 task_reassign.py "
                        f"--task {suggestion['task_id']} "
                        f"--agent {suggestion['primary_suggestion']}"
                    )
            report_lines.append("```")
        else:
            report_lines.append("✅ 所有任务运行正常，无需干预")

        return '\n'.join(report_lines)

    def run(self):
        """运行超时处理器"""
        print("⏰ 任务超时处理器启动")
        print("="*60)

        # 加载任务状态
        task_state = self.load_task_state()
        if not task_state:
            print("❌ 无法加载任务状态，退出")
            return False

        # 备份任务状态
        if not self.backup_task_state():
            print("⚠️ 备份失败，但还是继续处理")

        # 检查任务超时
        timeout_report = self.check_task_timeouts(task_state)

        if not timeout_report:
            print("✅ 无活跃任务，退出")
            return False

        # 处理超时任务
        reassign_suggestions = []
        modified = False

        for task_id, task_info in timeout_report.items():
            if task_info['should_handle']:
                print(f"\n🔴 处理超时任务: {task_info['name']}")
                print(f"  - 任务ID: {task_id}")
                print(f"  - 分配给: {task_info['assigned_agent']}")
                print(f"  - 运行时长: {task_info['running_minutes']:.0f}分钟")
                print(f"  - 超时级别: {task_info['timeout_level']}")

                # 生成重新分配建议
                suggestion = self.generate_reassign_suggestion(task_id, task_info)
                if suggestion and not isinstance(suggestion, str):
                    reassign_suggestions.append(suggestion)
                    print(f"  - 建议分配给: {suggestion['primary_suggestion']}")

                # 处理任务
                if self.handle_timeout_task(task_id, task_info, task_state):
                    self.handled_tasks.append(task_id)
                    self.save_timeout_log(task_info, 'marked_as_timeout')
                    modified = True

        # 保存任务状态（如果有修改）
        if modified:
            self.save_task_state(task_state)

        # 生成报告
        report = self.generate_report(timeout_report, reassign_suggestions)

        # 保存报告
        report_file = self.workspace / 'TASK_TIMEOUT_REPORT.md'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        # 打印摘要
        print(f"\n📊 超时处理完成")
        print(f"  检查任务: {len(timeout_report)}个")
        print(f"  超时任务: {sum(1 for t in timeout_report.values() if t['timeout_level'])}个")
        print(f"  已处理: {len(self.handled_tasks)}个")
        print(f"  重新分配建议: {len(reassign_suggestions)}个")
        print(f"  报告文件: {report_file}")
        print("="*60)

        # 返回是否有需要处理的任务
        has_critical_tasks = any(
            info['timeout_level'] in ['critical', 'fatal']
            for info in timeout_report.values()
        )

        return has_critical_tasks


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='任务超时处理器')
    parser.add_argument('--config', help='配置文件路径')
    parser.add_argument('--dry-run', action='store_true', help='试运行模式（不修改文件）')
    args = parser.parse_args()

    handler = TaskTimeoutHandler(config_path=args.config)

    # 如果是试运行模式，禁用自动保存
    if args.dry_run:
        handler.config['auto_mark_timeout'] = False
        handler.config['backup_before_modify'] = False
        print("🔍 试运行模式：将只检测，不会修改任务状态")

    has_critical = handler.run()

    # 返回退出码（0=正常，1=有严重问题）
    sys.exit(1 if has_critical else 0)


if __name__ == '__main__':
    main()
