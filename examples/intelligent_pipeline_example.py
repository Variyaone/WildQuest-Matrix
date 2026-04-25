"""
WildQuest Matrix - 智能管线使用示例

展示如何在实际项目中使用智能管线系统

Author: Variya
Version: 1.0.0
"""

import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.pipeline import (
    IntelligentPipeline,
    create_intelligent_pipeline,
    QualityGateManager,
    GateStatus,
    ReviewDecision,
)


# ============================================================================
# 步骤执行函数示例
# ============================================================================

def execute_position_check():
    """步骤 0: 持仓状态检查"""
    print("执行持仓状态检查...")

    # 这里应该调用实际的持仓检查逻辑
    # 简化实现：
    result = {
        'position_status': 'empty',  # empty, holding, liquidating
        'current_positions': [],
        'total_value': 0.0,
        'cash': 1000000.0,
    }

    print(f"持仓状态: {result['position_status']}")
    return result


def execute_data_update():
    """步骤 1: 数据更新"""
    print("执行数据更新...")

    # 这里应该调用实际的数据更新逻辑
    # 简化实现：
    result = {
        'updated_stocks': 95,
        'total_stocks': 100,
        'rows_added': 4750,
        'update_time': datetime.now().isoformat(),
    }

    print(f"更新了 {result['updated_stocks']}/{result['total_stocks']} 只股票")
    return result


def execute_data_quality_check():
    """步骤 2: 数据质量检查"""
    print("执行数据质量检查...")

    # 这里应该调用实际的数据质量检查逻辑
    # 简化实现：
    result = {
        'completeness': 0.95,
        'accuracy': 0.98,
        'consistency': 0.97,
        'timeliness': 1.0,
    }

    print(f"数据质量: 完整性 {result['completeness']:.2f}, 准确性 {result['accuracy']:.2f}")
    return result


def execute_factor_calculation():
    """步骤 3: 因子计算"""
    print("执行因子计算...")

    # 这里应该调用实际的因子计算逻辑
    # 简化实现：
    result = {
        'success_count': 18,
        'total_count': 20,
        'failed_factors': ['F00015', 'F00019'],
        'calculation_time': 120.5,
    }

    print(f"因子计算: {result['success_count']}/{result['total_count']} 成功")
    return result


def execute_factor_validation():
    """步骤 4: 因子验证"""
    print("执行因子验证...")

    # 这里应该调用实际的因子验证逻辑
    # 简化实现：
    result = {
        'ic_mean': 0.035,
        'ic_std': 0.12,
        'ir': 0.29,
        'rank_ic': 0.042,
    }

    print(f"因子验证: IC={result['ic_mean']:.3f}, IR={result['ir']:.2f}")
    return result


def execute_alpha_generation():
    """步骤 5: Alpha 生成"""
    print("执行 Alpha 生成...")

    # 这里应该调用实际的 Alpha 生成逻辑
    # 简化实现：
    result = {
        'signal_count': 100,
        'long_signals': 30,
        'short_signals': 20,
        'neutral_signals': 50,
        'avg_signal_strength': 0.65,
    }

    print(f"Alpha 生成: {result['signal_count']} 个信号")
    return result


def execute_strategy_execution():
    """步骤 6: 策略执行"""
    print("执行策略执行...")

    # 这里应该调用实际的策略执行逻辑
    # 简化实现：
    result = {
        'selected_stocks': 20,
        'long_positions': 15,
        'short_positions': 5,
        'total_weight': 1.0,
    }

    print(f"策略执行: 选中 {result['selected_stocks']} 只股票")
    return result


def execute_portfolio_optimization():
    """步骤 7: 组合优化"""
    print("执行组合优化...")

    # 这里应该调用实际的组合优化逻辑
    # 简化实现：
    result = {
        'optimized': True,
        'method': 'risk_parity',
        'expected_return': 0.15,
        'expected_risk': 0.12,
    }

    print(f"组合优化: {result['method']}, 预期收益 {result['expected_return']:.2%}")
    return result


def execute_risk_check():
    """步骤 8: 风控检查"""
    print("执行风控检查...")

    # 这里应该调用实际的风控检查逻辑
    # 简化实现：
    result = {
        'max_drawdown': 0.08,
        'concentration': 0.25,
        'leverage': 1.0,
        'risk_exposure': 0.75,
    }

    print(f"风控检查: 最大回撤 {result['max_drawdown']:.2%}")
    return result


def execute_trading_execution():
    """步骤 9: 交易执行"""
    print("执行交易执行...")

    # 这里应该调用实际的交易执行逻辑
    # 简化实现：
    result = {
        'orders_created': 20,
        'orders_executed': 18,
        'orders_failed': 2,
        'total_value': 500000.0,
    }

    print(f"交易执行: {result['orders_executed']}/{result['orders_created']} 订单执行")
    return result


