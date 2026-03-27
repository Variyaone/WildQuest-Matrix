"""
评估系统模块

提供因子和策略的绩效评估功能，包括：
- 因子绩效评估器：评估因子预测能力
- 策略绩效评估器：评估策略收益风险特征
- 绩效指标计算库：标准化绩效指标计算
- 绩效对比分析：对比多个因子或策略
- 绩效排名系统：对因子和策略排名
- 评估报告生成器：生成评估报告
"""

from .factor_evaluator import FactorEvaluator, FactorEvaluationResult
from .strategy_evaluator import StrategyEvaluator, StrategyEvaluationResult
from .metrics import PerformanceMetricsCalculator
from .comparison import PerformanceComparison
from .ranking import PerformanceRanking, RankingResult
from .report import EvaluationReportGenerator

__all__ = [
    'FactorEvaluator',
    'FactorEvaluationResult',
    'StrategyEvaluator',
    'StrategyEvaluationResult',
    'PerformanceMetricsCalculator',
    'PerformanceComparison',
    'PerformanceRanking',
    'RankingResult',
    'EvaluationReportGenerator',
]
