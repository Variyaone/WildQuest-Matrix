"""
WildQuest Matrix - 自动化调度模块

针对个人用户的自动化调度：
1. Hermes Cronjob 集成
2. macOS launchd 配置生成
3. 简单的定时任务管理

Author: Variya
Version: 1.0.0
"""

import os
import json
from datetime import datetime, time
from typing import Dict, Any, List, Optional
from pathlib import Path


class AutomationScheduler:
    """自动化调度器"""

    def __init__(self, project_path: str, python_env: str = "venv"):
        """
        初始化调度器

        Args:
            project_path: 项目路径
            python_env: Python 环境路径（相对于项目路径）
        """
        self.project_path = os.path.abspath(project_path)
        self.python_env = python_env

    def generate_hermes_cronjob(
        self,
        name: str,
        schedule: str,
        command: str,
        skills: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        生成 Hermes Cronjob 配置

        Args:
            name: 任务名称
            schedule: 调度表达式（cron 格式）
            command: 执行命令
            skills: 需要的技能列表

        Returns:
            Cronjob 配置
        """
        config = {
            'action': 'create',
            'name': name,
            'schedule': schedule,
            'prompt': f"""
执行 {name} 任务：
cd {self.project_path}
source {self.python_env}/bin/activate
{command}
""",
            'workdir': self.project_path
        }

        if skills:
            config['skills'] = skills

        return config

    def generate_launchd_plist(
        self,
        label: str,
        command: str,
        schedule: Dict[str, int],
        log_dir: str = "/tmp"
    ) -> str:
        """
        生成 macOS launchd plist 文件内容

        Args:
            label: 任务标签（格式: com.username.taskname）
            command: 执行命令
            schedule: 调度配置，包含:
                - weekday: 星期几（0-6，0=周日，5=周一到周五）
                - hour: 小时（0-23）
                - minute: 分钟（0-59）
            log_dir: 日志目录

        Returns:
            plist 文件内容
        """
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>cd {self.project_path} && source {self.python_env}/bin/activate && {command}</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>{schedule.get('weekday', 5)}</integer>
        <key>Hour</key>
        <integer>{schedule.get('hour', 20)}</integer>
        <key>Minute</key>
        <integer>{schedule.get('minute', 0)}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{log_dir}/{label.replace('.', '_')}.log</string>
    <key>StandardErrorPath</key>
    <string>{log_dir}/{label.replace('.', '_')}_error.log</string>
</dict>
</plist>
"""
        return plist_content

    def save_launchd_plist(
        self,
        label: str,
        command: str,
        schedule: Dict[str, int],
        log_dir: str = "/tmp"
    ) -> str:
        """
        保存 launchd plist 文件

        Args:
            label: 任务标签
            command: 执行命令
            schedule: 调度配置
            log_dir: 日志目录

        Returns:
            plist 文件路径
        """
        plist_content = self.generate_launchd_plist(label, command, schedule, log_dir)

        # 创建 launchd 目录
        launchd_dir = os.path.expanduser("~/Library/LaunchAgents")
        os.makedirs(launchd_dir, exist_ok=True)

        # 保存 plist 文件
        plist_file = os.path.join(launchd_dir, f"{label}.plist")
        with open(plist_file, 'w', encoding='utf-8') as f:
            f.write(plist_content)

        print(f"launchd plist 文件已保存: {plist_file}")
        return plist_file

    def load_launchd(self, label: str) -> bool:
        """
        加载 launchd 任务

        Args:
            label: 任务标签

        Returns:
            是否成功
        """
        plist_file = os.path.expanduser(f"~/Library/LaunchAgents/{label}.plist")

        if not os.path.exists(plist_file):
            print(f"plist 文件不存在: {plist_file}")
            return False

        import subprocess
        result = subprocess.run(
            ['launchctl', 'load', plist_file],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"launchd 任务已加载: {label}")
            return True
        else:
            print(f"加载 launchd 任务失败: {result.stderr}")
            return False

    def unload_launchd(self, label: str) -> bool:
        """
        卸载 launchd 任务

        Args:
            label: 任务标签

        Returns:
            是否成功
        """
        plist_file = os.path.expanduser(f"~/Library/LaunchAgents/{label}.plist")

        if not os.path.exists(plist_file):
            print(f"plist 文件不存在: {plist_file}")
            return False

        import subprocess
        result = subprocess.run(
            ['launchctl', 'unload', plist_file],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f"launchd 任务已卸载: {label}")
            return True
        else:
            print(f"卸载 launchd 任务失败: {result.stderr}")
            return False

    def list_launchd_jobs(self) -> List[Dict[str, Any]]:
        """
        列出所有 launchd 任务

        Returns:
            任务列表
        """
        import subprocess
        result = subprocess.run(
            ['launchctl', 'list'],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"获取 launchd 任务列表失败: {result.stderr}")
            return []

        # 解析输出
        jobs = []
        for line in result.stdout.split('\n')[1:]:  # 跳过标题行
            if line.strip():
                parts = line.split()
                if len(parts) >= 3:
                    jobs.append({
                        'pid': parts[0],
                        'last_exit_code': parts[1],
                        'label': parts[2]
                    })

        return jobs


class TaskManager:
    """简单的任务管理器"""

    def __init__(self, config_file: str = "config/tasks.json"):
        """
        初始化任务管理器

        Args:
            config_file: 任务配置文件路径
        """
        self.config_file = config_file
        self.tasks = self._load_tasks()

    def _load_tasks(self) -> Dict[str, Any]:
        """加载任务配置"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'tasks': []}

    def _save_tasks(self) -> None:
        """保存任务配置"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, indent=2, ensure_ascii=False)

    def add_task(
        self,
        name: str,
        schedule: str,
        command: str,
        enabled: bool = True
    ) -> None:
        """
        添加任务

        Args:
            name: 任务名称
            schedule: 调度表达式
            command: 执行命令
            enabled: 是否启用
        """
        task = {
            'name': name,
            'schedule': schedule,
            'command': command,
            'enabled': enabled,
            'created_at': datetime.now().isoformat(),
            'last_run': None,
            'next_run': None
        }

        self.tasks['tasks'].append(task)
        self._save_tasks()
        print(f"任务已添加: {name}")

    def remove_task(self, name: str) -> bool:
        """
        删除任务

        Args:
            name: 任务名称

        Returns:
            是否成功
        """
        for i, task in enumerate(self.tasks['tasks']):
            if task['name'] == name:
                self.tasks['tasks'].pop(i)
                self._save_tasks()
                print(f"任务已删除: {name}")
                return True

        print(f"任务不存在: {name}")
        return False

    def list_tasks(self) -> List[Dict[str, Any]]:
        """
        列出所有任务

        Returns:
            任务列表
        """
        return self.tasks['tasks']

    def enable_task(self, name: str) -> bool:
        """
        启用任务

        Args:
            name: 任务名称

        Returns:
            是否成功
        """
        for task in self.tasks['tasks']:
            if task['name'] == name:
                task['enabled'] = True
                self._save_tasks()
                print(f"任务已启用: {name}")
                return True

        print(f"任务不存在: {name}")
        return False

    def disable_task(self, name: str) -> bool:
        """
        禁用任务

        Args:
            name: 任务名称

        Returns:
            是否成功
        """
        for task in self.tasks['tasks']:
            if task['name'] == name:
                task['enabled'] = False
                self._save_tasks()
                print(f"任务已禁用: {name}")
                return True

        print(f"任务不存在: {name}")
        return False


def setup_daily_pipeline(
    project_path: str,
    python_env: str = "venv",
    use_hermes: bool = True,
    use_launchd: bool = False
) -> None:
    """
    设置每日管线自动化

    Args:
        project_path: 项目路径
        python_env: Python 环境
        use_hermes: 是否使用 Hermes Cronjob
        use_launchd: 是否使用 launchd
    """
    scheduler = AutomationScheduler(project_path, python_env)

    if use_hermes:
        # 生成 Hermes Cronjob 配置
        cronjob_config = scheduler.generate_hermes_cronjob(
            name="a_stock_daily_pipeline",
            schedule="0 20 * * 1-5",  # 工作日 20:00
            command="asa daily",
            skills=["asa-quant"]
        )

        print("Hermes Cronjob 配置:")
        print(json.dumps(cronjob_config, indent=2, ensure_ascii=False))

        # 保存到文件
        config_file = os.path.join(project_path, "config/hermes_cronjob.json")
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(cronjob_config, f, indent=2, ensure_ascii=False)

        print(f"\n配置已保存到: {config_file}")
        print("使用以下命令创建 Cronjob:")
        print(f"  hermes cronjob create --config {config_file}")

    if use_launchd:
        # 生成并保存 launchd plist
        plist_file = scheduler.save_launchd_plist(
            label="com.variya.a_stock_daily",
            command="asa daily",
            schedule={
                'weekday': 5,  # 周一到周五
                'hour': 20,
                'minute': 0
            }
        )

        print(f"\nlaunchd plist 文件已保存: {plist_file}")
        print("使用以下命令加载任务:")
        print(f"  launchctl load {plist_file}")
        print("\n使用以下命令卸载任务:")
        print(f"  launchctl unload {plist_file}")


if __name__ == "__main__":
    # 测试代码
    print("自动化调度模块测试")

    # 测试调度器
    scheduler = AutomationScheduler(
        project_path="~/workspace/a-stock-advisor-6.5",
        python_env="venv"
    )

    # 生成 Hermes Cronjob 配置
    cronjob_config = scheduler.generate_hermes_cronjob(
        name="test_task",
        schedule="0 20 * * 1-5",
        command="echo 'Hello World'",
        skills=["test"]
    )
    print("Hermes Cronjob 配置:")
    print(json.dumps(cronjob_config, indent=2, ensure_ascii=False))

    # 生成 launchd plist
    plist_content = scheduler.generate_launchd_plist(
        label="com.variya.test",
        command="echo 'Hello World'",
        schedule={'weekday': 5, 'hour': 20, 'minute': 0}
    )
    print("\nlaunchd plist 内容:")
    print(plist_content)

    # 测试任务管理器
    task_manager = TaskManager(config_file="test_tasks.json")
    task_manager.add_task(
        name="test_task",
        schedule="0 20 * * 1-5",
        command="echo 'Hello World'"
    )
    print("\n任务列表:")
    print(json.dumps(task_manager.list_tasks(), indent=2, ensure_ascii=False))

    # 清理测试文件
    if os.path.exists("test_tasks.json"):
        os.remove("test_tasks.json")
