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
    ValidationStatus,
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
    BacktestFrequency,
    MarketType,
    HoldingPeriod,
    TransactionCosts,
    ICStatistics,
    MonotonicityTest,
    BacktestCredibility,
    OOSValidationResult,
    TradingConstraints,
    ICSignificanceTester,
    MonotonicityAnalyzer,
    OOSValidator,
    TradingCalendarValidator,
    CredibilityAssessor,
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
    StockPool,
    ScoringWeights,
    ScoreSnapshot,
    FactorScore,
    FactorScoreHistory,
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
    DecayAction,
    DecayThresholds,
    DecayMetrics,
    DecayReport,
    RollingICCalculator,
    DecayDetector,
    FactorMonitor,
    get_factor_monitor,
    reset_factor_monitor
)

from .validation_scheduler import (
    ValidationTrigger,
    ValidationLevel,
    ValidationSchedule,
    ValidationTaskResult,
    ValidationReport,
    ValidationScheduler,
    get_validation_scheduler,
    reset_validation_scheduler
)

from .migration import (
    MigrationResult,
    ALPHA101_FACTORS,
    ALPHA191_FACTORS,
    CICC_FACTORS,
    HUATAI_FACTORS,
    SHENWAN_FACTORS,
    TALIB_FACTORS,
    CUSTOM_FACTORS,
    FactorMigrator,
    migrate_factors,
    get_factor_migrator
)

from .ml_models import (
    ModelType,
    ModelStatus,
    ModelConfig,
    TrainingResult,
    PredictionResult,
    BaseModelAdapter,
    LightGBMAdapter,
    XGBoostAdapter,
    MLPAdapter,
    QlibModelAdapter,
    ModelFactory,
    MLEnhancedFactorEngine,
    get_ml_engine,
    reset_ml_engine
)

from .ai_factor_miner import (
    AIModelConfig,
    TrainingResult as AITrainingResult,
    AIFactorResult,
    FeatureEngineer,
    BaseModel,
    LSTMModel,
    TransformerModel,
    MLModel,
    AIFactorMiner,
    create_ai_factor_miner,
    get_ai_factor_miner
)

from .enhanced_validator import (
    ValidationLevel,
    ValidationThreshold,
    InvalidScoreIssue,
    EnhancedValidationResult,
    EnhancedFactorValidator,
    BacktestParameterRecorder,
    get_enhanced_validator
)

from .quick_entry import (
    QuickEntryResult,
    FactorQuickEntry,
    StrategyQuickEntry,
    get_factor_quick_entry,
    get_strategy_quick_entry
)

from .enhanced_daily_backtest import (
    PriceType,
    TradingStatus,
    EnhancedDailyConfig,
    EnhancedLimitHandler,
    ExecutionPriceSimulator,
    OvernightGapAnalyzer,
    EnhancedDailyBacktest,
    get_enhanced_daily_config
)

from .hourly_backtest import (
    HourlyFrequency,
    HourlyBacktestConfig,
    TradingSessionManager,
    IntradayFactorCalculator,
    HourlyLimitHandler,
    HourlyBacktester,
    get_hourly_backtester
)

