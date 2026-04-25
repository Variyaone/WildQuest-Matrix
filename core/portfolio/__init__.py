"""
组合优化与持仓管理模块

功能:
- 组合权重优化
- 行业/风格中性化
- 组合约束管理
- 再平衡策略
- 风险预算配置
- 组合评估归因
- 组合持久化存储

优化方法:
- equal_weight: 等权重优化
- risk_parity: 风险平价
- mean_variance: 均值方差优化
- max_diversification: 最大分散化
- black_litterman: Black-Litterman模型
"""

from .optimizer import (
    OptimizationStatus,
    OptimizationResult,
    OptimizationError,
    PortfolioOptimizer,
)

from .neutralizer import (
    NeutralizationStatus,
    NeutralizationResult,
    NeutralizationError,
    PortfolioNeutralizer,
)

from .constraints import (
    ConstraintType,
    ConstraintStatus,
    ConstraintResult,
    ConstraintsCheckResult,
    ConstraintConfig,
    ConstraintError,
    ConstraintsManager,
)

from .rebalancer import (
    RebalanceTrigger,
    RebalanceStatus,
    Trade,
    RebalanceResult,
    RebalanceConfig,
    RebalanceError,
    PortfolioRebalancer,
)

from .risk_budget import (
    RiskBudgetType,
    RiskBudgetStatus,
    RiskBudgetItem,
    RiskBudgetResult,
    RiskBudgetConfig,
    RiskBudgetError,
    RiskBudgetManager,
)

from .evaluator import (
    EvaluationStatus,
    PerformanceMetrics,
    AttributionResult,
    RiskDecomposition,
    EvaluationResult,
    EvaluationError,
    PortfolioEvaluator,
)

from .storage import (
    PortfolioMetadata,
    PortfolioSnapshot,
    PortfolioStorage,
)

from .sizer import (
    SizingMethod,
    SizingStatus,
    PositionSize,
    SizingResult,
    SizingConfig,
    PositionSizer,
    PositionSizerError,
    get_position_sizer,
    reset_position_sizer,
)


__all__ = [
    'OptimizationStatus',
    'OptimizationResult',
    'OptimizationError',
    'PortfolioOptimizer',
    
    'NeutralizationStatus',
    'NeutralizationResult',
    'NeutralizationError',
    'PortfolioNeutralizer',
    
    'ConstraintType',
    'ConstraintStatus',
    'ConstraintResult',
    'ConstraintsCheckResult',
    'ConstraintConfig',
    'ConstraintError',
    'ConstraintsManager',
    
    'RebalanceTrigger',
    'RebalanceStatus',
    'Trade',
    'RebalanceResult',
    'RebalanceConfig',
    'RebalanceError',
    'PortfolioRebalancer',
    
    'RiskBudgetType',
    'RiskBudgetStatus',
    'RiskBudgetItem',
    'RiskBudgetResult',
    'RiskBudgetConfig',
    'RiskBudgetError',
    'RiskBudgetManager',
    
    'EvaluationStatus',
    'PerformanceMetrics',
    'AttributionResult',
    'RiskDecomposition',
    'EvaluationResult',
    'EvaluationError',
    'PortfolioEvaluator',
    
    'PortfolioMetadata',
    'PortfolioSnapshot',
    'PortfolioStorage',
    
    'SizingMethod',
    'SizingStatus',
    'PositionSize',
    'SizingResult',
    'SizingConfig',
    'PositionSizer',
    'PositionSizerError',
    'get_position_sizer',
    'reset_position_sizer',
]
