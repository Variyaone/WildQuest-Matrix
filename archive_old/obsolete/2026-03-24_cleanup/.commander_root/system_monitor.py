#!/usr/bin/env python3
"""
统一系统监控器 - 合并健康检查和超时处理
功能：
1. Agent健康监控（原agent_health_monitor.py）
2. 任务超时处理（原task_timeout_handler.py）
3. 系统资源监控（新增）
4. 组织效率分析（新增）

优势：
- 减少cron任务数量（从2个→1个）
- 统一监控入口
- 综合分析系统状态
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

class UnifiedSystemMonitor:
    """统一系统监控器"""
    
    def __init__(self):
        self.workspace = Path('/Users/variya/.openclaw/workspace/.commander')
        self.task_state_file = self.workspace / 'TASK_STATE.json'
        self.reports_dir = self.workspace / 'monitor_reports'
        self.reports_dir.mkdir(exist_ok=True)
        
        # 配置
        self.config = {
            'agent_warning_hours': 6,
            'agent_critical_hours': 12,
            'agent_timeout_hours': 24,
            'task_timeout_minutes': 240,
            'agents_to_monitor': ['main', 'researcher', 'architect', 'creator', 'critic', 'innovator']
        }
        
        self.alerts = []
        self.stats = {
            'agents_healthy': 0,
            'agents_warning': 0,
            'agents_critical': 0,
            'tasks_active': 0,
            'tasks_timeout': 0
        }
    
    def _log(self, message):
        """日志输出"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}")
    
    def check_agents_health(self):
        """检查Agent健康状态"""
        self._log("🔍 检查Agent健康状态...")
        
        if not self.task_state_file.exists():
            self._log("⚠️ TASK_STATE.json不存在")
            return {}
        
        try:
            with open(self.task_state_file, 'r', encoding='utf-8') as f:
                task_state = json.load(f)
        except Exception as e:
            self._log(f"❌ 读取TASK_STATE失败: {e}")
            return {}
        
        health_report = {}
        now = datetime.now()
        
        # 检查agentStates
        if 'agentStates' not in task_state:
            self._log("⚠️ 无agentStates数据")
            return {}
        
        for agent_name in self.config['agents_to_monitor']:
            if agent_name not in task_state['agentStates']:
                health_report[agent_name] = {
                    'status': 'unknown',
                    'message': '无状态数据'
                }
                continue
            
            agent_state = task_state['agentStates'][agent_name]
            last_activity_str = agent_state.get('lastActivity')
            
            if not last_activity_str:
                health_report[agent_name] = {
                    'status': 'unknown',
                    'message': '无活动记录'
                }
                continue
            
            # 解析时间
            try:
                if '+' in last_activity_str:
                    last_activity = datetime.fromisoformat(last_activity_str).replace(tzinfo=None)
                else:
                    last_activity = datetime.strptime(last_activity_str, '%Y-%m-%d %H:%M:%S')
                
                stale_hours = (now - last_activity).total_seconds() / 3600
                
                # 判断状态
                if stale_hours > self.config['agent_timeout_hours']:
                    status = 'timeout'
                    self.stats['agents_critical'] += 1
                    self.alerts.append(f"🔴 Agent {agent_name} 超时: {stale_hours:.1f}小时")
                elif stale_hours > self.config['agent_critical_hours']:
                    status = 'critical'
                    self.stats['agents_critical'] += 1
                    self.alerts.append(f"🟠 Agent {agent_name} 僵尸: {stale_hours:.1f}小时")
                elif stale_hours > self.config['agent_warning_hours']:
                    status = 'warning'
                    self.stats['agents_warning'] += 1
                    self.alerts.append(f"🟡 Agent {agent_name} 较久无活动: {stale_hours:.1f}小时")
                else:
                    status = 'healthy'
                    self.stats['agents_healthy'] += 1
                
                health_report[agent_name] = {
                    'status': status,
                    'stale_hours': stale_hours,
                    'last_activity': last_activity_str,
                    'current_task': agent_state.get('currentTask'),
                    'tasks_completed': agent_state.get('tasksCompleted', 0)
                }
                
            except Exception as e:
                health_report[agent_name] = {
                    'status': 'error',
                    'message': f'解析失败: {e}'
                }
        
        return health_report
    
    def check_tasks_timeout(self):
        """检查任务超时"""
        self._log("🔍 检查任务超时...")
        
        if not self.task_state_file.exists():
            return {}
        
        try:
            with open(self.task_state_file, 'r', encoding='utf-8') as f:
                task_state = json.load(f)
        except Exception as e:
            self._log(f"❌ 读取TASK_STATE失败: {e}")
            return {}
        
        timeout_report = {}
        
        if 'activeTasks' not in task_state:
            self._log("⚠️ 无activeTasks数据")
            return {}
        
        now = datetime.now()
        
        for task in task_state['activeTasks']:
            if task.get('status') != 'in_progress':
                continue
            
            self.stats['tasks_active'] += 1
            
            started_at_str = task.get('startedAt')
            if not started_at_str:
                continue
            
            try:
                if '+' in started_at_str:
                    started_at = datetime.fromisoformat(started_at_str).replace(tzinfo=None)
                else:
                    started_at = datetime.strptime(started_at_str, '%Y-%m-%d %H:%M:%S')
                
                running_minutes = (now - started_at).total_seconds() / 60
                
                is_timeout = running_minutes > self.config['task_timeout_minutes']
                
                timeout_report[task['id']] = {
                    'name': task['name'],
                    'assigned_agent': task.get('assignedAgent'),
                    'running_minutes': running_minutes,
                    'is_timeout': is_timeout
                }
                
                if is_timeout:
                    self.stats['tasks_timeout'] += 1
                    self.alerts.append(f"🔴 任务超时: {task['name']} ({running_minutes:.0f}分钟)")
                
            except Exception as e:
                self._log(f"⚠️ 解析任务时间失败: {e}")
        
        return timeout_report
    
    def check_system_resources(self):
        """检查系统资源"""
        self._log("🔍 检查系统资源...")
        
        resources = {
            'disk_usage': None,
            'memory_usage': None,
            'cpu_usage': None
        }
        
        try:
            # 磁盘使用
            result = subprocess.run(['df', '-h', '/Users'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 5:
                        resources['disk_usage'] = parts[4]
            
            # 内存使用（macOS）
            result = subprocess.run(['vm_stat'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # 简化处理，只记录是否成功
                resources['memory_available'] = True
            
        except Exception as e:
            self._log(f"⚠️ 资源检查失败: {e}")
        
        return resources
    
    def analyze_organization_efficiency(self, health_report, timeout_report):
        """分析组织效率"""
        self._log("📊 分析组织效率...")
        
        efficiency = {
            'agent_utilization': 0,
            'task_completion_rate': 0,
            'issues_count': len(self.alerts)
        }
        
        # 计算agent利用率
        if health_report:
            healthy_count = sum(1 for a in health_report.values() if a.get('status') == 'healthy')
            efficiency['agent_utilization'] = healthy_count / len(health_report) * 100
        
        # 计算任务完成率
        if timeout_report:
            timeout_count = sum(1 for t in timeout_report.values() if t.get('is_timeout'))
            efficiency['task_completion_rate'] = (len(timeout_report) - timeout_count) / len(timeout_report) * 100 if timeout_report else 100
        
        return efficiency
    
    def generate_report(self, health_report, timeout_report, resources, efficiency):
        """生成统一监控报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.reports_dir / f'MONITOR_REPORT_{timestamp}.md'
        
        lines = [
            "# 🦞 统一系统监控报告",
            "",
            f"**报告时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## 📊 系统概览",
            "",
            f"- **Agent健康**: {self.stats['agents_healthy']}/{len(self.config['agents_to_monitor'])}",
            f"- **Agent告警**: {self.stats['agents_warning']} 警告, {self.stats['agents_critical']} 严重",
            f"- **活跃任务**: {self.stats['tasks_active']}",
            f"- **超时任务**: {self.stats['tasks_timeout']}",
            f"- **告警总数**: {len(self.alerts)}",
            "",
            "---",
            "",
            "## 👥 Agent健康状态",
            "",
            "| Agent | 状态 | 无活动时长 | 当前任务 | 已完成 |",
            "|-------|------|-----------|---------|--------|",
        ]
        
        for agent_name, info in health_report.items():
            status_icons = {
                'healthy': '✅',
                'warning': '🟡',
                'critical': '🔴',
                'timeout': '💀',
                'unknown': '❓',
                'error': '❌'
            }
            icon = status_icons.get(info.get('status', 'unknown'), '❓')
            stale = info.get('stale_hours', 0)
            task = info.get('current_task', '无') or '无'
            completed = info.get('tasks_completed', 0)
            
            lines.append(f"| {icon} {agent_name} | {info.get('status', 'unknown')} | {stale:.1f}h | {task} | {completed} |")
        
        lines.extend([
            "",
            "---",
            "",
            "## 📋 任务状态",
            "",
        ])
        
        if not timeout_report:
            lines.append("✅ 无活跃任务")
        else:
            lines.append("| 任务ID | 任务名称 | 分配给 | 运行时长 | 状态 |")
            lines.append("|--------|----------|--------|----------|------|")
            
            for task_id, info in timeout_report.items():
                status = '🔴 超时' if info['is_timeout'] else '✅ 正常'
                lines.append(f"| {task_id} | {info['name']} | {info['assigned_agent']} | {info['running_minutes']:.0f}分钟 | {status} |")
        
        lines.extend([
            "",
            "---",
            "",
            "## 🚨 告警列表",
            "",
        ])
        
        if not self.alerts:
            lines.append("✅ 无告警")
        else:
            for alert in self.alerts:
                lines.append(f"- {alert}")
        
        lines.extend([
            "",
            "---",
            "",
            "## 💡 组织效率分析",
            "",
            f"- **Agent利用率**: {efficiency['agent_utilization']:.1f}%",
            f"- **任务完成率**: {efficiency['task_completion_rate']:.1f}%",
            f"- **问题数量**: {efficiency['issues_count']}",
            "",
            "---",
            "",
            "## 🔧 建议措施",
            "",
        ])
        
        if self.alerts:
            lines.append("⚠️ 发现问题，需要处理：")
            for alert in self.alerts[:5]:  # 只显示前5个
                lines.append(f"- {alert}")
        else:
            lines.append("✅ 系统运行正常，无需干预")
        
        report_content = '\n'.join(lines)
        
        # 保存报告
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        # 更新软链接
        symlink = self.workspace / 'MONITOR_REPORT.md'
        try:
            if symlink.exists():
                symlink.unlink()
            symlink.symlink_to(report_file)
        except Exception as e:
            self._log(f"⚠️ 更新软链接失败: {e}")
        
        self._log(f"📄 报告已生成: {report_file}")
        
        return report_content
    
    def run(self):
        """运行统一监控"""
        self._log("🦞 统一系统监控器启动")
        self._log("="*60)
        
        # 1. 检查Agent健康
        health_report = self.check_agents_health()
        
        # 2. 检查任务超时
        timeout_report = self.check_tasks_timeout()
        
        # 3. 检查系统资源
        resources = self.check_system_resources()
        
        # 4. 分析组织效率
        efficiency = self.analyze_organization_efficiency(health_report, timeout_report)
        
        # 5. 生成报告
        report = self.generate_report(health_report, timeout_report, resources, efficiency)
        
        self._log("="*60)
        self._log(f"✅ 监控完成")
        self._log(f"   Agent: {self.stats['agents_healthy']} 健康, {self.stats['agents_warning']} 警告, {self.stats['agents_critical']} 严重")
        self._log(f"   任务: {self.stats['tasks_active']} 活跃, {self.stats['tasks_timeout']} 超时")
        self._log(f"   告警: {len(self.alerts)} 个")
        
        # 返回是否有问题
        has_issues = len(self.alerts) > 0
        return has_issues


def main():
    """主函数"""
    monitor = UnifiedSystemMonitor()
    has_issues = monitor.run()
    
    # 返回退出码
    sys.exit(1 if has_issues else 0)


if __name__ == '__main__':
    main()
