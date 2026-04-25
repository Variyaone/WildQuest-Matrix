#!/usr/bin/env python3
"""
阶段13全面验证脚本
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def test_data_quality():
    """测试数据质量验证 (H1-H5)"""
    print('='*70)
    print('数据质量验证测试 (H1-H5)')
    print('='*70)
    
    from core.validation.checkers import DataLayerChecker
    
    checker = DataLayerChecker()
    
    # 创建测试数据
    np.random.seed(42)
    dates = pd.date_range('2026-01-01', periods=30, freq='B')
    stocks = ['000001.SZ', '000002.SZ', '600000.SH']
    
    data = []
    for stock in stocks:
        for date in dates:
            base_price = np.random.uniform(10, 50)
            open_price = base_price * (1 + np.random.uniform(-0.02, 0.02))
            close_price = base_price * (1 + np.random.uniform(-0.02, 0.02))
            high_price = max(open_price, close_price) * (1 + np.random.uniform(0, 0.02))
            low_price = min(open_price, close_price) * (1 - np.random.uniform(0, 0.02))
            volume = np.random.randint(1000000, 10000000)
            data.append({
                'stock_code': stock,
                'date': date.strftime('%Y-%m-%d'),
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
    
    df = pd.DataFrame(data)
    print(f'测试数据: {len(df)} 行, {len(stocks)} 只股票')
    
    # 运行检查
    result = checker.check(df)
    
    print(f'\n检查结果:')
    print(f'  可信度: {result.trust_level.value}')
    print(f'  质量分数: {result.score:.1f}')
    print(f'  通过: {result.passed}')
    
    print(f'\n详细检查项:')
    for check in result.results:
        status = '✓' if check.passed else '✗'
        print(f'  {status} {check.requirement_id}: {check.requirement_name} - {check.message}')
    
    return result.passed


def test_empty_data():
    """测试空数据"""
    print('\n' + '='*70)
    print('测试空数据 (应该失败)')
    print('='*70)
    
    from core.validation.checkers import DataLayerChecker
    checker = DataLayerChecker()
    
    empty_result = checker.check(pd.DataFrame())
    print(f'通过: {empty_result.passed}')
    print(f'可信度: {empty_result.trust_level.value}')
    
    return not empty_result.passed


def test_price_logic_error():
    """测试价格逻辑错误"""
    print('\n' + '='*70)
    print('测试价格逻辑错误 (H4)')
    print('='*70)
    
    from core.validation.checkers import DataLayerChecker
    checker = DataLayerChecker()
    
    # 创建有问题的数据
    df = pd.DataFrame({
        'stock_code': ['000001.SZ'] * 5,
        'date': pd.date_range('2026-01-01', periods=5, freq='B').strftime('%Y-%m-%d'),
        'open': [10.0, 10.5, 10.3, 10.8, 10.6],
        'high': [10.8, 11.0, 10.9, 11.2, 11.0],
        'low': [9.8, 10.2, 10.0, 10.5, 10.3],
        'close': [10.5, 10.8, 10.6, 11.0, 10.9],
        'volume': [1000000] * 5
    })
    
    # 制造价格逻辑错误
    df.loc[0, 'high'] = df.loc[0, 'low'] - 1
    
    bad_result = checker.check(df)
    print(f'通过: {bad_result.passed}')
    
    for check in bad_result.results:
        if check.requirement_id == 'H4':
            print(f'  H4 检查: {check.passed} - {check.message}')
            return not check.passed
    
    return False


def test_data_contract():
    """测试数据契约验证"""
    print('\n' + '='*70)
    print('数据契约验证测试')
    print('='*70)
    
    from core.validation.contracts import DataLayerContract
    
    contract = DataLayerContract()
    
    print(f'必需字段: {contract.REQUIRED_FIELDS}')
    print(f'硬性要求: {len(contract.HARD_REQUIREMENTS)} 项')
    print(f'弹性要求: {len(contract.ELASTIC_REQUIREMENTS)} 项')
    
    return True


def test_factor_checker():
    """测试因子检查器"""
    print('\n' + '='*70)
    print('因子检查器测试')
    print('='*70)
    
    from core.validation.checkers import FactorLayerChecker
    
    checker = FactorLayerChecker()
    
    # 创建测试因子数据
    factor_df = pd.DataFrame({
        'stock_code': ['000001.SZ', '000002.SZ', '600000.SH'] * 10,
        'date': pd.date_range('2026-01-01', periods=10, freq='B').repeat(3),
        'factor_1': np.random.randn(30),
        'factor_2': np.random.randn(30),
    })
    
    result = checker.check(factor_df)
    print(f'因子检查通过: {result.passed}')
    print(f'可信度: {result.trust_level.value}')
    
    return True


def test_portfolio_checker():
    """测试组合检查器"""
    print('\n' + '='*70)
    print('组合检查器测试')
    print('='*70)
    
    from core.validation.checkers import PortfolioLayerChecker
    
    checker = PortfolioLayerChecker()
    
    # 创建测试组合数据 (字典格式)
    portfolio_data = {
        '000001.SZ': 0.25,
        '000002.SZ': 0.25,
        '600000.SH': 0.25,
        '600519.SH': 0.25
    }
    
    result = checker.check(portfolio_data)
    print(f'组合检查通过: {result.passed}')
    print(f'可信度: {result.trust_level.value}')
    
    return True


def test_pre_check_manager():
    """测试前置检查管理器"""
    print('\n' + '='*70)
    print('前置检查管理器测试')
    print('='*70)
    
    from core.validation import PreCheckManager
    from core.validation.freshness import ExecutionMode
    
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
    print(f'数据层检查通过: {result.passed}')
    print(f'可信度: {result.trust_level.value}')
    
    return True


def main():
    """运行所有验证测试"""
    print('\n' + '#'*70)
    print('# 阶段13：全面验证')
    print('#'*70)
    
    tests = [
        ('数据质量验证 (H1-H5)', test_data_quality),
        ('空数据测试', test_empty_data),
        ('价格逻辑错误测试', test_price_logic_error),
        ('数据契约验证', test_data_contract),
        ('因子检查器', test_factor_checker),
        ('组合检查器', test_portfolio_checker),
        ('前置检查管理器', test_pre_check_manager),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed, None))
        except Exception as e:
            results.append((name, False, str(e)))
    
    # 打印总结
    print('\n' + '='*70)
    print('验证总结')
    print('='*70)
    
    passed_count = 0
    for name, passed, error in results:
        status = '✓ 通过' if passed else '✗ 失败'
        print(f'  {status}: {name}')
        if error:
            print(f'    错误: {error}')
        if passed:
            passed_count += 1
    
    print(f'\n总计: {passed_count}/{len(results)} 测试通过')
    
    return passed_count == len(results)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