from .dashboard import (
    StockPool,
    BacktestPeriod,
    FactorFilterConfig,
    DEFAULT_FILTER_CONFIG,
    FactorDashboardConfigManager,
    FactorDashboardRow,
    FactorDashboardResult,
    FactorDashboard,
    get_factor_dashboard
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
    "TransactionCosts",
    "BacktestFrequency",
    "ICStatistics",
    "MonotonicityTest",
    "BacktestCredibility",
    "TradingConstraints",
    "ICSignificanceTester",
    "MonotonicityAnalyzer",
    "CredibilityAssessor",
    "GroupBacktestResult",
    "FactorBacktestResult",
    "MarketClassifier",
    "GroupConstructor",
    "PortfolioSimulator",
    "FactorBacktester",
    "get_factor_backtester",
    "reset_factor_backtester",
    
    "StockPool",
    "ScoringWeights",
    "ScoreSnapshot",
    "FactorScore",
    "FactorScoreHistory",
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
    "DecayAction",
    "DecayThresholds",
    "DecayMetrics",
    "DecayReport",
    "RollingICCalculator",
    "DecayDetector",
    "FactorMonitor",
    "get_factor_monitor",
    "reset_factor_monitor",
    
    "ValidationTrigger",
    "ValidationLevel",
    "ValidationSchedule",
    "ValidationTaskResult",
    "ValidationReport",
    "ValidationScheduler",
    "get_validation_scheduler",
    "reset_validation_scheduler",
    
    "MigrationResult",
    "ALPHA101_FACTORS",
    "ALPHA191_FACTORS",
    "CICC_FACTORS",
    "HUATAI_FACTORS",
    "SHENWAN_FACTORS",
    "TALIB_FACTORS",
    "CUSTOM_FACTORS",
    "FactorMigrator",
    "migrate_factors",
    "get_factor_migrator",
    
    "ModelType",
    "ModelStatus",
    "ModelConfig",
    "TrainingResult",
    "PredictionResult",
    "BaseModelAdapter",
    "LightGBMAdapter",
    "XGBoostAdapter",
    "MLPAdapter",
    "QlibModelAdapter",
    "ModelFactory",
    "MLEnhancedFactorEngine",
    "get_ml_engine",
    "reset_ml_engine",
    
    "AIModelConfig",
    "AITrainingResult",
    "AIFactorResult",
    "FeatureEngineer",
    "BaseModel",
    "LSTMModel",
    "TransformerModel",
    "MLModel",
    "AIFactorMiner",
    "create_ai_factor_miner",
    "get_ai_factor_miner",
    
    "ValidationLevel",
    "ValidationThreshold",
    "InvalidScoreIssue",
    "EnhancedValidationResult",
    "EnhancedFactorValidator",
    "BacktestParameterRecorder",
    "get_enhanced_validator",
    
    "QuickEntryResult",
    "FactorQuickEntry",
    "StrategyQuickEntry",
    "get_factor_quick_entry",
    "get_strategy_quick_entry",
    
    "PriceType",
    "TradingStatus",
    "EnhancedDailyConfig",
    "EnhancedLimitHandler",
    "ExecutionPriceSimulator",
    "OvernightGapAnalyzer",
    "EnhancedDailyBacktest",
    "get_enhanced_daily_config",
    
    "HourlyFrequency",
    "HourlyBacktestConfig",
    "TradingSessionManager",
    "IntradayFactorCalculator",
    "HourlyLimitHandler",
    "HourlyBacktester",
    "get_hourly_backtester",
    
    "StockPool",
    "BacktestPeriod",
    "FactorFilterConfig",
    "DEFAULT_FILTER_CONFIG",
    "FactorDashboardConfigManager",
    "FactorDashboardRow",
    "FactorDashboardResult",
    "FactorDashboard",
    "get_factor_dashboard",
]


