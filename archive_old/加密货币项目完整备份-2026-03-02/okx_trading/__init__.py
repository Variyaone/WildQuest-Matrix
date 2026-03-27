"""
OKX Trading System
核心交易系统框架

包含完整的数据采集、策略执行、风险管理和回测引擎
"""

__version__ = "1.0.0"
__author__ = "Creator"

# 核心模块
from .data.collector import DataCollector, MarketData
from .data.storage import Storage
from .strategy.base import BaseStrategy, Signal, Position
from .strategy.grid import GridStrategy
from .execution.risk_manager import RiskManager, RiskLevel, RiskCheckResult
from .backtest import BacktestEngine
try:
    from .backtest import BacktestResult
except ImportError:
    # BacktestResult 可能未导出
    BacktestResult = None

# 异常处理
from .exceptions import (
    TradingException,
    APIException,
    WebSocketException,
    DataQualityException,
    OrderException,
    RiskException,
    ConfigException,
    handle_exceptions,
    retry_on_exception
)

__all__ = [
    # 数据模块
    'DataCollector',
    'MarketData',
    'Storage',

    # 策略模块
    'BaseStrategy',
    'Signal',
    'Position',
    'GridStrategy',

    # 风险管理
    'RiskManager',
    'RiskLevel',
    'RiskCheckResult',

    # 回测引擎
    'BacktestEngine',
    'BacktestResult',

    # 异常处理
    'TradingException',
    'APIException',
    'WebSocketException',
    'DataQualityException',
    'OrderException',
    'RiskException',
    'ConfigException',
    'handle_exceptions',
    'retry_on_exception',
]
