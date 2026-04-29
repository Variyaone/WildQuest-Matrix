#!/usr/bin/env python3
"""
WildQuest Matrix - 非交互式执行脚本
直接调用核心功能，无需交互式输入
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.daily.unified_pipeline import run_unified_pipeline

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='WildQuest Matrix 非交互式执行')
    parser.add_argument('--mode', type=str, default='standard',
                       choices=['standard', 'fast', 'live', 'backtest'],
                       help='执行模式')
    parser.add_argument('--max-stocks', type=int, default=None,
                       help='最大股票数量')
    parser.add_argument('--max-factors', type=int, default=10,
                       help='最大因子数量（默认10，确保Alpha生成有足够因子）')
    parser.add_argument('--no-quality-gate', action='store_true',
                       help='禁用质量门控')
    parser.add_argument('--strategy', type=str, default=None,
                       help='策略名称或ID（如：ST00031 或 优化多因子策略）')
    
    args = parser.parse_args()
    
    print(f"开始执行 WildQuest Matrix - {args.mode.upper()} 模式")
    print("=" * 80)
    
    # 执行统一管线
    result = run_unified_pipeline(
        mode=args.mode,
        max_stocks=args.max_stocks,
        max_factors=args.max_factors,
        enable_quality_gate=not args.no_quality_gate,
        quality_gate_strict=True,
        strategy_id=args.strategy
    )
    
    print("=" * 80)
    print(f"执行完成！")
    print(f"状态: {'成功' if result.success else '失败'}")
    print(f"决策: {result.decision}")
    print(f"总步骤: {result.total_steps}")
    print(f"成功步骤: {result.completed_steps}")
    print(f"失败步骤: {result.failed_steps}")
    print(f"总耗时: {result.total_duration:.2f}秒")
    
    if not result.success:
        print("\n失败的步骤:")
        for step_result in result.step_results:
            if step_result.status != "success":
                print(f"  - {step_result.step_name}: {step_result.error}")
    
    return 0 if result.success else 1

if __name__ == "__main__":
    sys.exit(main())
