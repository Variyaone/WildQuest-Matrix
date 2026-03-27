"""
前置检查系统测试

测试验证模块的功能。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, timedelta

from core.validation import PreCheckManager, TrustManager, CheckReporter
from core.validation.contracts import TrustLevel, RequirementType
from core.validation.freshness import FreshnessPolicy, ExecutionMode


def test_data_layer_check():
    """测试数据层检查"""
    print("\n" + "="*70)
    print("测试数据层检查")
    print("="*70)
    
    from core.validation.checkers import DataLayerChecker
    
    checker = DataLayerChecker()
    
    # 测试正常数据
    normal_data = pd.DataFrame({
        'stock_code': ['000001.SZ', '000001.SZ', '000002.SZ', '000002.SZ'],
        'date': ['2026-03-25', '2026-03-26', '2026-03-25', '2026-03-26'],
        'open': [10.0, 10.5, 20.0, 20.5],
        'high': [10.8, 11.0, 20.8, 21.0],
        'low': [9.8, 10.2, 19.8, 20.2],
        'close': [10.5, 10.8, 20.5, 20.8],
        'volume': [1000000, 1200000, 800000, 900000]
    })
    
    result = checker.check(normal_data)
    print(f"\n正常数据检查结果:")
    print(f"  可信度: {result.trust_level.value}")
    print(f"  质量分数: {result.score:.1f}")
    print(f"  通过: {result.passed}")
    
    # 测试空数据
    empty_result = checker.check(pd.DataFrame())
    print(f"\n空数据检查结果:")
    print(f"  可信度: {empty_result.trust_level.value}")
    print(f"  质量分数: {empty_result.score:.1f}")
    print(f"  通过: {empty_result.passed}")
    
    assert result.passed, "正常数据应该通过检查"
    assert not empty_result.passed, "空数据不应该通过检查"
    print("\n✓ 数据层检查测试通过")


def test_freshness_policy():
    """测试新鲜度策略"""
    print("\n" + "="*70)
    print("测试新鲜度策略")
    print("="*70)
    
    policy = FreshnessPolicy(ExecutionMode.LIVE_TRADING)
    
    # 测试新鲜数据
    fresh_time = datetime.now() - timedelta(hours=2)
    result = policy.check_freshness('data', 'market_data', fresh_time)
    print(f"\n2小时前的数据:")
    print(f"  状态: {result.status.value}")
    print(f"  消息: {result.message}")
    
    # 测试过期数据
    stale_time = datetime.now() - timedelta(days=3)
    result = policy.check_freshness('data', 'market_data', stale_time)
    print(f"\n3天前的数据:")
    print(f"  状态: {result.status.value}")
    print(f"  消息: {result.message}")
    
    print("\n✓ 新鲜度策略测试通过")


def test_pre_check_manager():
    """测试前置检查管理器"""
    print("\n" + "="*70)
    print("测试前置检查管理器")
    print("="*70)
    
    manager = PreCheckManager(mode=ExecutionMode.LIVE_TRADING)
    
    # 测试数据层
    market_data = pd.DataFrame({
        'stock_code': ['000001.SZ', '000002.SZ'],
        'date': ['2026-03-26', '2026-03-26'],
        'open': [10.0, 20.0],
        'high': [10.8, 20.8],
        'low': [9.8, 19.8],
        'close': [10.5, 20.5],
        'volume': [1000000, 800000]
    })
    
    result = manager.check_layer('data', market_data)
    print(f"\n数据层检查结果:")
    print(f"  可信度: {result.trust_level.value}")
    print(f"  质量分数: {result.score:.1f}")
    
    # 测试组合优化层
    weights = {
        '000001.SZ': 0.5,
        '000002.SZ': 0.5
    }
    
    result = manager.check_layer('portfolio', weights)
    print(f"\n组合优化层检查结果:")
    print(f"  可信度: {result.trust_level.value}")
    print(f"  质量分数: {result.score:.1f}")
    
    # 生成报告
    print("\n" + "-"*70)
    print("检查报告:")
    print("-"*70)
    report = manager.generate_report()
    print(report)
    
    print("\n✓ 前置检查管理器测试通过")


def test_trust_manager():
    """测试可信度管理器"""
    print("\n" + "="*70)
    print("测试可信度管理器")
    print("="*70)
    
    manager = TrustManager()
    
    # 创建模拟结果
    from core.validation.contracts import LayerCheckResult, CheckResult
    
    # 通过的结果
    passed_result = LayerCheckResult(
        layer_name='data',
        layer_step=1,
        results=[
            CheckResult('H1', '数据非空', RequirementType.HARD, True, 100, '>0', '通过'),
        ],
        trust_level=TrustLevel.TRUSTED,
        score=100.0,
        timestamp=datetime.now().isoformat()
    )
    
    manager.update_layer_result(passed_result)
    print(f"\n添加通过结果后:")
    print(f"  整体可信度: {manager.current_trust_level.value}")
    print(f"  可以继续: {manager.can_proceed()}")
    
    # 失败的结果
    failed_result = LayerCheckResult(
        layer_name='factor',
        layer_step=2,
        results=[
            CheckResult('H1', '因子非空', RequirementType.HARD, False, 0, '>0', '失败'),
        ],
        trust_level=TrustLevel.UNTRUSTED,
        score=0.0,
        timestamp=datetime.now().isoformat()
    )
    
    manager.update_layer_result(failed_result)
    print(f"\n添加失败结果后:")
    print(f"  整体可信度: {manager.current_trust_level.value}")
    print(f"  可以继续: {manager.can_proceed()}")
    print(f"  失败层: {manager.get_failed_layer()}")
    
    assert not manager.can_proceed(), "有硬性失败时不应可以继续"
    print("\n✓ 可信度管理器测试通过")


def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("前置检查系统测试套件")
    print("="*70)
    
    try:
        test_data_layer_check()
        test_freshness_policy()
        test_pre_check_manager()
        test_trust_manager()
        
        print("\n" + "="*70)
        print("所有测试通过！")
        print("="*70)
        return 0
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
