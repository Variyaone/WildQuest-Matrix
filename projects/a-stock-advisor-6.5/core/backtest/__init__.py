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
- 未来函数检测：防止look-ahead bias
- 交易日历：A股交易日判断
- 多频率支持：日/小时/分钟级回测
- 鲁棒性验证：存续偏差、滚动回测、流动性约束、事件模拟等
"""

from .engine import BacktestEngine, BacktestConfig, BacktestResult
from .matcher import OrderMatcher, Order, OrderType, OrderStatus, MatchResult
from .analyzer import PerformanceAnalyzer, PerformanceMetrics
from .reporter import BacktestReporter, ReportConfig
from .benchmark import BenchmarkManager, Benchmark
from .slippage import SlippageModel, SlippageType
from .cost import CostModel, CostType, TransactionCost
from .lookahead_guard import (
    LookAheadGuard,
    LookAheadBiasError,
    DataAccessor,
    LookAheadValidator,
    DataAccessType,
    DataAccessRecord,
    LookAheadViolation
)
from .trading_calendar import (
    TradingCalendar,
    TradingCalendarManager,
    MarketType,
    TradingSession,
    get_trading_calendar,
    is_trading_day,
    get_next_trading_day,
    get_trading_days
)
from .frequency import (
    BarFrequency,
    FrequencyConfig,
    DataResampler,
    MultiFrequencyBacktestEngine,
    FrequencyAwareBacktestConfig,
    detect_data_frequency
)
from .stock_pool_snapshot import (
    StockPoolSnapshotManager,
    StockPoolSnapshot,
    create_snapshot_manager
)
from .walk_forward import (
    WalkForwardBacktester,
    WalkForwardMode,
    WalkForwardWindow,
    WalkForwardResult,
    WalkForwardSummary,
    create_walk_forward_backtester
)
from .liquidity_checker import (
    LiquidityConstraintChecker,
    LiquidityMetrics,
    LiquidityCheckResult,
    create_liquidity_checker
)
from .event_simulator import (
    BlackSwanEventSimulator,
    MarketEvent,
    EventEffect,
    EventType,
    create_event_simulator
)
from .enhanced_impact import (
    EnhancedMarketImpactModel,
    MarketImpactParams,
    create_enhanced_impact_model
)
from .market_regime import (
    MarketAwareBacktester,
    MarketRegimeClassifier,
    MarketRegime,
    MarketPeriod,
    create_market_aware_backtester
)
from .constraints import (
    TurnoverConstraintChecker,
    OverfittingDetector,
    TurnoverMetrics,
    TurnoverCheckResult,
    OverfittingCheckResult,
    create_turnover_checker,
    create_overfitting_detector
)
from .robust_framework import (
    RobustBacktestFramework,
    RobustBacktestConfig,
    RobustBacktestResult,
    create_robust_framework
)

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
    'LookAheadGuard',
    'LookAheadBiasError',
    'DataAccessor',
    'LookAheadValidator',
    'DataAccessType',
    'DataAccessRecord',
    'LookAheadViolation',
    'TradingCalendar',
    'TradingCalendarManager',
    'MarketType',
    'TradingSession',
    'get_trading_calendar',
    'is_trading_day',
    'get_next_trading_day',
    'get_trading_days',
    'BarFrequency',
    'FrequencyConfig',
    'DataResampler',
    'MultiFrequencyBacktestEngine',
    'FrequencyAwareBacktestConfig',
    'detect_data_frequency',
    'StockPoolSnapshotManager',
    'StockPoolSnapshot',
    'create_snapshot_manager',
    'WalkForwardBacktester',
    'WalkForwardMode',
    'WalkForwardWindow',
    'WalkForwardResult',
    'WalkForwardSummary',
    'create_walk_forward_backtester',
    'LiquidityConstraintChecker',
    'LiquidityMetrics',
    'LiquidityCheckResult',
    'create_liquidity_checker',
    'BlackSwanEventSimulator',
    'MarketEvent',
    'EventEffect',
    'EventType',
    'create_event_simulator',
    'EnhancedMarketImpactModel',
    'MarketImpactParams',
    'create_enhanced_impact_model',
    'MarketAwareBacktester',
    'MarketRegimeClassifier',
    'MarketRegime',
    'MarketPeriod',
    'create_market_aware_backtester',
    'TurnoverConstraintChecker',
    'OverfittingDetector',
    'TurnoverMetrics',
    'TurnoverCheckResult',
    'OverfittingCheckResult',
    'create_turnover_checker',
    'create_overfitting_detector',
    'RobustBacktestFramework',
    'RobustBacktestConfig',
    'RobustBacktestResult',
    'create_robust_framework',
]
