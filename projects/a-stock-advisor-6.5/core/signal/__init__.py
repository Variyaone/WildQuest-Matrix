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
]
