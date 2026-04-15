"""
因子评分系统模块

综合评估因子质量并排名，支持多维度评分和动态排名。
支持历史评分记录、股票池维度评分、加权计算。
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
from pathlib import Path

import pandas as pd
import numpy as np

from .registry import FactorMetadata, FactorQualityMetrics, get_factor_registry, ValidationStatus
from .validator import ValidationResult
from .backtester import FactorBacktestResult
from ..infrastructure.exceptions import FactorException


class StockPool(Enum):
    """股票池类型"""
    ALL = "全市场"
    HS300 = "沪深300"
    ZZ500 = "中证500"
    ZZ1000 = "中证1000"
    CYB = "创业板"
    KCB = "科创板"


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
class ScoreSnapshot:
    """评分快照 - 记录某次回测的评分"""
    score_id: str
    factor_id: str
    stock_pool: str
    score_date: str
    total_score: float
    ic_score: float
    ir_score: float
    monotonicity_score: float
    backtest_score: float
    innovation_score: float
    grade: str = "C"
    backtest_period: str = ""
    backtest_return: float = 0.0
    backtest_sharpe: float = 0.0
    backtest_drawdown: float = 0.0
    ic_mean: float = 0.0
    ir: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score_id": self.score_id,
            "factor_id": self.factor_id,
            "stock_pool": self.stock_pool,
            "score_date": self.score_date,
            "total_score": self.total_score,
            "ic_score": self.ic_score,
            "ir_score": self.ir_score,
            "monotonicity_score": self.monotonicity_score,
            "backtest_score": self.backtest_score,
            "innovation_score": self.innovation_score,
            "grade": self.grade,
            "backtest_period": self.backtest_period,
            "backtest_return": self.backtest_return,
            "backtest_sharpe": self.backtest_sharpe,
            "backtest_drawdown": self.backtest_drawdown,
            "ic_mean": self.ic_mean,
            "ir": self.ir,
            "details": self.details
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScoreSnapshot":
        return cls(
            score_id=data.get("score_id", ""),
            factor_id=data.get("factor_id", ""),
            stock_pool=data.get("stock_pool", "全市场"),
            score_date=data.get("score_date", ""),
            total_score=data.get("total_score", 0.0),
            ic_score=data.get("ic_score", 0.0),
            ir_score=data.get("ir_score", 0.0),
            monotonicity_score=data.get("monotonicity_score", 0.0),
            backtest_score=data.get("backtest_score", 0.0),
            innovation_score=data.get("innovation_score", 0.0),
            grade=data.get("grade", "C"),
            backtest_period=data.get("backtest_period", ""),
            backtest_return=data.get("backtest_return", 0.0),
            backtest_sharpe=data.get("backtest_sharpe", 0.0),
            backtest_drawdown=data.get("backtest_drawdown", 0.0),
            ic_mean=data.get("ic_mean", 0.0),
            ir=data.get("ir", 0.0),
            details=data.get("details", {})
        )


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
    stock_pool: str = "全市场"
    weighted_score: float = 0.0
    score_count: int = 0
    score_trend: str = "stable"
    details: Dict[str, Any] = None


@dataclass
class FactorScoreHistory:
    """因子评分历史记录"""
    factor_id: str
    stock_pool: str
    snapshots: List[ScoreSnapshot] = field(default_factory=list)
    
    def add_snapshot(self, snapshot: ScoreSnapshot):
        """添加评分快照"""
        self.snapshots.append(snapshot)
        self.snapshots.sort(key=lambda x: x.score_date, reverse=True)
        if len(self.snapshots) > 100:
            self.snapshots = self.snapshots[:100]
    
    def get_weighted_score(self, decay_factor: float = 0.9) -> float:
        """
        计算加权评分（指数衰减）
        
        Args:
            decay_factor: 衰减因子，越大则历史评分权重越高
            
        Returns:
            float: 加权评分
        """
        if not self.snapshots:
            return 0.0
        
        weights = []
        for i in range(len(self.snapshots)):
            weights.append(decay_factor ** i)
        
        total_weight = sum(weights)
        weighted_sum = sum(
            s.total_score * w 
            for s, w in zip(self.snapshots, weights)
        )
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def get_score_trend(self) -> str:
        """
        获取评分趋势
        
        Returns:
            str: 'improving', 'declining', 'stable'
        """
        if len(self.snapshots) < 3:
            return "stable"
        
        recent_scores = [s.total_score for s in self.snapshots[:5]]
        if len(recent_scores) < 3:
            return "stable"
        
        avg_recent = np.mean(recent_scores[:2])
        avg_older = np.mean(recent_scores[2:])
        
        if avg_recent > avg_older * 1.1:
            return "improving"
        elif avg_recent < avg_older * 0.9:
            return "declining"
        return "stable"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "stock_pool": self.stock_pool,
            "snapshots": [s.to_dict() for s in self.snapshots]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactorScoreHistory":
        return cls(
            factor_id=data.get("factor_id", ""),
            stock_pool=data.get("stock_pool", "全市场"),
            snapshots=[ScoreSnapshot.from_dict(s) for s in data.get("snapshots", [])]
        )


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
    支持历史评分记录、股票池维度评分、加权计算。
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
    
    SCORE_HISTORY_FILE = "./data/factors/score_history.json"
    
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
        self._score_history: Dict[str, Dict[str, FactorScoreHistory]] = {}
        self._load_score_history()
    
    def _load_score_history(self):
        """加载评分历史"""
        try:
            path = Path(self.SCORE_HISTORY_FILE)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for factor_id, pools in data.items():
                    self._score_history[factor_id] = {}
                    for pool, history in pools.items():
                        self._score_history[factor_id][pool] = FactorScoreHistory.from_dict(history)
        except Exception:
            self._score_history = {}
    
    def _save_score_history(self):
        """保存评分历史"""
        try:
            path = Path(self.SCORE_HISTORY_FILE)
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            for factor_id, pools in self._score_history.items():
                data[factor_id] = {}
                for pool, history in pools.items():
                    data[factor_id][pool] = history.to_dict()
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def record_score_snapshot(
        self,
        factor_id: str,
        stock_pool: str,
        backtest_result: Optional[Dict[str, Any]] = None,
        quality_metrics: Optional[FactorQualityMetrics] = None
    ) -> ScoreSnapshot:
        """
        记录评分快照（回测后调用）
        
        Args:
            factor_id: 因子ID
            stock_pool: 股票池
            backtest_result: 回测结果
            quality_metrics: 质量指标
            
        Returns:
            ScoreSnapshot: 评分快照
        """
        factor = self._registry.get(factor_id)
        if not factor:
            raise FactorException(f"因子不存在: {factor_id}")
        
        metrics = quality_metrics or factor.quality_metrics or FactorQualityMetrics()
        
        ic_score = self._normalizer.normalize_ic(metrics.ic_mean)
        ir_score = self._normalizer.normalize_ir(metrics.ir)
        monotonicity_score = self._normalizer.normalize_monotonicity(metrics.monotonicity)
        
        backtest_score = 50.0
        backtest_return = 0.0
        backtest_sharpe = 0.0
        backtest_drawdown = 0.0
        backtest_period = ""
        credibility_adjustment = 1.0
        
        if backtest_result:
            credibility = backtest_result.get("credibility", {})
            credibility_score = credibility.get("total_score", 0) if isinstance(credibility, dict) else 0
            
            if credibility_score > 0:
                if credibility_score >= 70:
                    credibility_adjustment = 1.0
                elif credibility_score >= 50:
                    credibility_adjustment = 0.8
                else:
                    credibility_adjustment = 0.5
            
            oos_validation = backtest_result.get("oos_validation", {})
            if isinstance(oos_validation, dict) and oos_validation:
                if not oos_validation.get("is_valid", True):
                    ic_decay_rate = oos_validation.get("ic_decay_rate", 0)
                    if ic_decay_rate > 0.5:
                        credibility_adjustment *= 0.7
                    elif ic_decay_rate > 0.3:
                        credibility_adjustment *= 0.85
            
            backtest_score = self._normalizer.normalize_backtest(
                backtest_result.get("annual_return", 0),
                backtest_result.get("sharpe_ratio", 0),
                backtest_result.get("max_drawdown", 0),
                backtest_result.get("win_rate", 0.5)
            )
            backtest_return = backtest_result.get("annual_return", 0)
            backtest_sharpe = backtest_result.get("sharpe_ratio", 0)
            backtest_drawdown = backtest_result.get("max_drawdown", 0)
            backtest_period = backtest_result.get("period", "")
        
        innovation_score = self._normalizer.normalize_innovation(
            factor.source,
            metrics.correlation_with_others,
            False
        )
        
        total_score = (
            ic_score * self.weights.ic_performance +
            ir_score * self.weights.stability_ir +
            monotonicity_score * self.weights.monotonicity +
            backtest_score * self.weights.backtest_performance +
            innovation_score * self.weights.innovation
        )
        
        total_score *= credibility_adjustment
        
        grade = self._get_grade(total_score)
        
        score_id = f"{factor_id}_{stock_pool}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        snapshot = ScoreSnapshot(
            score_id=score_id,
            factor_id=factor_id,
            stock_pool=stock_pool,
            score_date=datetime.now().strftime("%Y-%m-%d"),
            total_score=total_score,
            ic_score=ic_score,
            ir_score=ir_score,
            monotonicity_score=monotonicity_score,
            backtest_score=backtest_score,
            innovation_score=innovation_score,
            grade=grade,
            backtest_period=backtest_period,
            backtest_return=backtest_return,
            backtest_sharpe=backtest_sharpe,
            backtest_drawdown=backtest_drawdown,
            ic_mean=metrics.ic_mean,
            ir=metrics.ir,
            details={
                "correlation": metrics.correlation_with_others,
                "nan_ratio": metrics.nan_ratio,
                "coverage": metrics.coverage,
                "credibility_adjustment": credibility_adjustment,
                "credibility_score": backtest_result.get("credibility", {}).get("total_score", 0) if backtest_result else 0,
                "oos_validation": backtest_result.get("oos_validation", {}) if backtest_result else {},
                "trading_calendar_valid": backtest_result.get("trading_calendar_valid", True) if backtest_result else True,
                "non_trading_days_filtered": backtest_result.get("non_trading_days_filtered", 0) if backtest_result else 0
            }
        )
        
        if factor_id not in self._score_history:
            self._score_history[factor_id] = {}
        if stock_pool not in self._score_history[factor_id]:
            self._score_history[factor_id][stock_pool] = FactorScoreHistory(
                factor_id=factor_id,
                stock_pool=stock_pool
            )
        
        self._score_history[factor_id][stock_pool].add_snapshot(snapshot)
        self._save_score_history()
        
        return snapshot
    
    def get_factor_weighted_score(
        self,
        factor_id: str,
        stock_pool: str = "全市场",
        decay_factor: float = 0.9
    ) -> float:
        """
        获取因子加权评分
        
        Args:
            factor_id: 因子ID
            stock_pool: 股票池
            decay_factor: 衰减因子
            
        Returns:
            float: 加权评分
        """
        if factor_id not in self._score_history:
            return 0.0
        if stock_pool not in self._score_history[factor_id]:
            return 0.0
        
        return self._score_history[factor_id][stock_pool].get_weighted_score(decay_factor)
    
    def get_factor_score_history(
        self,
        factor_id: str,
        stock_pool: str = "全市场"
    ) -> Optional[FactorScoreHistory]:
        """
        获取因子评分历史
        
        Args:
            factor_id: 因子ID
            stock_pool: 股票池
            
        Returns:
            Optional[FactorScoreHistory]: 评分历史
        """
        if factor_id not in self._score_history:
            return None
        return self._score_history[factor_id].get(stock_pool)
    
    def get_factor_all_pools_scores(
        self,
        factor_id: str,
        decay_factor: float = 0.9
    ) -> Dict[str, float]:
        """
        获取因子在所有股票池的加权评分
        
        Args:
            factor_id: 因子ID
            decay_factor: 衰减因子
            
        Returns:
            Dict[str, float]: {股票池: 加权评分}
        """
        result = {}
        if factor_id not in self._score_history:
            return result
        
        for pool, history in self._score_history[factor_id].items():
            result[pool] = history.get_weighted_score(decay_factor)
        
        return result
    
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
        validation_status = getattr(factor, 'validation_status', ValidationStatus.NOT_VALIDATED)
        
        if validation_status == ValidationStatus.NOT_VALIDATED:
            return FactorScore(
                factor_id=factor.id,
                total_score=0.0,
                ic_score=0.0,
                ir_score=0.0,
                monotonicity_score=0.0,
                backtest_score=0.0,
                innovation_score=0.0,
                grade="N/A",
                details={
                    "reason": "因子未通过验证",
                    "validation_status": "not_validated"
                }
            )
        
        if validation_status == ValidationStatus.FAILED:
            return FactorScore(
                factor_id=factor.id,
                total_score=0.0,
                ic_score=0.0,
                ir_score=0.0,
                monotonicity_score=0.0,
                backtest_score=0.0,
                innovation_score=0.0,
                grade="F",
                details={
                    "reason": "因子验证失败",
                    "validation_status": "failed"
                }
            )
        
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
                "correlation": metrics.correlation_with_others,
                "validation_status": validation_status.value
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
    
    def score_all_factors(self, stock_pool: str = "全市场", use_weighted: bool = True) -> List[FactorScore]:
        """
        评估所有因子并排名
        
        Args:
            stock_pool: 股票池
            use_weighted: 是否使用加权评分
            
        Returns:
            List[FactorScore]: 排序后的评分列表
        """
        factors = self._registry.list_by_status(
            self._registry._factors.get(list(self._registry._factors.keys())[0]).status if self._registry._factors else None
        )
        
        if not factors:
            factors = self._registry.list_all()
        
        scores = []
        for f in factors:
            base_score = self.score_factor(f)
            
            if use_weighted and f.id in self._score_history:
                pool_scores = self.get_factor_all_pools_scores(f.id)
                if stock_pool in pool_scores:
                    base_score.weighted_score = pool_scores[stock_pool]
                elif "全市场" in pool_scores:
                    base_score.weighted_score = pool_scores["全市场"]
                else:
                    base_score.weighted_score = base_score.total_score
                
                history = self.get_factor_score_history(f.id, stock_pool)
                if history:
                    base_score.score_count = len(history.snapshots)
                    base_score.score_trend = history.get_score_trend()
            
            base_score.stock_pool = stock_pool
            scores.append(base_score)
        
        sort_key = 'weighted_score' if use_weighted else 'total_score'
        scores.sort(key=lambda x: getattr(x, sort_key), reverse=True)
        
        for i, score in enumerate(scores):
            score.rank = i + 1
            score.percentile = (1 - i / len(scores)) * 100 if scores else 0
        
        return scores
    
    def update_factor_scores(self, stock_pool: str = "全市场") -> Dict[str, FactorScore]:
        """
        更新所有因子评分并保存到注册表
        
        Args:
            stock_pool: 股票池
            
        Returns:
            Dict[str, FactorScore]: 评分结果字典
        """
        scores = self.score_all_factors(stock_pool=stock_pool, use_weighted=True)
        
        result = {}
        for score in scores:
            final_score = score.weighted_score if score.weighted_score > 0 else score.total_score
            self._registry.update_score(
                score.factor_id,
                final_score,
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
