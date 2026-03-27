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

from .registry import (
    StrategyType,
    StrategyStatus,
    RebalanceFrequency,
    RiskParams,
    StrategyPerformance,
    SignalConfig,
    StrategyMetadata,
    StrategyRegistry,
    get_strategy_registry,
    reset_strategy_registry
)

from .designer import (
    StrategyTemplate,
    StrategyDesigner,
    BUILTIN_TEMPLATES,
    get_strategy_designer,
    reset_strategy_designer
)

from .selector import (
    StockSelection,
    SelectionResult,
    ScoreCalculator,
    StockSelector,
    get_stock_selector,
    reset_stock_selector
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


__all__ = [
    "StrategyType",
    "StrategyStatus",
    "RebalanceFrequency",
    "RiskParams",
    "StrategyPerformance",
    "SignalConfig",
    "StrategyMetadata",
    "StrategyRegistry",
    "get_strategy_registry",
    "reset_strategy_registry",
    
    "StrategyTemplate",
    "StrategyDesigner",
    "BUILTIN_TEMPLATES",
    "get_strategy_designer",
    "reset_strategy_designer",
    
    "StockSelection",
    "SelectionResult",
    "ScoreCalculator",
    "StockSelector",
    "get_stock_selector",
    "reset_stock_selector",
    
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
]
