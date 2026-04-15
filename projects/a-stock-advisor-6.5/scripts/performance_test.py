#!/usr/bin/env python3
"""
性能测试脚本 - 阶段13
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import numpy as np
import pandas as pd


def test_data_cleaner_performance():
    """测试数据清洗器性能"""
    from core.data.cleaner import DataCleaner
    
    cleaner = DataCleaner()
    
    # 创建大规模测试数据
    n_rows = 10000
    np.random.seed(42)
    
    data = []
    for i in range(n_rows):
        data.append({
            'stock_code': f'00000{i:04d}.SZ',
            'date': f'2026-01-{(i // 400) + 1:02d}',
            'open': np.random.uniform(10, 50),
            'high': np.random.uniform(10, 50),
            'low': np.random.uniform(10, 50),
            'close': np.random.uniform(10, 50),
            'volume': np.random.randint(1000000, 10000000)
        })
    
    df = pd.DataFrame(data)
    
    start = time.time()
    result = cleaner.clean(df)
    elapsed = time.time() - start
    
    print(f'数据清洗器性能测试:')
    print(f'  数据行数: {n_rows}')
    print(f'  处理时间: {elapsed:.3f}s')
    print(f'  每行处理时间: {elapsed/n_rows*1000:.3f}ms')
    
    return elapsed < 10


def test_factor_registry_performance():
    """测试因子注册表性能"""
    from core.factor.registry import FactorRegistry
    
    registry = FactorRegistry()
    
    # 注册100个因子
    start = time.time()
    for i in range(100):
        registry.register(
            factor_id=f'F{i:04d}',
            name=f'factor_{i}',
            formula=f'close / close.shift(5)',
            category='momentum'
        )
    elapsed = time.time() - start
    
    print(f'因子注册表性能测试:')
    print(f'  注册因子数: 100')
    print(f'  注册时间: {elapsed:.3f}s')
    
    return elapsed < 5


def test_signal_generator_performance():
    """测试信号生成器性能"""
    from core.signal.generator import SignalGenerator
    
    generator = SignalGenerator()
    
    # 创建测试数据
    n_stocks = 100
    n_dates = 50
    
    factor_data = pd.DataFrame({
        'stock_code': np.repeat([f'00000{i:04d}.SZ' for i in range(n_stocks)], n_dates),
        'date': np.tile(pd.date_range('2026-01-01', periods=n_dates, freq='B'), n_stocks),
        'momentum_5': np.random.randn(n_stocks * n_dates),
        'volume_ratio': np.random.randn(n_stocks * n_dates)
    })
    
    start = time.time()
    signals = generator.generate(factor_data)
    elapsed = time.time() - start
    
    print(f'信号生成器性能测试:')
    print(f'  股票数: {n_stocks}')
    print(f'  日期数: {n_dates}')
    print(f'  生成时间: {elapsed:.3f}s')
    
    return elapsed < 10


def test_portfolio_optimizer_performance():
    """测试组合优化器性能"""
    from core.portfolio.optimizer import PortfolioOptimizer
    
    optimizer = PortfolioOptimizer()
    
    # 创建测试数据
    n_stocks = 50
    stock_codes = [f'00000{i:04d}.SZ' for i in range(n_stocks)]
    
    start = time.time()
    result = optimizer.optimize(stock_codes, method='equal_weight')
    elapsed = time.time() - start
    
    print(f'组合优化器性能测试:')
    print(f'  股票数: {n_stocks}')
    print(f'  优化时间: {elapsed:.3f}s')
    
    return elapsed < 5


def test_risk_metrics_performance():
    """测试风控指标性能"""
    from core.risk.metrics import RiskMetrics
    
    metrics = RiskMetrics()
    
    # 创建测试数据
    n_points = 1000
    returns = np.random.randn(n_points) * 0.02
    
    start = time.time()
    var = metrics.calculate_var(returns, confidence_level=0.95)
    elapsed = time.time() - start
    
    print(f'风控指标性能测试:')
    print(f'  数据点数: {n_points}')
    print(f'  VaR计算时间: {elapsed:.3f}s')
    
    return elapsed < 5


def test_backtest_engine_performance():
    """测试回测引擎性能"""
    from core.backtest.engine import BacktestEngine
    
    engine = BacktestEngine()
    
    # 创建测试数据
    n_days = 100
    n_stocks = 10
    
    signals = pd.DataFrame({
        'date': np.tile(pd.date_range('2026-01-01', periods=n_days, freq='B'), n_stocks),
        'stock_code': np.repeat([f'00000{i:04d}.SZ' for i in range(n_stocks)], n_days),
        'signal': np.random.choice([1, 0, -1], n_days * n_stocks)
    })
    
    prices = pd.DataFrame({
        'date': np.tile(pd.date_range('2026-01-01', periods=n_days, freq='B'), n_stocks),
        'stock_code': np.repeat([f'00000{i:04d}.SZ' for i in range(n_stocks)], n_days),
        'close': np.random.uniform(10, 50, n_days * n_stocks)
    })
    
    start = time.time()
    result = engine.run(signals, prices)
    elapsed = time.time() - start
    
    print(f'回测引擎性能测试:')
    print(f'  交易日数: {n_days}')
    print(f'  股票数: {n_stocks}')
    print(f'  回测时间: {elapsed:.3f}s')
    
    return elapsed < 30


def main():
    """运行所有性能测试"""
    print('\n' + '='*70)
    print('阶段13：性能测试')
    print('='*70 + '\n')
    
    tests = [
        ('数据清洗器', test_data_cleaner_performance),
        ('因子注册表', test_factor_registry_performance),
        ('信号生成器', test_signal_generator_performance),
        ('组合优化器', test_portfolio_optimizer_performance),
        ('风控指标', test_risk_metrics_performance),
        ('回测引擎', test_backtest_engine_performance),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            elapsed = test_func()
            results.append((name, elapsed, True))
        except Exception as e:
            results.append((name, 0, False))
            print(f'  错误: {e}')
    
    # 打印总结
    print('\n' + '='*70)
    print('性能测试总结')
    print('='*70)
    
    passed_count = 0
    total_time = 0
    for name, elapsed, passed in results:
        status = '✓ 通过' if passed else '✗ 失败'
        print(f'  {status}: {name} - {elapsed:.3f}s')
        if passed:
            passed_count += 1
            total_time += elapsed
    
    print(f'\n总计: {passed_count}/{len(tests)} 测试通过')
    print(f'总耗时: {total_time:.3f}s')


if __name__ == '__main__':
    main()
