#!/usr/bin/env python3
"""
熵值检查脚本
用于cron定期调用
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path


class EntropyChecker:
    def __init__(self, workspace='.commander'):
        self.workspace = Path(workspace)

    def count_files(self, directory, pattern="*"):
        """统计文件数量"""
        path = self.workspace / directory
        if not path.exists():
            return 0
        return len([f for f in path.glob(pattern) if f.is_file()])

    def get_directory_size(self, directory):
        """获取目录大小（MB）"""
        path = self.workspace / directory
        if not path.exists():
            return 0

        total = 0
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size

        return total / (1024 * 1024)  # MB

    def check_entropy(self):
        """检查系统熵值"""
        print(f"\n{'='*50}")
        print("🔍 系统熵值检查")
        print(f"{'='*50}\n")

        # 检查各项指标
        health_reports = self.count_files("health_reports")
        task_backups = self.count_files("task_state_backups")
        okx_temp_size = self.get_directory_size("archive") if (self.workspace / "archive").exists() else 0

        print("📊 当前状态:")
        print(f"  健康报告: {health_reports} 个")
        print(f"  任务备份: {task_backups} 个")
        print(f"  归档大小: {okx_temp_size:.1f} MB")

        # 计算熵值
        entropy_score = 0

        if health_reports > 20:
            entropy_score += (health_reports // 10)
            print(f"  ⚠️ 健康报告过多: +{health_reports // 10} 分")

        if task_backups > 30:
            entropy_score += (task_backups // 10)
            print(f"  ⚠️ 任务备份过多: +{task_backups // 10} 分")

        if okx_temp_size > 100:
            entropy_score += int(okx_temp_size / 50)
            print(f"  ⚠️ 归档过大: +{int(okx_temp_size / 50)} 分")

        print(f"\n🎯 熵值评分: {entropy_score}/100")

        if entropy_score < 20:
            print("✅ 系统状态良好")
        elif entropy_score < 50:
            print("⚠️ 建议清理")
        else:
            print("🔴 需要立即清理")

        print(f"\n{'='*50}\n")

        return {
            "health_reports": health_reports,
            "task_backups": task_backups,
            "archive_size_mb": okx_temp_size,
            "entropy_score": entropy_score,
            "timestamp": datetime.now().isoformat()
        }

def main():
    checker = EntropyChecker()
    result = checker.check_entropy()

    # 保存结果
    result_path = checker.workspace / 'entropy_status.json'
    # 确保父目录存在
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with open(result_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"✅ 检查完成，结果已保存: {result_path}")

if __name__ == "__main__":
    main()
