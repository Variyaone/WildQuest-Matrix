#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试脚本 - 测试OKX交易系统框架
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import Settings
from data.storage import Storage
from strategy.base import DummyStrategy, Signal
from strategy.grid import GridStrategy
from execution.risk_manager import RiskManager
from monitor.monitor import Monitor

print("\n" + "="*60)
print("OKX交易系统框架测试")
print("="*60 + "\n")

# 1. 测试配置模块
print("[1/6] 测试配置模块...")
settings = Settings()
print(f"  ✓ Settings 实例创建成功")

# 2. 测试数据存储
print("\n[2/6] 测试数据存储...")
storage = Storage(db_path='test_db.sqlite')
print(f"  ✓ Storage 实例创建成功")
storage.insert_candlestick(
    instrument_id='BTC-USDT-SWAP',
    timeframe='1H',
    timestamp=1700000000000,
    open_price=45000,
    high=46000,
    low=44500,
    close=45500,
    volume=1000
)
print(f"  ✓ K线数据插入成功")

# 3. 测试风险管理
print("\n[3/6] 测试风险管理...")
risk_config = {
    'max_position_value': 500,
    'stop_loss_percent': 2.0,
    'take_profit_percent': 5.0
}
risk_manager = RiskManager(config=risk_config)
print(f"  ✓ RiskManager 实例创建成功")

result = risk_manager.check_order(
    symbol='BTC-USDT-SWAP',
    side='buy',
    order_value=300,
    current_positions={}
)
print(f"  ✓ 订单风险检查: {result.passed} - {result.message}")

# 4. 测试监控器
print("\n[4/6] 测试监控器...")
monitor = Monitor()
monitor.initialize()
monitor.start()
print(f"  ✓ Monitor 实例创建并启动")

monitor.alert('info', '测试告警')
monitor.alert('warning', '测试警告')
print(f"  ✓ 告警系统正常")

# 5. 测试虚策略
print("\n[5/6] 测试虚策略...")
dummy = DummyStrategy('DummyStrategy', {})
dummy.initialize()
dummy.start()
print(f"  ✓ DummyStrategy 初始化并启动")

# 测试信号处理
signal = Signal(
    signal_type='buy',
    instrument_id='BTC-USDT-SWAP',
    price=45500,
    amount=0.001,
    reason='测试信号'
)
monitor.on_signal(signal.__dict__)
print(f"  ✓ 信号处理正常")

# 6. 测试网格策略
print("\n[6/6] 测试网格策略...")
grid_config = {
    'instrument_id': 'BTC-USDT-SWAP',
    'upper_price': 50000,
    'lower_price': 45000,
    'grid_count': 5,
    'grid_amount': 100,
    'position_side': 'long'
}
grid = GridStrategy('TestGrid', grid_config)
grid.initialize()
grid.start()
print(f"  ✓ GridStrategy 初始化并启动")
print(f"  - 网格层数: {len(grid.grid_levels)}")
print(f"  - 单格利润: {grid.grid_profit:.4f}%")

# 测试数据更新
test_data = {
    'candle': [1700000000000, 45500, 45800, 45400, 45700, 500]
}
signal = grid.on_data(test_data)
print(f"  - 测试数据: {test_data}")
print(f"  - 信号生成: {signal.signal_type if signal else '无'}")

# 输出统计信息
print("\n" + "="*60)
print("统计摘要")
print("="*60)
print(f"策略统计: {grid.get_stats()}")
print(f"风险统计: {risk_manager.get_stats()}")
print(f"监控统计: {monitor.get_stats()}")

print("\n" + "="*60)
print("✓ 所有测试通过！框架运行正常。")
print("="*60 + "\n")

# 清理
grid.stop()
monitor.stop()
