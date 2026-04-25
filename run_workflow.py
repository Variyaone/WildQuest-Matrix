#!/usr/bin/env python3
"""
运行 A 股量化工作流 - Standard 模式
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from core.daily.unified_pipeline import run_unified_pipeline

def main():
    """主函数"""
    print("=" * 80)
    print("开始运行 A 股量化工作流 - Standard 模式")
    print("=" * 80)
    print()

    # 检查环境变量
    webhook_url = os.getenv('FEISHU_WEBHOOK_URL')
    notification_enabled = os.getenv('ASA_NOTIFICATION_ENABLED')

    print(f"Webhook URL: {webhook_url}")
    print(f"通知启用: {notification_enabled}")
    print()

    # 运行工作流
    try:
        result = run_unified_pipeline(
            mode="standard",
            max_stocks=None,
            max_factors=None,
            enable_quality_gate=True,
            quality_gate_strict=True,
            rebalance_threshold=0.05,
            factor_decay_threshold=0.3,
        )

        print()
        print("=" * 80)
        print("工作流执行完成")
        print("=" * 80)
        print(f"状态: {result.status}")
        print(f"决策场景: {result.decision_scenario}")
        print(f"质量通过: {result.quality_passed}")
        print(f"执行时间: {result.duration_seconds:.2f} 秒")
        print()

        if result.details:
            print("详细信息:")
            for key, value in result.details.items():
                print(f"  {key}: {value}")

        print()
        print("=" * 80)

        return 0 if result.status == "success" else 1

    except Exception as e:
        print()
        print("=" * 80)
        print("工作流执行失败")
        print("=" * 80)
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("=" * 80)
        return 1

if __name__ == "__main__":
    sys.exit(main())
