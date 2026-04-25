"""
回测引擎模块
提供完善的交易策略回测功能
包含滑点模拟、市场冲击、订单簿深度检查等
"""

from .backtest_engine import BacktestEngine

__all__ = ['BacktestEngine']