def calculate_factors(
    factor_ids: list = None,
    max_factors: int = 10,
    save_results: bool = True
) -> dict:
    """
    计算因子（管线调用入口）
    
    Args:
        factor_ids: 要计算的因子ID列表（None则计算前N个）
        max_factors: 最大计算因子数量
        save_results: 是否保存结果
    
    Returns:
        计算结果字典
    """
    import time
    from pathlib import Path
    import pandas as pd
    from ..infrastructure.logging import get_logger
    from ..infrastructure.config import get_data_paths
    from ..data.storage import ParquetStorage
    
    logger = get_logger("factor.calculate")
    paths = get_data_paths()
    storage = ParquetStorage(paths)
    registry = get_factor_registry()
    engine = get_factor_engine()
    
    start_time = time.time()
    
    logger.info("=" * 60)
    logger.info("开始因子计算")
    logger.info("=" * 60)
    
    all_factors = registry.list_all()
    
    if not all_factors:
        logger.warning("没有注册的因子")
        return {
            "status": "error",
            "message": "没有注册的因子",
            "factors_calculated": 0,
            "factors_failed": 0
        }
    
    if factor_ids is None:
        factor_ids = [f.id for f in all_factors[:max_factors]]
    
    logger.info(f"待计算因子数量: {len(factor_ids)}")
    
    stock_list_path = Path(paths.data_root) / "stock_list.parquet"
    if not stock_list_path.exists():
        logger.error("股票列表不存在，请先更新数据")
        return {
            "status": "error",
            "message": "股票列表不存在",
            "factors_calculated": 0,
            "factors_failed": 0
        }
    
    stock_list = pd.read_parquet(stock_list_path)
    if stock_list.empty:
        logger.error("股票列表为空，请先更新数据")
        return {
            "status": "error",
            "message": "股票列表为空",
            "factors_calculated": 0,
            "factors_failed": 0
        }
    
    if 'code' in stock_list.columns:
        stock_codes = stock_list['code'].tolist()[:100]
    elif 'stock_code' in stock_list.columns:
        stock_codes = stock_list['stock_code'].tolist()[:100]
    else:
        logger.error("股票列表缺少代码列")
        return {
            "status": "error",
            "message": "股票列表缺少代码列",
            "factors_calculated": 0,
            "factors_failed": 0
        }
    
    stock_data = {}
    for stock_code in stock_codes:
        try:
            history = storage.load_stock_data(stock_code, "daily")
            if history is not None and not history.empty:
                stock_data[stock_code] = history
        except Exception as e:
            logger.warning(f"加载 {stock_code} 数据失败: {e}")
    
    if not stock_data:
        logger.error("没有可用的历史数据")
        return {
            "status": "error",
            "message": "没有可用的历史数据",
            "factors_calculated": 0,
            "factors_failed": 0
        }
    
    logger.info(f"加载数据: {len(stock_data)} 只股票")
    
    factors_calculated = 0
    factors_failed = 0
    total_rows = 0
    all_factor_results = {fid: [] for fid in factor_ids}
    
    for stock_code, df in stock_data.items():
        data = {col: df[col] for col in df.columns if col not in ['date', 'stock_code']}
        data['date'] = df['date'] if 'date' in df.columns else None
        
        for factor_id in factor_ids:
            result = engine.compute_single(factor_id, data, stock_code=stock_code)
            if result.success and result.data is not None:
                all_factor_results[factor_id].append(result.data)
    
    for factor_id, result_dfs in all_factor_results.items():
        if result_dfs:
            combined_df = pd.concat(result_dfs, ignore_index=True)
            total_rows += len(combined_df)
            factors_calculated += 1
            
            if save_results:
                try:
                    factor_path = Path(paths.data_root) / "factors" / f"{factor_id}.parquet"
                    factor_path.parent.mkdir(parents=True, exist_ok=True)
                    combined_df.to_parquet(factor_path, index=False)
                    logger.info(f"  ✓ {factor_id}: {len(combined_df)} 行")
                except Exception as e:
                    logger.error(f"  ✗ {factor_id} 保存失败: {e}")
        else:
            factors_failed += 1
            logger.error(f"  ✗ {factor_id}: 计算失败")
    
    duration = time.time() - start_time
    
    logger.info("=" * 60)
    logger.info("因子计算完成")
    logger.info(f"  成功: {factors_calculated}")
    logger.info(f"  失败: {factors_failed}")
    logger.info(f"  总行数: {total_rows}")
    logger.info(f"  耗时: {duration:.2f} 秒")
    logger.info("=" * 60)
    
    return {
        "status": "success" if factors_failed == 0 else "partial",
        "factors_calculated": factors_calculated,
        "factors_failed": factors_failed,
        "total_rows": total_rows,
        "duration_seconds": duration,
        "factor_ids": factor_ids
    }
