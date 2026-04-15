"""
信号库管理系统

提供完整的信号管理功能，包括：
- 信号注册表
- 信号生成器
- 信号过滤器
- 信号质量评估
- 信号持久化存储
"""

from .registry import (
    SignalType,
    SignalDirection,
    SignalStatus,
    SignalStrength,
    SignalPerformance,
    SignalRules,
    SignalMetadata,
    SignalRegistry,
    get_signal_registry,
    reset_signal_registry
)

from .generator import (
    GeneratedSignal,
    SignalGenerationResult,
    FactorCombiner,
    SignalStrengthCalculator,
    SignalGenerator,
    get_signal_generator,
    reset_signal_generator
)

from .filter import (
    FilterConfig,
    FilterResult,
    StrengthFilter,
    WinRateFilter,
    ConfidenceFilter,
    IndustryDiversificationFilter,
    StockListFilter,
    TopNFilter,
    SignalFilter,
    get_signal_filter,
    reset_signal_filter
)

from .quality import (
    SignalQualityMetrics,
    QualityAssessmentResult,
    SignalQualityAssessor,
    get_signal_quality_assessor,
    reset_signal_quality_assessor
)

from .storage import (
    SignalStorageResult,
    SignalStorage,
    get_signal_storage,
    reset_signal_storage
)

from .ml_signal_generator import (
    MLSignalConfig,
    MLSignalResult,
    MLSignalGenerator,
    prepare_training_data,
    create_default_ml_signal_generator,
    get_ml_signal_generator,
    reset_ml_signal_generator
)

from .ai_signal_generator import (
    AIModelType,
    AISignalConfig,
    AISignalTrainingResult,
    AISignalModel,
    LSTMSignalModel,
    MLSignalModel,
    AISignalGenerator,
    create_ai_signal_generator,
    register_ai_signal
)

from .ai_enhanced_generator import (
    SignalSourceType,
    EnhancedSignalConfig,
    SignalEnsembleResult,
    AISignalIntegrator,
    EnhancedSignalGenerator,
    create_enhanced_signal_generator,
    get_enhanced_signal_generator
)


__all__ = [
    "SignalType",
    "SignalDirection",
    "SignalStatus",
    "SignalStrength",
    "SignalPerformance",
    "SignalRules",
    "SignalMetadata",
    "SignalRegistry",
    "get_signal_registry",
    "reset_signal_registry",
    
    "GeneratedSignal",
    "SignalGenerationResult",
    "FactorCombiner",
    "SignalStrengthCalculator",
    "SignalGenerator",
    "get_signal_generator",
    "reset_signal_generator",
    
    "FilterConfig",
    "FilterResult",
    "StrengthFilter",
    "WinRateFilter",
    "ConfidenceFilter",
    "IndustryDiversificationFilter",
    "StockListFilter",
    "TopNFilter",
    "SignalFilter",
    "get_signal_filter",
    "reset_signal_filter",
    
    "SignalQualityMetrics",
    "QualityAssessmentResult",
    "SignalQualityAssessor",
    "get_signal_quality_assessor",
    "reset_signal_quality_assessor",
    
    "SignalStorageResult",
    "SignalStorage",
    "get_signal_storage",
    "reset_signal_storage",
    
    "MLSignalConfig",
    "MLSignalResult",
    "MLSignalGenerator",
    "prepare_training_data",
    "create_default_ml_signal_generator",
    "get_ml_signal_generator",
    "reset_ml_signal_generator",
    
    "AIModelType",
    "AISignalConfig",
    "AISignalTrainingResult",
    "AISignalModel",
    "LSTMSignalModel",
    "MLSignalModel",
    "AISignalGenerator",
    "create_ai_signal_generator",
    "register_ai_signal",
]

from .dashboard import (
    SignalTypeFilter,
    SignalDirectionFilter,
    SignalStrengthFilter,
    SignalFilterConfig,
    DEFAULT_SIGNAL_FILTER_CONFIG,
    SignalDashboardConfigManager,
    SignalDashboardRow,
    SignalDashboardResult,
    SignalDashboard,
    get_signal_dashboard
)

__all__.extend([
    "SignalTypeFilter",
    "SignalDirectionFilter", 
    "SignalStrengthFilter",
    "SignalFilterConfig",
    "DEFAULT_SIGNAL_FILTER_CONFIG",
    "SignalDashboardConfigManager",
    "SignalDashboardRow",
    "SignalDashboardResult",
    "SignalDashboard",
    "get_signal_dashboard",
])
