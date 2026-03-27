#!/usr/bin/env python3
"""
每日任务早餐 - 生成任务列表和T0摘要
"""

import json
from pathlib import Path
from datetime import datetime

def read_t0():
    """读取T0任务"""
    t0_path = Path("/Users/variya/.openclaw/workspace/Sentinel/T0.md")
    if not t0_path.exists():
        return "无T0任务"

    with open(t0_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取T0任务部分
    if "无待决T0任务" in content:
        return "✅ 无待决T0任务"

    lines = content.split('\n')
    t0_section = []
    in_t0 = False
    for line in lines:
        if "当前T0任务" in line or in_t0:
            in_t0 = True
            t0_section.append(line)
            if "已处理T0任务" in line:
                break

    return '\n'.join(t0_section)

def read_task_pool():
    """读取任务池前30行"""
    pool_path = Path("/Users/variya/.openclaw/workspace/Sentinel/TASK_POOL.md")
    if not pool_path.exists():
        return "TASK_POOL.md不存在"

    with open(pool_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()[:30]

    return ''.join(lines)

def read_fix_progress():
    """读取P0修复进度"""
    progress_path = Path("/Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/P0_FIX_PROGRESS.md")
    if not progress_path.exists():
        return ""

    with open(progress_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()[:50]

    return ''.join(lines)

def daily_digest():
    """生成每日摘要"""
    now = datetime.now()

    digest = f"""# 📋 每日任务早餐

**时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}
**星期**: {now.strftime('%A')}

---

## 🔴 T0任务

{read_t0()}

---

## 📊 任务池摘要

{read_task_pool()}

---

## 🔧 P0修复进度

{read_fix_progress()}

---
*生成于 {now.strftime('%Y-%m-%d %H:%M:%S')}*
    """

    return digest

if __name__ == "__main__":
    print(daily_digest())
