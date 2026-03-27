"""
A股量化投顾系统 - 核心模块

包含：
- data: 数据管理模块
- infrastructure: 基础设施模块
- validation: 验证模块
- factor: 因子库管理系统
- signal: 信号库管理系统
- strategy: 策略库管理系统
"""

__version__ = "6.5.0"
__author__ = "Quant Team"

from .data import (
    ParquetStorage,
    DataStorage,
    get_data_storage,
    reset_data_storage
)

from .infrastructure import (
    get_config_manager,
    get_config,
    get_data_paths,
    AppException,
    FactorException,
    SignalException,
    StrategyException
)

from .validation import (
    PreCheckManager,
    get_pre_check_manager,
    TrustManager,
    get_trust_manager,
    CheckResult,
    TrustLevel
)

from .factor import (
    FactorCategory,
    FactorSubCategory,
    FactorClassification,
    get_factor_classification,
    FactorRegistry,
    get_factor_registry,
    FactorEngine,
    get_factor_engine,
    FactorValidator,
    get_factor_validator,
    FactorBacktester,
    get_factor_backtester,
    FactorScorer,
    get_factor_scorer,
    FactorStorage,
    get_factor_storage,
    FactorMiner,
    get_factor_miner,
    FactorMonitor,
    get_factor_monitor
)

from .signal import (
    SignalType,
    SignalDirection,
    SignalRegistry,
    get_signal_registry,
    SignalGenerator,
    get_signal_generator,
    SignalFilter,
    get_signal_filter,
    SignalQualityAssessor,
    get_signal_quality_assessor,
    SignalStorage,
    get_signal_storage
)

from .strategy import (
    StrategyType,
    StrategyRegistry,
    get_strategy_registry,
    StrategyDesigner,
    get_strategy_designer,
    StockSelector,
    get_stock_selector,
    StrategyBacktester,
    get_strategy_backtester,
    StrategyOptimizer,
    get_strategy_optimizer,
    StrategyStorage,
    get_strategy_storage
)

from .portfolio import (
    PortfolioOptimizer,
    PortfolioNeutralizer,
    ConstraintsManager,
    PortfolioRebalancer,
    PortfolioEvaluator,
    PortfolioStorage
)

from .risk import (
    RiskLimits,
    get_risk_limits,
    RiskMetricsCalculator,
    PreTradeRiskChecker,
    IntradayRiskMonitor,
    PostTradeAnalyzer,
    RiskAlertManager,
    RiskReportGenerator
)

from .backtest import (
    BacktestEngine,
    BacktestConfig,
    BacktestResult,
    OrderMatcher,
    PerformanceAnalyzer,
    PerformanceMetrics,
    BacktestReporter
)


__all__ = [
    "ParquetStorage",
    "DataStorage",
    "get_data_storage",
    "reset_data_storage",
    
    "get_config_manager",
    "get_config",
    "get_data_paths",
    "AppException",
    "FactorException",
    "SignalException",
    "StrategyException",
    
    "PreCheckManager",
    "get_pre_check_manager",
    "TrustManager",
    "get_trust_manager",
    "CheckResult",
    "TrustLevel",
    
    "FactorCategory",
    "FactorSubCategory",
    "FactorClassification",
    "get_factor_classification",
    "FactorRegistry",
    "get_factor_registry",
    "FactorEngine",
    "get_factor_engine",
    "FactorValidator",
    "get_factor_validator",
    "FactorBacktester",
    "get_factor_backtester",
    "FactorScorer",
    "get_factor_scorer",
    "FactorStorage",
    "get_factor_storage",
    "FactorMiner",
    "get_factor_miner",
    "FactorMonitor",
    "get_factor_monitor",
    
    "SignalType",
    "SignalDirection",
    "SignalRegistry",
    "get_signal_registry",
    "SignalGenerator",
    "get_signal_generator",
    "SignalFilter",
    "get_signal_filter",
    "SignalQualityAssessor",
    "get_signal_quality_assessor",
    "SignalStorage",
    "get_signal_storage",
    
    "StrategyType",
    "StrategyRegistry",
    "get_strategy_registry",
    "StrategyDesigner",
    "get_strategy_designer",
    "StockSelector",
    "get_stock_selector",
    "StrategyBacktester",
    "get_strategy_backtester",
    "StrategyOptimizer",
    "get_strategy_optimizer",
    "StrategyStorage",
    "get_strategy_storage",
    
    "PortfolioOptimizer",
    "PortfolioNeutralizer",
    "ConstraintsManager",
    "PortfolioRebalancer",
    "PortfolioEvaluator",
    "PortfolioStorage",
    
    "RiskLimits",
    "get_risk_limits",
    "RiskMetricsCalculator",
    "PreTradeRiskChecker",
    "IntradayRiskMonitor",
    "PostTradeAnalyzer",
    "RiskAlertManager",
    "RiskReportGenerator",
    
    "BacktestEngine",
    "BacktestConfig",
    "BacktestResult",
    "OrderMatcher",
    "PerformanceAnalyzer",
    "PerformanceMetrics",
    "BacktestReporter",
]
