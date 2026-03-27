"""
回测系统模块

提供完整的回测功能，包括：
- 回测引擎：事件驱动和向量化回测
- 订单撮合器：模拟真实市场成交
- 绩效分析器：计算回测绩效指标
- 回测报告生成器：生成可视化报告
- 基准管理：管理基准数据
- 滑点模型：模拟交易滑点
- 交易成本模型：计算交易成本
"""

from .engine import BacktestEngine, BacktestConfig, BacktestResult
from .matcher import OrderMatcher, Order, OrderType, OrderStatus, MatchResult
from .analyzer import PerformanceAnalyzer, PerformanceMetrics
from .reporter import BacktestReporter, ReportConfig
from .benchmark import BenchmarkManager, Benchmark
from .slippage import SlippageModel, SlippageType
from .cost import CostModel, CostType, TransactionCost

__all__ = [
    'BacktestEngine',
    'BacktestConfig',
    'BacktestResult',
    'OrderMatcher',
    'Order',
    'OrderType',
    'OrderStatus',
    'MatchResult',
    'PerformanceAnalyzer',
    'PerformanceMetrics',
    'BacktestReporter',
    'ReportConfig',
    'BenchmarkManager',
    'Benchmark',
    'SlippageModel',
    'SlippageType',
    'CostModel',
    'CostType',
    'TransactionCost',
]
