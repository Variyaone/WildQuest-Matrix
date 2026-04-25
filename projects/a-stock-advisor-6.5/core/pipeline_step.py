"""
WildQuest Matrix - Pipeline Step CLI

Lobster工作流的单步执行入口，每个步骤输出JSON到stdout。

Usage:
    python -m core.pipeline_step <step_name> [--args-json '{}']

步骤列表:
    position_check    - 持仓状态检查
    data_update       - 数据更新
    data_quality      - 数据质量检查
    factor_calc       - 因子计算
    factor_validate   - 因子验证
    alpha_generate    - Alpha生成
    strategy_execute  - 策略执行
    portfolio_optimize - 组合优化
    risk_check        - 风控检查
    trading_execute   - 交易执行
    report_generate   - 报告生成
    monitor_push      - 监控推送
"""

import sys
import json
import argparse
from datetime import datetime
from typing import Dict, Any


def _run_step(step_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    from core.daily.unified_pipeline import UnifiedPipeline, PipelineMode

    pipeline = UnifiedPipeline(
        mode=PipelineMode.STANDARD,
        max_stocks=args.get("max_stocks"),
        max_factors=args.get("max_factors"),
        enable_quality_gate=args.get("enable_quality_gate", True),
        quality_gate_strict=args.get("quality_gate_strict", True),
        rebalance_threshold=args.get("rebalance_threshold", 0.05),
        factor_decay_threshold=args.get("factor_decay_threshold", 0.3),
    )

    step_map = {
        "position_check": 0,
        "data_update": 1,
        "data_quality": 2,
        "factor_calc": 3,
        "factor_validate": 4,
        "alpha_generate": 5,
        "strategy_execute": 6,
        "portfolio_optimize": 7,
        "risk_check": 8,
        "trading_execute": 9,
        "report_generate": 10,
        "monitor_push": 11,
    }

    step_id = step_map.get(step_name)
    if step_id is None:
        return {
            "ok": False,
            "error": f"Unknown step: {step_name}",
            "available_steps": list(step_map.keys()),
        }

    step_name_cn = {
        0: "持仓状态检查",
        1: "数据更新",
        2: "数据质量检查",
        3: "因子计算",
        4: "因子验证",
        5: "Alpha生成",
        6: "策略执行",
        7: "组合优化",
        8: "风控检查",
        9: "交易执行",
        10: "报告生成",
        11: "监控推送",
    }

    start = datetime.now()
    try:
        result = pipeline._execute_step(step_id, step_name_cn[step_id])
        end = datetime.now()
        return {
            "ok": result.status == "success",
            "step_id": step_id,
            "step_name": step_name,
            "status": result.status,
            "duration_seconds": (end - start).total_seconds(),
            "quality_passed": result.quality_passed,
            "quality_level": result.quality_level,
            "details": result.details,
            "error": result.error,
        }
    except Exception as e:
        end = datetime.now()
        return {
            "ok": False,
            "step_id": step_id,
            "step_name": step_name,
            "status": "failed",
            "duration_seconds": (end - start).total_seconds(),
            "error": str(e),
        }


def main():
    parser = argparse.ArgumentParser(description="WildQuest Matrix Pipeline Step CLI")
    parser.add_argument("step", nargs="?", default=None, help="Step name to execute")
    parser.add_argument("--args-json", default="{}", help="JSON args string")
    parser.add_argument("--list", action="store_true", help="List available steps")
    args = parser.parse_args()

    if args.list or args.step is None:
        steps = [
            "position_check",
            "data_update",
            "data_quality",
            "factor_calc",
            "factor_validate",
            "alpha_generate",
            "strategy_execute",
            "portfolio_optimize",
            "risk_check",
            "trading_execute",
            "report_generate",
            "monitor_push",
        ]
        print(json.dumps({"steps": steps}, indent=2))
        return 0

    try:
        step_args = json.loads(args.args_json) if args.args_json else {}
    except json.JSONDecodeError as e:
        print(json.dumps({"ok": False, "error": f"Invalid args-json: {e}"}))
        return 1

    result = _run_step(args.step, step_args)
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
