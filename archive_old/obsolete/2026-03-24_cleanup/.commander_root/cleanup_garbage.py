#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统垃圾文件清理脚本
删除无用的deleted sessions、过时文档、临时日志等
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta
import sys

# 配置路径
WORKSPACE_DIR = Path.home() / ".openclaw" / "workspace"
COMMANDER_DIR = WORKSPACE_DIR / ".commander"
AGENTS_DIR = Path.home() / ".openclaw" / "agents"
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"

# 备份目录
BACKUP_DIR = COMMANDER_DIR / "cleanup_backups"
ARCHIVE_DIR = WORKSPACE_DIR / "archive"

# 日志统计
stats = {
    "deleted_sessions": 0,
    "archived_docs": 0,
    "deleted_logs": 0,
    "deleted_backups": 0,
    "total_foldersizes": 0
}


def create_backup(original_files):
    """创建备份"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"backup_{timestamp}"
    backup_path.mkdir(parents=True, exist_ok=True)

    for filepath in original_files:
        if Path(filepath).exists():
            shutil.copy2(filepath, backup_path / Path(filepath).name)

    return backup_path


def get_file_age_days(filepath):
    """获取文件创建天数"""
    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
    age = datetime.now() - mtime
    return age.days


def cleanup_deleted_sessions(dry_run=True):
    """清理已删除的会话文件"""
    print("\n🔍 扫描已删除的会话文件...")

    deleted_files = []
    for agent_dir in AGENTS_DIR.glob("*/sessions/"):
        deleted_files.extend(agent_dir.glob("*.deleted.*"))

    if deleted_files:
        print(f"   找到 {len(deleted_files)} 个已删除会话文件")

        # 按年龄过滤（>7天的才删除）
        old_files = [f for f in deleted_files if get_file_age_days(f) > 7]

        if dry_run:
            print(f"   [预览] 将删除 {len(old_files)} 个旧文件（>7天）:")
            for f in old_files[:5]:
                print(f"      - {f}")
            if len(old_files) > 5:
                print(f"      ... 还有 {len(old_files) - 5} 个")
        else:
            if old_files:
                # 备份
                create_backup(old_files)
                # 删除
                for f in old_files:
                    if f.exists():
                        f.unlink()
                        print(f"   ✅ 删除: {f.name}")
                        stats["deleted_sessions"] += 1
    else:
        print("   ✅ 没有找到已删除的会话文件")


def cleanup_monitoring_logs(dry_run=True):
    """清理监控日志"""
    print("\n🔍 扫描监控日志文件...")

    log_files = [
        COMMANDER_DIR / "monitoring_cron.log",
        COMMANDER_DIR / "timeout_cron.log",
        COMMANDER_DIR / "AGENT_ALERTS.log",
    ]

    old_logs = [f for f in log_files if f.exists() and get_file_age_days(f) > 3]

    if old_logs:
        print(f"   找到 {len(old_logs)} 个旧日志文件（>3天）")

        if dry_run:
            for f in old_logs:
                size_kb = f.stat().st_size / 1024
                print(f"   [预览] 将删除: {f.name} ({size_kb:.1f} KB)")
        else:
            for f in old_logs:
                size_kb = f.stat().st_size / 1024
                f.unlink()
                print(f"   ✅ 删除: {f.name} ({size_kb:.1f} KB)")
                stats["deleted_logs"] += 1
    else:
        print("   ✅ 没有旧日志文件需要清理")


def cleanup_old_configs(dry_run=True):
    """清理旧备份配置"""
    print("\n🔍 扫描旧备份配置...")

    backup_file = Path.home() / ".openclaw" / "openclaw.json.bak"

    if backup_file.exists() and get_file_age_days(backup_file) > 7:
        size_kb = backup_file.stat().st_size / 1024
        print(f"   找到旧备份: {backup_file.name} ({size_kb:.1f} KB, {get_file_age_days(backup_file)}天)")

        if dry_run:
            print(f"   [预览] 将删除: {backup_file.name}")
        else:
            backup_file.unlink()
            print(f"   ✅ 删除: {backup_file.name}")
            stats["deleted_backups"] += 1
    else:
        print("   ✅ 没有需要清理的备份")


def archive_old_docs(dry_run=True):
    """归档过时文档"""
    print("\n🔍 扫描过时文档...")

    # 过时文档列表（2026-02-25之前的）
    old_docs = [
        "COMPLETE_STRATEGY_RESEARCH_PLAN.md",  # 12KB
        "OKX_API_RESEARCH.md",
        "OKX_API_USAGE_GUIDE.md",
        "OKX_DEMO_API_SOLUTION.md",
        "OKX_ISSUE_DIAGNOSIS.md",
        "OKX_TRADING_MANUAL_STUDY.md",
        "COMMANDER_DASHBOARD.md",
        "COMMANDER_WORKBOARD.md",
        "READY_TO_DEPLOY.md",
        "SIMULATION_STATUS_REPORT.md",
        "TRADING_FREQUENCY_EXPLANATION.md",
        "API_KEYS.md",
        "DECISION_CHECKLIST.md",
        "EVOMAP_IDEA.md",
    ]

    docs_to_archive = []
    for doc_name in old_docs:
        doc_path = COMMANDER_DIR / doc_name
        if doc_path.exists():
            docs_to_archive.append(doc_path)

    if docs_to_archive:
        print(f"   找到 {len(docs_to_archive)} 个过时文档")

        # 创建归档目录
        archive_month = datetime.now().strftime("%Y-%m")
        doc_archive_dir = ARCHIVE_DIR / "old_docs" / archive_month
        doc_archive_dir.mkdir(parents=True, exist_ok=True)

        total_size = 0
        if dry_run:
            for doc in docs_to_archive:
                size_kb = doc.stat().st_size / 1024
                days = get_file_age_days(doc)
                total_size += size_kb
                print(f"   [预览] 将归档: {doc.name} ({size_kb:.1f} KB, {days}天)")
            print(f"   总大小: {total_size:.1f} KB")
        else:
            for doc in docs_to_archive:
                size_kb = doc.stat().st_size / 1024
                shutil.move(doc, doc_archive_dir / doc.name)
                print(f"   ✅ 归档: {doc.name} ({size_kb:.1f} KB)")
                stats["archived_docs"] += 1
                stats["total_foldersizes"] += size_kb
    else:
        print("   ✅ 没有找到过时文档")


def cleanup_old_tasks(dry_run=True):
    """清理旧任务文件"""
    print("\n🔍 扫描旧任务文件...")

    old_tasks = [
        "20260227_005534_architect_tasks.md",
        "20260227_005534_creator_tasks.md",
        "20260227_005534_critic_tasks.md",
        "20260227_005534_researcher_tasks.md",
    ]

    task_archive_dir = ARCHIVE_DIR / "old_tasks"
    task_archive_dir.mkdir(parents=True, exist_ok=True)

    tasks_to_archive = []
    for task_name in old_tasks:
        task_path = COMMANDER_DIR / "team_tasks" / task_name
        if task_path.exists():
            tasks_to_archive.append(task_path)

    if tasks_to_archive:
        print(f"   找到 {len(tasks_to_archive)} 个旧任务文件")

        if dry_run:
            for task in tasks_to_archive:
                print(f"   [预览] 将归档: {task.name}")
        else:
            for task in tasks_to_archive:
                shutil.move(task, task_archive_dir / task.name)
                print(f"   ✅ 归档: {task.name}")
    else:
        print("   ✅ 没有找到旧任务文件")


def main():
    """主函数"""
    dry_run = True

    if "--apply" in sys.argv:
        dry_run = False
        print("🚀 执行模式：将实际删除文件")
    else:
        print("👀 预览模式：只显示将要删除的文件")

    print("=" * 60)
    print("🧹 系统垃圾清理工具")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 执行清理
    cleanup_deleted_sessions(dry_run)
    cleanup_monitoring_logs(dry_run)
    cleanup_old_configs(dry_run)
    archive_old_docs(dry_run)
    cleanup_old_tasks(dry_run)

    # 汇报
    print("\n" + "=" * 60)
    print("📊 清理统计")
    print("=" * 60)

    if dry_run:
        print("   (预览模式，实际操作需要使用 --apply)")
    else:
        print(f"   ✅ 删除会话文件: {stats['deleted_sessions']} 个")
        print(f"   ✅ 删除日志文件: {stats['deleted_logs']} 个")
        print(f"   ✅ 删除备份文件: {stats['deleted_backups']} 个")
        print(f"   📦 归档文档: {stats['archived_docs']} 个 ({stats['total_foldersizes']:.1f} KB)")
        print(f"\n   💾 备份位置: {BACKUP_DIR}")
        print(f"   📦 归档位置: {ARCHIVE_DIR}")

    print("=" * 60)


if __name__ == "__main__":
    main()
