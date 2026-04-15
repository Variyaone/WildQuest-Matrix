"""
WildQuest Matrix - A股量化投顾系统核心模块

包含：
- data: 数据管理模块
- infrastructure: 基础设施模块
- validation: 验证模块
- factor: 因子库管理系统
- signal: 信号库管理系统
- strategy: 策略库管理系统
- portfolio: 组合优化模块
- risk: 风控系统模块
- backtest: 回测系统模块
- trading: 交易系统模块
- monitor: 监控系统模块
- evaluation: 评估系统模块
- rdagent: RDAgent集成模块
"""

__version__ = "6.5.0"
__author__ = "Variya"

from .data import (
    ParquetStorage,
    DataStorage,
    get_data_storage,
    reset_data_storage,
    get_data_fetcher,
    reset_data_fetcher,
    get_unified_updater,
    reset_unified_updater,
    UnifiedDataUpdater,
    MultiSourceFetcher
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
    # StockSelector,  # TODO: 需要重构，使用AlphaGenerator
    # get_stock_selector,  # TODO: 需要重构
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

from .trading import (
    OrderManager,
    TradeOrder,
    OrderSide,
    OrderType,
    PositionManager,
    TradeNotifier,
    create_rl_executor,
    get_local_account_tracker,
    get_trade_feedback_handler
)

from .monitor import (
    Dashboard,
    DashboardManager,
    PerformanceTracker,
    AlertSystem,
    AlertLevel,
    ReportGenerator,
    ReportType,
    AttributionAnalyzer,
    FactorDecayMonitor,
    SignalQualityMonitor,
    StrategyHealthMonitor,
    SystemHealthMonitor,
    get_alert_trigger,
    get_monitor_dashboard
)

from .evaluation import (
    FactorEvaluator,
    StrategyEvaluator,
    PerformanceMetricsCalculator,
    PerformanceComparison,
    PerformanceRanking,
    EvaluationReportGenerator
)

from .rdagent_integration import (
    RDAgentRunner,
    RDAgentConfig,
    RDAgentScenario
)


__all__ = [
    "ParquetStorage",
    "DataStorage",
    "get_data_storage",
    "reset_data_storage",
    "get_data_fetcher",
    "reset_data_fetcher",
    "get_unified_updater",
    "reset_unified_updater",
    "UnifiedDataUpdater",
    "MultiSourceFetcher",
    
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
    # "StockSelector",  # TODO: 需要重构
    # "get_stock_selector",  # TODO: 需要重构
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
    
    "OrderManager",
    "TradeOrder",
    "OrderSide",
    "OrderType",
    "PositionManager",
    "TradeNotifier",
    "create_rl_executor",
    "get_local_account_tracker",
    "get_trade_feedback_handler",
    
    "Dashboard",
    "DashboardManager",
    "PerformanceTracker",
    "AlertSystem",
    "AlertLevel",
    "ReportGenerator",
    "ReportType",
    "AttributionAnalyzer",
    "FactorDecayMonitor",
    "SignalQualityMonitor",
    "StrategyHealthMonitor",
    "SystemHealthMonitor",
    "get_alert_trigger",
    "get_monitor_dashboard",
    
    "FactorEvaluator",
    "StrategyEvaluator",
    "PerformanceMetricsCalculator",
    "PerformanceComparison",
    "PerformanceRanking",
    "EvaluationReportGenerator",
    
    "RDAgentRunner",
    "RDAgentConfig",
    "LLMProvider",
    "RDAgentScenario",
    "check_rdagent_installed",
    "get_rdagent_version",
    "import_rdagent_factors",
]
