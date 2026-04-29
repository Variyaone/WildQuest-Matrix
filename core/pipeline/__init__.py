"""
WildQuest Matrix - 智能管线模块

提供智能管线执行能力，包括：
1. 质量门控系统
2. 智能管线执行器
3. LLM 审查集成
4. 断点续传
5. 状态管理

Author: Variya
Version: 1.0.0
"""

from .quality_gate import (
    PipelineQualityManager,
    QualityGateResult,
    GateStatus,
)

# 为兼容性创建别名
QualityGateManager = PipelineQualityManager

# 这些类在当前版本中可能不存在，先创建占位符
class SmartPipelineExecutor:
    """智能管线执行器（占位符）"""
    pass

class PipelineState:
    """管线状态（占位符）"""
    pass

class ReviewDecision:
    """审查决策（占位符）"""
    pass

from .intelligent_pipeline import (
    IntelligentPipeline,
    create_intelligent_pipeline,
)

__all__ = [
    # 质量门控
    'QualityGateManager',
    'SmartPipelineExecutor',
    'QualityGateResult',
    'PipelineState',
    'GateStatus',
    'ReviewDecision',
    # 智能管线
    'IntelligentPipeline',
    'create_intelligent_pipeline',
]