def execute_report_generation():
    """步骤 10: 报告生成"""
    print("执行报告生成...")

    # 这里应该调用实际的报告生成逻辑
    # 简化实现：
    result = {
        'report_id': f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        'report_type': 'daily',
        'sections': ['summary', 'performance', 'risk', 'positions'],
    }

    print(f"报告生成: {result['report_id']}")
    return result


def execute_monitor_push():
    """步骤 11: 监控推送"""
    print("执行监控推送...")

    # 这里应该调用实际的监控推送逻辑
    # 简化实现：
    result = {
        'pushed': True,
        'channels': ['feishu'],
        'recipients': 5,
        'push_time': datetime.now().isoformat(),
    }

    print(f"监控推送: 推送到 {result['channels']}")
    return result


# ============================================================================
# 步骤检查函数示例
# ============================================================================

def check_data_update(data: dict) -> dict:
    """检查数据更新质量"""
    updated_count = data.get('updated_stocks', 0)
    total_count = data.get('total_stocks', 0)

    score = updated_count / total_count if total_count > 0 else 0.0

    return {
        'score': score,
        'details': {
            'updated_count': updated_count,
            'total_count': total_count,
            'success_rate': score,
        },
    }


def check_factor_calculation(data: dict) -> dict:
    """检查因子计算质量"""
    success_count = data.get('success_count', 0)
    total_count = data.get('total_count', 0)

    score = success_count / total_count if total_count > 0 else 0.0

    return {
        'score': score,
        'details': {
            'success_count': success_count,
            'total_count': total_count,
            'success_rate': score,
            'failed_factors': data.get('failed_factors', []),
        },
    }


def check_backtest(data: dict) -> dict:
    """检查回测质量"""
    sharpe_ratio = data.get('sharpe_ratio', 0.0)
    max_drawdown = data.get('max_drawdown', 1.0)

    # Sharpe Ratio > 1 且 最大回撤 < 20%
    score = min(1.0, max(0.0, (sharpe_ratio / 2.0) * (1.0 - max_drawdown)))

    return {
        'score': score,
        'details': {
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
        },
    }


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    print("\n" + "="*60)
    print("WildQuest Matrix 智能管线示例")
    print("="*60 + "\n")

    # 创建智能管线
    pipeline_id = f"daily_pipeline_{datetime.now().strftime('%Y%m%d')}"
    pipeline = create_intelligent_pipeline(
        pipeline_id=pipeline_id,
        config={
            'enable_llm_review': True,
            'auto_resume': True,
        }
    )

    # 注册步骤执行函数
    pipeline.register_step_executor(0, execute_position_check)
    pipeline.register_step_executor(1, execute_data_update)
    pipeline.register_step_executor(2, execute_data_quality_check)
    pipeline.register_step_executor(3, execute_factor_calculation)
    pipeline.register_step_executor(4, execute_factor_validation)
    pipeline.register_step_executor(5, execute_alpha_generation)
    pipeline.register_step_executor(6, execute_strategy_execution)
    pipeline.register_step_executor(7, execute_portfolio_optimization)
    pipeline.register_step_executor(8, execute_risk_check)
    pipeline.register_step_executor(9, execute_trading_execution)
    pipeline.register_step_executor(10, execute_report_generation)
    pipeline.register_step_executor(11, execute_monitor_push)

    # 注册步骤检查函数
    pipeline.register_step_checker(1, check_data_update)
    pipeline.register_step_checker(3, check_factor_calculation)
    # pipeline.register_step_checker(6, check_backtest)  # 如果有回测步骤

    # 执行管线
    result = pipeline.execute(mode="standard")

    # 打印结果
    print("\n" + "="*60)
    print("执行结果")
    print("="*60)
    print(f"管线 ID: {pipeline_id}")
    print(f"状态: {result.get('status', 'unknown')}")
    print(f"完成步骤: {result['summary']['passed_gates']}/{result['summary']['total_gates']}")
    print(f"失败步骤: {result['summary']['failed_gates']}")
    print(f"警告步骤: {result['summary']['warning_gates']}")
    print(f"需要审查: {result['summary']['review_required_gates']}")
    print("="*60 + "\n")

    # 获取状态
    status = pipeline.get_status()
    print("管线状态:")
    print(f"  当前步骤: {status['current_step']}")
    print(f"  完成步骤: {status['completed_steps']}")
    print(f"  失败步骤: {status['failed_steps']}")
    print(f"  开始时间: {status['start_time']}")
    print(f"  结束时间: {status['end_time']}")
    print()

    # 获取报告
    report = pipeline.get_report()
    print("质量报告:")
    for gate_name, gate_result in report.get('gates', {}).items():
        print(f"  {gate_name}: {gate_result['status']} (分数: {gate_result['score']:.2f})")
    print()


if __name__ == "__main__":
    main()
