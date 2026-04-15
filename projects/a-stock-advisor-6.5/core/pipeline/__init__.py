"""
管线模块

提供完整的量化投资管线执行能力。
"""

from .quality_gate import (
    QualityGate,
    QualityGateResult,
    QualityLevel,
    GateStatus,
    QualityMetric,
    DataUpdateQualityGate,
    FactorCalculationQualityGate,
    AlphaGenerationQualityGate,
    BacktestQualityGate,
    PortfolioOptimizationQualityGate,
    RiskCheckQualityGate,
    PipelineQualityManager,
    get_quality_manager
)

__all__ = [
    "QualityGate",
    "QualityGateResult",
    "QualityLevel",
    "GateStatus",
    "QualityMetric",
    "DataUpdateQualityGate",
    "FactorCalculationQualityGate",
    "AlphaGenerationQualityGate",
    "BacktestQualityGate",
    "PortfolioOptimizationQualityGate",
    "RiskCheckQualityGate",
    "PipelineQualityManager",
    "get_quality_manager"
]
