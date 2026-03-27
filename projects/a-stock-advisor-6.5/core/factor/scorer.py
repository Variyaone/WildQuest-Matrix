"""
因子评分系统模块

综合评估因子质量并排名，支持多维度评分和动态排名。
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import numpy as np

from .registry import FactorMetadata, FactorQualityMetrics, get_factor_registry
from .validator import ValidationResult
from .backtester import FactorBacktestResult
from ..infrastructure.exceptions import FactorException


@dataclass
class ScoringWeights:
    """评分权重配置"""
    ic_performance: float = 0.30
    stability_ir: float = 0.25
    monotonicity: float = 0.15
    backtest_performance: float = 0.20
    innovation: float = 0.10
    
    def validate(self) -> bool:
        """验证权重总和是否为1"""
        total = (
            self.ic_performance + 
            self.stability_ir + 
            self.monotonicity + 
            self.backtest_performance + 
            self.innovation
        )
        return abs(total - 1.0) < 0.001


@dataclass
class FactorScore:
    """因子评分结果"""
    factor_id: str
    total_score: float
    ic_score: float
    ir_score: float
    monotonicity_score: float
    backtest_score: float
    innovation_score: float
    rank: int = 0
    percentile: float = 0.0
    grade: str = "C"
    details: Dict[str, Any] = None


class ScoreNormalizer:
    """
    分数标准化器
    
    将各项指标转换为0-100的标准分数。
    """
    
    @staticmethod
    def normalize_ic(ic_mean: float, max_ic: float = 0.1) -> float:
        """
        标准化IC分数
        
        Args:
            ic_mean: IC均值
            max_ic: IC最大阈值
            
        Returns:
            float: 标准化分数 (0-100)
        """
        abs_ic = abs(ic_mean)
        score = min(abs_ic / max_ic, 1.0) * 100
        return score
    
    @staticmethod
    def normalize_ir(ir: float, max_ir: float = 1.0) -> float:
        """
        标准化IR分数
        
        Args:
            ir: 信息比率
            max_ir: IR最大阈值
            
        Returns:
            float: 标准化分数 (0-100)
        """
        abs_ir = abs(ir)
        score = min(abs_ir / max_ir, 1.0) * 100
        return score
    
    @staticmethod
    def normalize_monotonicity(monotonicity: float) -> float:
        """
        标准化单调性分数
        
        Args:
            monotonicity: 单调性值
            
        Returns:
            float: 标准化分数 (0-100)
        """
        return monotonicity * 100
    
    @staticmethod
    def normalize_backtest(
        annual_return: float,
        sharpe_ratio: float,
        max_drawdown: float,
        win_rate: float
    ) -> float:
        """
        标准化回测分数
        
        Args:
            annual_return: 年化收益
            sharpe_ratio: 夏普比率
            max_drawdown: 最大回撤
            win_rate: 胜率
            
        Returns:
            float: 标准化分数 (0-100)
        """
        return_score = min(max(annual_return, 0), 0.5) / 0.5 * 30
        sharpe_score = min(max(sharpe_ratio, 0), 3) / 3 * 30
        drawdown_score = max(0, 1 + max_drawdown) * 20
        win_rate_score = win_rate * 20
        
        return return_score + sharpe_score + drawdown_score + win_rate_score
    
    @staticmethod
    def normalize_innovation(
        source: str,
        correlation_with_others: float,
        is_new: bool = False
    ) -> float:
        """
        标准化创新性分数
        
        Args:
            source: 因子来源
            correlation_with_others: 与其他因子的相关性
            is_new: 是否为新因子
            
        Returns:
            float: 标准化分数 (0-100)
        """
        source_score = 50
        if source == "自研":
            source_score = 80
        elif source in ["Alpha101", "Alpha191", "WorldQuant"]:
            source_score = 60
        elif source == "学术论文":
            source_score = 70
        
        low_correlation_bonus = (1 - correlation_with_others) * 20
        
        new_bonus = 10 if is_new else 0
        
        return min(source_score + low_correlation_bonus + new_bonus, 100)


class FactorScorer:
    """
    因子评分系统
    
    综合评估因子质量并排名。
    """
    
    GRADE_THRESHOLDS = [
        (90, "A+"),
        (85, "A"),
        (80, "A-"),
        (75, "B+"),
        (70, "B"),
        (65, "B-"),
        (60, "C+"),
        (55, "C"),
        (50, "C-"),
        (0, "D")
    ]
    
    def __init__(self, weights: Optional[ScoringWeights] = None):
        """
        初始化因子评分系统
        
        Args:
            weights: 评分权重配置
        """
        self.weights = weights or ScoringWeights()
        if not self.weights.validate():
            raise ValueError("评分权重总和必须为1")
        
        self._registry = get_factor_registry()
        self._normalizer = ScoreNormalizer()
    
    def score_factor(
        self,
        factor: FactorMetadata,
        is_new: bool = False
    ) -> FactorScore:
        """
        评估单个因子
        
        Args:
            factor: 因子元数据
            is_new: 是否为新因子
            
        Returns:
            FactorScore: 评分结果
        """
        metrics = factor.quality_metrics or FactorQualityMetrics()
        
        ic_score = self._normalizer.normalize_ic(metrics.ic_mean)
        
        ir_score = self._normalizer.normalize_ir(metrics.ir)
        
        monotonicity_score = self._normalizer.normalize_monotonicity(metrics.monotonicity)
        
        backtest_score = 50.0
        if factor.backtest_results:
            avg_results = self._aggregate_backtest_results(factor.backtest_results)
            backtest_score = self._normalizer.normalize_backtest(
                avg_results["annual_return"],
                avg_results["sharpe_ratio"],
                avg_results["max_drawdown"],
                avg_results["win_rate"]
            )
        
        innovation_score = self._normalizer.normalize_innovation(
            factor.source,
            metrics.correlation_with_others,
            is_new
        )
        
        total_score = (
            ic_score * self.weights.ic_performance +
            ir_score * self.weights.stability_ir +
            monotonicity_score * self.weights.monotonicity +
            backtest_score * self.weights.backtest_performance +
            innovation_score * self.weights.innovation
        )
        
        grade = self._get_grade(total_score)
        
        return FactorScore(
            factor_id=factor.id,
            total_score=total_score,
            ic_score=ic_score,
            ir_score=ir_score,
            monotonicity_score=monotonicity_score,
            backtest_score=backtest_score,
            innovation_score=innovation_score,
            grade=grade,
            details={
                "ic_mean": metrics.ic_mean,
                "ir": metrics.ir,
                "monotonicity": metrics.monotonicity,
                "correlation": metrics.correlation_with_others
            }
        )
    
    def _aggregate_backtest_results(
        self,
        backtest_results: Dict[str, Any]
    ) -> Dict[str, float]:
        """聚合回测结果"""
        if not backtest_results:
            return {
                "annual_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.5
            }
        
        returns = []
        sharpes = []
        drawdowns = []
        win_rates = []
        
        for result in backtest_results.values():
            if hasattr(result, 'annual_return'):
                returns.append(result.annual_return)
                sharpes.append(result.sharpe_ratio)
                drawdowns.append(result.max_drawdown)
                win_rates.append(result.win_rate)
        
        return {
            "annual_return": np.mean(returns) if returns else 0.0,
            "sharpe_ratio": np.mean(sharpes) if sharpes else 0.0,
            "max_drawdown": np.mean(drawdowns) if drawdowns else 0.0,
            "win_rate": np.mean(win_rates) if win_rates else 0.5
        }
    
    def _get_grade(self, score: float) -> str:
        """根据分数获取等级"""
        for threshold, grade in self.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return "D"
    
    def score_all_factors(self) -> List[FactorScore]:
        """
        评估所有因子并排名
        
        Returns:
            List[FactorScore]: 排序后的评分列表
        """
        factors = self._registry.list_by_status(
            self._registry._factors.get(list(self._registry._factors.keys())[0]).status if self._registry._factors else None
        )
        
        if not factors:
            factors = self._registry.list_all()
        
        scores = [self.score_factor(f) for f in factors]
        
        scores.sort(key=lambda x: x.total_score, reverse=True)
        
        for i, score in enumerate(scores):
            score.rank = i + 1
            score.percentile = (1 - i / len(scores)) * 100 if scores else 0
        
        return scores
    
    def update_factor_scores(self) -> Dict[str, FactorScore]:
        """
        更新所有因子评分并保存到注册表
        
        Returns:
            Dict[str, FactorScore]: 评分结果字典
        """
        scores = self.score_all_factors()
        
        result = {}
        for score in scores:
            self._registry.update_score(
                score.factor_id,
                score.total_score,
                score.rank
            )
            result[score.factor_id] = score
        
        return result
    
    def get_top_factors(self, n: int = 10) -> List[FactorScore]:
        """
        获取排名前N的因子
        
        Args:
            n: 数量
            
        Returns:
            List[FactorScore]: 前N名因子评分
        """
        scores = self.score_all_factors()
        return scores[:n]
    
    def get_factors_by_grade(self, grade: str) -> List[FactorScore]:
        """
        按等级获取因子
        
        Args:
            grade: 等级
            
        Returns:
            List[FactorScore]: 指定等级的因子评分
        """
        scores = self.score_all_factors()
        return [s for s in scores if s.grade == grade]
    
    def generate_score_report(
        self,
        score: FactorScore,
        factor: FactorMetadata
    ) -> str:
        """
        生成评分报告
        
        Args:
            score: 评分结果
            factor: 因子元数据
            
        Returns:
            str: 报告文本
        """
        lines = [
            f"因子评分报告 - {factor.name} ({factor.id})",
            "=" * 50,
            f"总分: {score.total_score:.2f} ({score.grade})",
            f"排名: 第{score.rank}名 (前{score.percentile:.1f}%)",
            "",
            "分项得分:",
            "-" * 50,
            f"  IC表现: {score.ic_score:.2f} (权重: {self.weights.ic_performance:.0%})",
            f"  稳定性IR: {score.ir_score:.2f} (权重: {self.weights.stability_ir:.0%})",
            f"  单调性: {score.monotonicity_score:.2f} (权重: {self.weights.monotonicity:.0%})",
            f"  回测表现: {score.backtest_score:.2f} (权重: {self.weights.backtest_performance:.0%})",
            f"  创新性: {score.innovation_score:.2f} (权重: {self.weights.innovation:.0%})",
            "",
            "因子信息:",
            "-" * 50,
            f"  分类: {factor.category.value} - {factor.sub_category.value}",
            f"  来源: {factor.source}",
            f"  方向: {factor.direction.value}",
            f"  状态: {factor.status.value}",
        ]
        
        if factor.quality_metrics:
            metrics = factor.quality_metrics
            lines.extend([
                "",
                "质量指标:",
                "-" * 50,
                f"  IC均值: {metrics.ic_mean:.4f}",
                f"  IC标准差: {metrics.ic_std:.4f}",
                f"  信息比率: {metrics.ir:.4f}",
                f"  单调性: {metrics.monotonicity:.4f}",
                f"  因子相关性: {metrics.correlation_with_others:.4f}",
                f"  NaN比例: {metrics.nan_ratio:.2%}",
            ])
        
        return "\n".join(lines)


_default_scorer: Optional[FactorScorer] = None


def get_factor_scorer(weights: Optional[ScoringWeights] = None) -> FactorScorer:
    """获取全局因子评分系统实例"""
    global _default_scorer
    if _default_scorer is None or weights is not None:
        _default_scorer = FactorScorer(weights)
    return _default_scorer


def reset_factor_scorer():
    """重置全局因子评分系统"""
    global _default_scorer
    _default_scorer = None
