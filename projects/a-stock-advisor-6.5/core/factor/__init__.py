"""
因子库管理系统

提供完整的因子管理功能，包括：
- 因子分类体系
- 因子注册表
- 因子计算引擎
- 因子验证器
- 因子回测器
- 因子评分系统
- 因子持久化存储
- 因子挖掘器
- 因子衰减监控
"""

from .classification import (
    FactorCategory,
    FactorSubCategory,
    FactorTypeInfo,
    FactorClassification,
    get_factor_classification,
    reset_factor_classification,
    FACTOR_CLASSIFICATION
)

from .registry import (
    FactorDirection,
    FactorStatus,
    FactorSource,
    FactorQualityMetrics,
    BacktestResult,
    FactorMetadata,
    FactorRegistry,
    get_factor_registry,
    reset_factor_registry
)

from .engine import (
    OperatorRegistry,
    FormulaParser,
    FactorComputeContext,
    FactorEngine,
    FactorComputeResult,
    get_factor_engine,
    reset_factor_engine
)

from .validator import (
    ICAnalyzer,
    MonotonicityAnalyzer,
    CorrelationAnalyzer,
    FactorValidator,
    ValidationResult,
    ICAnalysisResult,
    get_factor_validator,
    reset_factor_validator
)

from .backtester import (
    MarketType,
    HoldingPeriod,
    GroupBacktestResult,
    FactorBacktestResult,
    MarketClassifier,
    GroupConstructor,
    PortfolioSimulator,
    FactorBacktester,
    get_factor_backtester,
    reset_factor_backtester
)

from .scorer import (
    ScoringWeights,
    FactorScore,
    ScoreNormalizer,
    FactorScorer,
    get_factor_scorer,
    reset_factor_scorer
)

from .storage import (
    StorageResult,
    FactorStorage,
    get_factor_storage,
    reset_factor_storage
)

from .miner import (
    GeneNode,
    CandidateFactor,
    GeneticProgrammingConfig,
    GeneticProgrammingMiner,
    FactorCombiner,
    FactorMiner,
    get_factor_miner,
    reset_factor_miner
)

from .monitor import (
    DecayLevel,
    DecayMetrics,
    DecayReport,
    RollingICCalculator,
    DecayDetector,
    FactorMonitor,
    get_factor_monitor,
    reset_factor_monitor
)

from .migration import (
    MigrationResult,
    ALPHA101_FACTORS,
    ALPHA191_FACTORS,
    CUSTOM_FACTORS,
    FactorMigrator,
    migrate_factors,
    get_factor_migrator
)


__all__ = [
    "FactorCategory",
    "FactorSubCategory",
    "FactorTypeInfo",
    "FactorClassification",
    "get_factor_classification",
    "reset_factor_classification",
    "FACTOR_CLASSIFICATION",
    
    "FactorDirection",
    "FactorStatus",
    "FactorSource",
    "FactorQualityMetrics",
    "BacktestResult",
    "FactorMetadata",
    "FactorRegistry",
    "get_factor_registry",
    "reset_factor_registry",
    
    "OperatorRegistry",
    "FormulaParser",
    "FactorComputeContext",
    "FactorEngine",
    "FactorComputeResult",
    "get_factor_engine",
    "reset_factor_engine",
    
    "ICAnalyzer",
    "MonotonicityAnalyzer",
    "CorrelationAnalyzer",
    "FactorValidator",
    "ValidationResult",
    "ICAnalysisResult",
    "get_factor_validator",
    "reset_factor_validator",
    
    "MarketType",
    "HoldingPeriod",
    "GroupBacktestResult",
    "FactorBacktestResult",
    "MarketClassifier",
    "GroupConstructor",
    "PortfolioSimulator",
    "FactorBacktester",
    "get_factor_backtester",
    "reset_factor_backtester",
    
    "ScoringWeights",
    "FactorScore",
    "ScoreNormalizer",
    "FactorScorer",
    "get_factor_scorer",
    "reset_factor_scorer",
    
    "StorageResult",
    "FactorStorage",
    "get_factor_storage",
    "reset_factor_storage",
    
    "GeneNode",
    "CandidateFactor",
    "GeneticProgrammingConfig",
    "GeneticProgrammingMiner",
    "FactorCombiner",
    "FactorMiner",
    "get_factor_miner",
    "reset_factor_miner",
    
    "DecayLevel",
    "DecayMetrics",
    "DecayReport",
    "RollingICCalculator",
    "DecayDetector",
    "FactorMonitor",
    "get_factor_monitor",
    "reset_factor_monitor",
    
    "MigrationResult",
    "ALPHA101_FACTORS",
    "ALPHA191_FACTORS",
    "CUSTOM_FACTORS",
    "FactorMigrator",
    "migrate_factors",
    "get_factor_migrator",
]
