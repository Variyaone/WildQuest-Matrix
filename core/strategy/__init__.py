"""
策略库管理系统

提供完整的策略管理功能，包括：
- 策略注册表
- 策略设计器
- 股票选择器
- 策略回测器
- 策略优化器
- 策略持久化存储
"""

from core.infrastructure.exceptions import AppException, ErrorCode


class StrategyException(AppException):
    """策略异常"""
    
    def __init__(self, message: str, details: dict = None, cause: Exception = None):
        super().__init__(
            message=message,
            code=ErrorCode.STRATEGY_ERROR,
            details=details or {},
            cause=cause
        )


from .registry import (
    StrategyType,
    StrategyStatus,
    RebalanceFrequency,
    RiskParams,
    StrategyPerformance,
    StrategyMetadata,
    StrategyRegistry,
    get_strategy_registry,
    reset_strategy_registry
)

from .factor_combiner import (
    FactorCombinationConfig,
    FactorCombinationResult,
    FactorCombiner,
    get_factor_combiner,
    reset_factor_combiner
)

from .combination_storage import (
    CombinationRecord,
    CombinationStorage,
    get_combination_storage,
    reset_combination_storage
)

from .alpha_generator import (
    AlphaGenerationResult,
    AlphaGenerator,
    get_alpha_generator,
    reset_alpha_generator
)

from .designer import (
    StrategyTemplate,
    StrategyDesigner,
    BUILTIN_TEMPLATES,
    get_strategy_designer,
    reset_strategy_designer
)

from .backtester import (
    BacktestMode,
    Position,
    Portfolio,
    Trade,
    BacktestResult,
    PortfolioSimulator,
    PerformanceCalculator,
    StrategyBacktester,
    get_strategy_backtester,
    reset_strategy_backtester
)

from .optimizer import (
    OptimizationMethod,
    OptimizationTarget,
    ParameterRange,
    OptimizationResult,
    GridSearchOptimizer,
    RandomSearchOptimizer,
    GeneticOptimizer,
    StrategyOptimizer,
    get_strategy_optimizer,
    reset_strategy_optimizer
)

from .storage import (
    StrategyStorageResult,
    StrategyStorage,
    get_strategy_storage,
    reset_strategy_storage
)

from .preset_loader import (
    load_preset_strategies,
    import_preset_strategy,
    import_all_preset_strategies,
    get_preset_strategy_info,
    list_preset_strategies
)

from .abu_signals import (
    load_abu_signals,
    get_all_signals,
    get_signals_by_category,
    get_signals_by_type,
    get_signal_strategies,
    get_signal_info,
    list_buy_signals,
    list_sell_signals,
    search_signals
)

from .execution import (
    ExecutionStatus,
    ExecutionResult,
    ExecutionConfig,
    StrategyExecutor,
    get_strategy_executor,
    reset_strategy_executor
)

from .rl_strategy import (
    RLAlgorithm,
    RLConfig,
    TradingState,
    TradingAction,
    RLTrainingResult,
    TradingEnvironment,
    PPOAgent,
    DQNAgent,
    RLTradingStrategy,
    create_rl_strategy,
    register_rl_strategy,
    get_rl_strategy
)

from .multi_strategy_combiner import (
    AllocationMethod,
    StrategyAllocation,
    MultiStrategyResult,
    StrategyPerformance,
    MultiStrategyCombiner,
    create_strategy_combiner
)

from .dashboard import (
    StrategyTypeFilter,
    RebalanceFreqFilter,
    StrategyFilterConfig,
    DEFAULT_STRATEGY_FILTER_CONFIG,
    StrategyDashboardConfigManager,
    StrategyDashboardRow,
    StrategyDashboardResult,
    StrategyDashboard,
    get_strategy_dashboard
)


__all__ = [
    "StrategyType",
    "StrategyStatus",
    "RebalanceFrequency",
    "RiskParams",
    "StrategyPerformance",
    "StrategyMetadata",
    "StrategyRegistry",
    "get_strategy_registry",
    "reset_strategy_registry",
    
    "FactorCombinationConfig",
    "FactorCombinationResult",
    "FactorCombiner",
    "get_factor_combiner",
    "reset_factor_combiner",
    
    "CombinationRecord",
    "CombinationStorage",
    "get_combination_storage",
    "reset_combination_storage",
    
    "AlphaGenerationResult",
    "AlphaGenerator",
    "get_alpha_generator",
    "reset_alpha_generator",
    
    "StrategyTemplate",
    "StrategyDesigner",
    "BUILTIN_TEMPLATES",
    "get_strategy_designer",
    "reset_strategy_designer",
    
    "BacktestMode",
    "Position",
    "Portfolio",
    "Trade",
    "BacktestResult",
    "PortfolioSimulator",
    "PerformanceCalculator",
    "StrategyBacktester",
    "get_strategy_backtester",
    "reset_strategy_backtester",
    
    "OptimizationMethod",
    "OptimizationTarget",
    "ParameterRange",
    "OptimizationResult",
    "GridSearchOptimizer",
    "RandomSearchOptimizer",
    "GeneticOptimizer",
    "StrategyOptimizer",
    "get_strategy_optimizer",
    "reset_strategy_optimizer",
    
    "StrategyStorageResult",
    "StrategyStorage",
    "get_strategy_storage",
    "reset_strategy_storage",
    
    "load_preset_strategies",
    "import_preset_strategy",
    "import_all_preset_strategies",
    "get_preset_strategy_info",
    "list_preset_strategies",
    
    "load_abu_signals",
    "get_all_signals",
    "get_signals_by_category",
    "get_signals_by_type",
    "get_signal_strategies",
    "get_signal_info",
    "list_buy_signals",
    "list_sell_signals",
    "search_signals",
    
    "ExecutionStatus",
    "ExecutionResult",
    "ExecutionConfig",
    "StrategyExecutor",
    "get_strategy_executor",
    "reset_strategy_executor",
    
    "RLAlgorithm",
    "RLConfig",
    "TradingState",
    "TradingAction",
    "RLTrainingResult",
    "TradingEnvironment",
    "PPOAgent",
    "DQNAgent",
    "RLTradingStrategy",
    "create_rl_strategy",
    "get_rl_strategy",
    "register_rl_strategy",
    
    "AllocationMethod",
    "StrategyAllocation",
    "MultiStrategyResult",
    "StrategyPerformance",
    "MultiStrategyCombiner",
    "create_strategy_combiner",
    
    "StrategyTypeFilter",
    "RebalanceFreqFilter",
    "StrategyFilterConfig",
    "DEFAULT_STRATEGY_FILTER_CONFIG",
    "StrategyDashboardConfigManager",
    "StrategyDashboardRow",
    "StrategyDashboardResult",
    "StrategyDashboard",
    "get_strategy_dashboard",
]
