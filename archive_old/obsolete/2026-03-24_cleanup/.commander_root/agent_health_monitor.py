#!/usr/bin/env python3
"""
Agent健康监控器

功能：
1. 定期检查各Agent的lastActivity状态
2. 当Agent无活动超过阈值时触发告警
3. 生成健康报告和建议
4. 支持自动唤醒尝试（通过指挥官API）

作者: 创新者 (Innovator)
版本: 1.0
日期: 2026-02-27
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import argparse


class AgentHealthMonitor:
    """Agent健康监控器"""

    def __init__(self, config_path=None):
        """初始化监控器"""
        self.workspace = Path('/Users/variya/.openclaw/workspace/.commander')
        self.task_state_file = self.workspace / 'TASK_STATE.json'
        self.alert_log_file = self.workspace / 'AGENT_ALERTS.log'

        # 报告归档设置
        self.reports_dir = self.workspace / 'health_reports'
        self.reports_dir.mkdir(exist_ok=True)

        # 生成带时间戳的报告文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.report_file = self.reports_dir / f'AGENT_HEALTH_REPORT_{timestamp}.md'

        # 创建软链接（指向最新报告）
        self.symlink_latest = self.workspace / 'AGENT_HEALTH_REPORT.md'

        # 加载配置
        self.config = self._load_config(config_path)
        self.alerts = []

    def _load_config(self, config_path):
        """加载配置文件"""
        default_config = {
            'warning_threshold_hours': 6,   # 告警阈值
            'critical_threshold_hours': 12, # 严重告警阈值
            'timeout_threshold_hours': 24,  # 超时阈值
            'task_timeout_minutes': 240,    # 任务超时（4小时）
            'agents_to_monitor': ['main', 'researcher', 'architect', 'creator', 'critic']
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

    def parse_activity_time(self, time_str):
        """解析活动时间字符串"""
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

    def check_agent_health(self, task_state):
        """检查所有Agent的健康状态"""
        if not task_state or 'agentStates' not in task_state:
            print("❌ 任务状态中没有agentStates数据")
            return {}

        health_report = {}
        now = datetime.now()

        for agent_name, agent_state in task_state['agentStates'].items():
            if agent_name not in self.config['agents_to_monitor']:
                continue

            # 解析lastActivity时间
            last_activity_str = agent_state.get('lastActivity')
            last_activity = self.parse_activity_time(last_activity_str)

            if not last_activity:
                health_report[agent_name] = {
                    'status': 'unknown',
                    'message': '无法解析lastActivity时间'
                }
                continue

            # 计算停滞时间
            stale_duration = now - last_activity
            stale_hours = stale_duration.total_seconds() / 3600

            # 判断健康状态
            status = 'healthy'
            message = f"无活动 {stale_duration}"

            if stale_hours > self.config['timeout_threshold_hours']:
                status = 'timeout'
                message = f"严重超时: {stale_hours:.1f}小时"
                self._add_alert('critical', f"Agent {agent_name} 超时: {message}")

            elif stale_hours > self.config['critical_threshold_hours']:
                status = 'critical'
                message = f"严重告警: {stale_hours:.1f}小时"
                self._add_alert('warning', f"Agent {agent_name} 僵尸: {message}")

            elif stale_hours > self.config['warning_threshold_hours']:
                status = 'warning'
                message = f"告警: {stale_hours:.1f}小时"
                self._add_alert('info', f"Agent {agent_name} 较久无活动: {message}")

            health_report[agent_name] = {
                'status': status,
                'last_activity': last_activity_str,
                'stale_duration': str(stale_duration),
                'stale_hours': stale_hours,
                'message': message,
                'current_task': agent_state.get('currentTask'),
                'tasks_completed': agent_state.get('tasksCompleted', 0)
            }

        return health_report

    def check_task_timeout(self, task_state):
        """检查任务超时"""
        if not task_state or 'activeTasks' not in task_state:
            print("⚠️ 任务状态中没有activeTasks数据")
            return {}

        timeout_report = {}
        now = datetime.now()

        for task in task_state['activeTasks']:
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

            # 检查是否超时
            is_timeout = running_minutes > self.config['task_timeout_minutes']

            timeout_report[task_id] = {
                'name': task_name,
                'assigned_agent': assigned_agent,
                'status': status,
                'started_at': started_at_str,
                'running_duration': str(running_duration),
                'running_minutes': running_minutes,
                'is_timeout': is_timeout,
                'subtasks': task.get('subtasks', [])
            }

            if is_timeout:
                self._add_alert('critical',
                    f"任务超时: {task_name} (运行{running_minutes:.0f}分钟)")

        return timeout_report

    def _add_alert(self, level, message):
        """添加告警"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }
        self.alerts.append(alert)

    def save_alerts(self):
        """保存告警日志"""
        if not self.alerts:
            return

        # 创建文件（如果不存在）
        if not self.alert_log_file.exists():
            self.alert_log_file.parent.mkdir(parents=True, exist_ok=True)

        # 追加告警日志
        with open(self.alert_log_file, 'a', encoding='utf-8') as f:
            for alert in self.alerts:
                f.write(f"[{alert['timestamp']}] [{alert['level'].upper()}] {alert['message']}\n")

        print(f"💾 告警已保存: {self.alert_log_file}")

    def generate_report(self, health_report, timeout_report):
        """生成健康报告"""
        report_lines = [
            "# 🦞 Agent健康监控报告",
            "",
            f"**报告时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**监控Agent数量**: {len(health_report)}",
            f"**活跃任务数量**: {len(timeout_report)}",
            "",
            "---",
            "",
            "## 📊 Agent健康状态",
            "",
            "| Agent | 状态 | 无活动时长 | Last Activity | 当前任务 | 已完成任务 |",
            "|-------|------|-----------|---------------|---------|-----------|",
        ]

        for agent_name, info in health_report.items():
            # 状态图标
            status_icons = {
                'healthy': '✅',
                'warning': '⚠️',
                'critical': '🔴',
                'timeout': '💀',
                'unknown': '❓'
            }
            icon = status_icons.get(info['status'], '❓')

            report_lines.append(
                f"| {icon} {agent_name} | {info['status']} | "
                f"{info['stale_hours']:.1f}小时 | {info['last_activity']} | "
                f"{info['current_task'] or '无'} | {info['tasks_completed']} |"
            )

        report_lines.extend([
            "",
            "## ⏰ 任务超时检测",
            "",
        ])

        if not timeout_report:
            report_lines.append("✅ 无超时任务")
        else:
            report_lines.append("| 任务ID | 任务名称 | 分配给 | 运行时长 | 状态 | 子任务 |")
            report_lines.append("|--------|----------|--------|----------|------|--------|")

            for task_id, info in timeout_report.items():
                if info['is_timeout']:
                    status_icon = '🔴'
                    status_text = '超时'
                else:
                    status_icon = '✅'
                    status_text = '正常'

                subtasks = ', '.join(info.get('subtasks', [])[:2])
                if len(info.get('subtasks', [])) > 2:
                    subtasks += f" ...（共{len(info.get('subtasks', []))}个）"

                report_lines.append(
                    f"| {task_id} | {info['name']} | {info['assigned_agent']} | "
                    f"{info['running_minutes']:.0f}分钟 | {status_icon} {status_text} | {subtasks} |"
                )

        report_lines.extend([
            "",
            "## 🚨 告警列表",
            "",
        ])

        if not self.alerts:
            report_lines.append("✅ 无告警")
        else:
            for alert in self.alerts:
                report_lines.append(
                    f"- [{alert['level'].upper()}] {alert['message']} "
                    f"({alert['timestamp']})"
                )

        report_lines.extend([
            "",
            "## 🔧 建议措施",
            "",
        ])

        # 根据健康状态生成建议
        needs_action = False

        for agent_name, info in health_report.items():
            if info['status'] in ['critical', 'timeout']:
                needs_action = True
                report_lines.append(f"- **唤醒Agent {agent_name}** - "
                                  f"无活动{info['stale_hours']:.1f}小时，建议立即重新分配任务")

        for task_id, info in timeout_report.items():
            if info['is_timeout']:
                needs_action = True
                report_lines.append(f"- **处理超时任务** - 任务 '{info['name']}' 已运行"
                                  f"{info['running_minutes']:.0f}分钟，建议强制标记为timeout并重新分配")

        if not needs_action:
            report_lines.append("✅ 系统运行正常，无需干预")
        else:
            report_lines.append("")
            report_lines.append("**执行唤醒命令**:")
            report_lines.append("```bash")
            report_lines.append("# 手动唤醒Agent（通过指挥官）")
            report_lines.append("python3 agent_wakeup.py --agent main")
            report_lines.append("python3 agent_wakeup.py --agent researcher")
            report_lines.append("```")
            report_lines.append("")
            report_lines.append("**自动唤醒建议**:")
            report_lines.append("- 定期运行agent_health_monitor.py进行健康检查")
            report_lines.append("- 集成到cron job，每5-10分钟运行一次")
            report_lines.append("- 结合task_timeout_handler.py自动处理超时任务")

        report_content = '\n'.join(report_lines)

        # 保存报告
        self.report_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        # 更新软链接指向最新报告
        self.update_symlink()

        return report_content

    def update_symlink(self):
        """更新软链接 -> 最新报告"""
        try:
            # 删除旧软链接
            if self.symlink_latest.exists():
                self.symlink_latest.unlink()

            # 创建新软链接
            self.symlink_latest.symlink_to(self.report_file)
        except Exception as e:
            print(f"⚠️ 更新软链接失败: {e}")

    def cleanup_old_reports(self, days=7):
        """清理旧的健康报告（>N天）"""
        cutoff = datetime.now() - timedelta(days=days)
        old_reports = []

        for report_file in self.reports_dir.glob('AGENT_HEALTH_REPORT_*.md'):
            try:
                mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
                if mtime < cutoff:
                    old_reports.append(report_file)
            except Exception:
                continue

        deleted = 0
        for old_file in old_reports:
            try:
                old_file.unlink()
                deleted += 1
            except Exception:
                pass

        if deleted > 0:
            print(f"   🗑️  清理旧报告: {deleted}个")

        return deleted

    def run(self):
        """运行健康检查"""
        print("🦞 Agent健康监控器启动")
        print("="*60)

        # 加载任务状态
        task_state = self.load_task_state()
        if not task_state:
            print("❌ 无法加载任务状态，退出")
            return False

        # 检查Agent健康
        health_report = self.check_agent_health(task_state)

        # 检查任务超时
        timeout_report = self.check_task_timeout(task_state)

        # 保存告警
        self.save_alerts()

        # 生成报告
        report = self.generate_report(health_report, timeout_report)

        # 清理旧报告
        self.cleanup_old_reports(days=7)

        # 打印摘要
        print(f"\n📊 健康检查完成")
        print(f"  监控Agent: {len(health_report)}个")
        print(f"  活跃任务: {len(timeout_report)}个")
        print(f"  生成告警: {len(self.alerts)}个")
        print(f"  报告文件: {self.report_file}")

        # 打印关键信息
        print(f"\n🔑 关键信息:")
        for agent_name, info in health_report.items():
            if info['status'] != 'healthy':
                status_icon = '🔴' if info['status'] == 'timeout' else '⚠️'
                print(f"  {status_icon} {agent_name}: {info['message']}")

        for task_id, info in timeout_report.items():
            if info['is_timeout']:
                print(f"  🔴 任务超时: {info['name']} ({info['running_minutes']:.0f}分钟)")

        print("="*60)

        # 返回是否有问题
        has_issues = (
            any(info['status'] != 'healthy' for info in health_report.values()) or
            any(info['is_timeout'] for info in timeout_report.values())
        )

        return has_issues


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Agent健康监控器')
    parser.add_argument('--config', help='配置文件路径')
    args = parser.parse_args()

    monitor = AgentHealthMonitor(config_path=args.config)
    has_issues = monitor.run()

    # 返回退出码（0=正常，1=有问题）
    sys.exit(1 if has_issues else 0)


if __name__ == '__main__':
    main()
