"""
OKX Trading - 回测模块

提供完善的回测引擎，包含：
- 订单簿深度模拟
- 滑点计算
- 市场冲击模拟
- 手续费计算
- 完整的性能指标输出
"""

from .backtest_engine import (
    # 数据类型
    OrderType,
    OrderSide,
    OrderStatus,
    Order,
    Trade,
    Position,
    BacktestMetrics,
    BacktestResult,

    # 核心类
    MarketEnvironment,
    OrderExecutor,
    BaseStrategy,
    BacktestEngine,

    # 辅助函数
    print_backtest_summary,
    create_sample_strategy,
)

__all__ = [
    # 数据类型
    'OrderType',
    'OrderSide',
    'OrderStatus',
    'Order',
    'Trade',
    'Position',
    'BacktestMetrics',
    'BacktestResult',

    # 核心类
    'MarketEnvironment',
    'OrderExecutor',
    'BaseStrategy',
    'BacktestEngine',

    # 辅助函数
    'print_backtest_summary',
    'create_sample_strategy',
]

__version__ = '1.0.0'
