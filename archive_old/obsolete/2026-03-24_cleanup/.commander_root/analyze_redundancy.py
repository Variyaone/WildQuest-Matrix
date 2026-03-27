#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统冗余分析工具
识别系统中的重复功能、冗余操作、可合并流程
"""

import os
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime as DateTime

# 路径定义
COMMANDER_DIR = Path.home() / ".openclaw" / "workspace" / ".commander"
AGENT_DIRS = Path.home() / ".openclaw" / "agents"


def analyze_script_similarity():
    """分析脚本功能相似性"""
    print("\n🔍 分析脚本功能相似性...")

    scripts = {
        "agent_health_monitor.py": "健康监控 - 检查Agent状态，生成报告",
        "task_timeout_handler.py": "超时处理 - 监控任务超时，自动标记",
        "agent_permission_manager.py": "权限管理 - 应用模板，配置Agent",
        "dispatch_team.py": "任务分发 - 分发任务给Agent",
        "start_research_tasks.py": "研究启动 - 启动研究任务",
        "cleanup_garbage.py": "垃圾清理 - 清理归档",
    }

    # 识别冗余
    redundancies = []

    # 冗余1: dispatch_team.py vs start_research_tasks.py
    # 都是任务启动功能，可能可以合并
    redundancy_1 = {
        "type": "重复功能",
        "description": "任务分发脚本功能重复",
        "files": ["dispatch_team.py", "start_research_tasks.py"],
        "recommendation": "合并为统一的task_dispatcher.py",
        "priority": "high",
    }
    redundancies.append(redundancy_1)

    # 冗余2: agent_health_monitor.py 和 task_timeout_handler.py
    # 都在监控状态，可以整合为统一的监控器
    redundancy_2 = {
        "type": "功能重叠",
        "description": "监控功能分散，agent_health_monitor监控Agent，task_timeout_handler监控任务",
        "files": ["agent_health_monitor.py", "task_timeout_handler.py"],
        "recommendation": "整合为unified_monitor.py，统一监控Agent和任务",
        "priority": "medium",
    }
    redundancies.append(redundancy_2)

    # 冗余3: 备份机制分散
    cleanup_backups = COMMANDER_DIR / "cleanup_backups"
    task_state_backups = COMMANDER_DIR / "task_state_backups"
    if cleanup_backups.exists() and task_state_backups.exists():
        redundancy_3 = {
            "type": "分散备份",
            "description": "备份目录分散在多个位置",
            "locations": ["cleanup_backups/", "task_state_backups/", "~/.openclaw/openclaw.json.bak"],
            "recommendation": "统一为backups/目录，按类别组织",
            "priority": "low",
        }
        redundancies.append(redundancy_3)

    # 冗余4: cron jobs功能相近
    # 每5分钟健康检查 vs 每10分钟超时检测
    redundancy_4 = {
        "type": "Cron冗余",
        "description": "健康检查和超时检测都是监控，可以合并为一个统一脚本",
        "cron_jobs": ["agent_health_monitor.py", "task_timeout_handler.py"],
        "recommendation": "创建unified_monitor.py，每5分钟运行一次，同时检查Agent和任务",
        "priority": "high",
    }
    redundancies.append(redundancy_4)

    # 冗余5: 报告生成重复
    # AGENT_HEALTH_REPORT.md每次覆盖，旧报告丢失
    redundancy_5 = {
        "type": "报告管理",
        "description": "健康报告每次覆盖，历史数据丢失",
        "files": ["AGENT_HEALTH_REPORT.md", "TASK_TIMEOUT_REPORT.md"],
        "recommendation": "添加时间戳归档，保留历史报告",
        "priority": "medium",
    }
    redundancies.append(redundancy_5)

    # 冗余6: 文档重复
    # COMMANDER_DASHBOARD.md vs COMMANDER_WORKBOARD.md（已归档但需总结教训）
    redundancy_6 = {
        "type": "文档模板重复",
        "description": "dashboard和workboard功能重叠，导致维护困难",
        "lessons": "避免创建类似功能重复的文档模板",
        "recommendation": "统一为单一KANBAN.md模板",
        "priority": "archived",
    }
    redundancies.append(redundancy_6)

    return redundancies


def analyze_document_overlap():
    """分析文档内容重叠"""
    print("\n🔍 分析文档内容重叠...")

    overlaps = []

    # 已归档的重复文档
    archived_duplicates = [
        {
            "files": ["COMMANDER_DASHBOARD.md", "COMMANDER_WORKBOARD.md"],
            "reason": "功能重叠：都是Agent状态和任务展示",
            "resolution": "已合并为KANBAN.md，原文件已归档",
        },
    ]

    overlaps.extend(archived_duplicates)
    return overlaps


def analyze_process_redundancy():
    """分析流程冗余"""
    print("\n🔍 分析流程冗余...")

    processes = []

    # 流程冗余1: 权限配置流程
    # apply vs migrate vs import/export
    process_1 = {
        "type": "配置流程冗余",
        "description": "权限管理有多个命令（apply, migrate, import, export），功能有重叠",
        "commands": ["apply", "migrate", "import", "export"],
        "recommendation": "简化接口，apply为通用命令，detect自动识别配置状态",
        "priority": "high",
    }
    processes.append(process_1)

    # 流程冗余2: 备份流程
    # cleanup_garbage.py备份, agent_permission_manager.py备份, task_timeout_handler.py备份
    process_2 = {
        "type": "重复备份流程",
        "description": "多个脚本都有自己的备份逻辑",
        "scripts": ["cleanup_garbage.py", "agent_permission_manager.py", "task_timeout_handler.py"],
        "recommendation": "统一备份工具类，所有脚本复用同一个备份模块",
        "priority": "medium",
    }
    processes.append(process_2)

    # 流程冗余3: 配置验证重复
    # agent_permission_manager.py validate, openclaw doctor, 等等
    process_3 = {
        "type": "验证流程重复",
        "description": "多个地方都有配置验证逻辑",
        "validation_points": ["agent_permission_manager.py validate", "openclaw doctor", "cleanup_garbage.py"],
        "recommendation": "统一为validate_config模块",
        "priority": "medium",
    }
    processes.append(process_3)

    return processes


def generate_optimization_plan(redundancies, overlaps, processes):
    """生成优化方案"""
    print("\n📋 生成优化方案...")

    plan = {
        "high_priority": [],
        "medium_priority": [],
        "low_priority": [],
        "best_practices": [],
    }

    # 高优先级：严重影响效率或维护成本
    for r in redundancies + processes:
        if r.get("priority") == "high":
            plan["high_priority"].append(r)

    # 中优先级：可以提升效率但非阻塞
    for r in redundancies + processes:
        if r.get("priority") == "medium":
            plan["medium_priority"].append(r)

    # 低优先级：建议改进
    for r in redundancies + processes:
        if r.get("priority") == "low":
            plan["low_priority"].append(r)

    # 最佳实践
    for o in overlaps:
        plan["best_practices"].append(o)

    return plan


def main():
    """主函数"""
    print("=" * 60)
    print("🔍 系统冗余分析工具")
    print("=" * 60)

    # 分析
    redundancies = analyze_script_similarity()
    overlaps = analyze_document_overlap()
    processes = analyze_process_redundancy()

    # 生成方案
    plan = generate_optimization_plan(redundancies, overlaps, processes)

    # 输出
    print("\n" + "=" * 60)
    print("📊 冗余分析结果")
    print("=" * 60)

    print(f"\n🔴 高优先级优化项 ({len(plan['high_priority'])}个):")
    for i, item in enumerate(plan["high_priority"], 1):
        print(f"\n{i}. {item['type']}")
        print(f"   描述: {item['description']}")
        if "files" in item:
            print(f"   涉及: {', '.join(item['files'])}")
        if "cron_jobs" in item:
            print(f"   涉及: {', '.join(item['cron_jobs'])}")
        print(f"   建议: {item['recommendation']}")

    print(f"\n🟡 中优先级优化项 ({len(plan['medium_priority'])}个):")
    for i, item in enumerate(plan["medium_priority"], 1):
        print(f"\n{i}. {item['type']}")
        print(f"   描述: {item['description']}")
        print(f"   建议: {item['recommendation']}")

    print(f"\n🟢 低优先级优化项 ({len(plan['low_priority'])}个):")
    for i, item in enumerate(plan["low_priority"], 1):
        print(f"\n{i}. {item['type']}")
        print(f"   描述: {item['description']}")
        print(f"   建议: {item['recommendation']}")

    print(f"\n💡 最佳实践 ({len(plan['best_practices'])}个):")
    for i, item in enumerate(plan["best_practices"], 1):
        print(f"\n{i}. 避免文档功能重复")
        print(f"   示例: {item['files']}")
        print(f"   原因: {item['reason']}")
        print(f"   解决: {item['resolution']}")

    print("\n" + "=" * 60)
    print("✅ 分析完成")
    print("=" * 60)

    # 保存方案
    output_file = COMMANDER_DIR / "REDUNDANCY_ANALYSIS.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# 🔍 系统冗余分析报告\n\n")
        f.write(f"**生成时间**: {DateTime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**分析人**: 创新者 (Innovator)\n\n")
        f.write("## 🔴 高优先级优化\n\n")
        for i, item in enumerate(plan["high_priority"], 1):
            f.write(f"### {i}. {item['type']}\n\n")
            f.write(f"**描述**: {item['description']}\n\n")
            f.write(f"**建议**: {item['recommendation']}\n\n")

    print(f"\n📄 报告已保存: {output_file}")


if __name__ == "__main__":
    main()
