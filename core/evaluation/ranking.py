"""
绩效排名系统

对因子和策略进行排名。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np


@dataclass
class RankingResult:
    """排名结果"""
    name: str
    category: str
    rank: int
    total: int
    percentile: float
    score: float
    is_top_quartile: bool
    is_bottom_quartile: bool
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'category': self.category,
            'rank': self.rank,
            'total': self.total,
            'percentile': self.percentile,
            'score': self.score,
            'is_top_quartile': self.is_top_quartile,
            'is_bottom_quartile': self.is_bottom_quartile,
            'metrics': self.metrics
        }


class PerformanceRanking:
    """
    绩效排名系统
    
    对因子和策略进行排名。
    """
    
    FACTOR_WEIGHTS = {
        'ic': 0.30,
        'stability': 0.25,
        'correlation': 0.20,
        'utility': 0.25
    }
    
    STRATEGY_WEIGHTS = {
        'return': 0.30,
        'risk': 0.25,
        'risk_adjusted': 0.25,
        'stability': 0.20
    }
    
    def __init__(
        self,
        factor_weights: Optional[Dict[str, float]] = None,
        strategy_weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化排名系统
        
        Args:
            factor_weights: 因子排名权重
            strategy_weights: 策略排名权重
        """
        self.factor_weights = factor_weights or self.FACTOR_WEIGHTS.copy()
        self.strategy_weights = strategy_weights or self.STRATEGY_WEIGHTS.copy()
    
    def rank_factors(
        self,
        evaluation_results: Dict[str, Any],
        category: Optional[str] = None
    ) -> List[RankingResult]:
        """
        因子排名
        
        Args:
            evaluation_results: 因子评估结果字典
            category: 因子类别（用于分类排名）
            
        Returns:
            List[RankingResult]: 排名结果列表
        """
        scores = []
        
        for factor_name, result in evaluation_results.items():
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result
            
            ic_score = self._normalize_score(result_dict.get('ic_mean', 0), -0.1, 0.1)
            stability_score = result_dict.get('monthly_ic_stability', 0) * 100
            correlation_score = 100 - result_dict.get('correlation_with_similar', 0) * 100
            utility_score = result_dict.get('coverage', 0) * 100
            
            total_score = (
                ic_score * self.factor_weights['ic'] +
                stability_score * self.factor_weights['stability'] +
                correlation_score * self.factor_weights['correlation'] +
                utility_score * self.factor_weights['utility']
            )
            
            scores.append({
                'name': factor_name,
                'category': category or result_dict.get('category', 'unknown'),
                'score': total_score,
                'metrics': {
                    'ic_score': ic_score,
                    'stability_score': stability_score,
                    'correlation_score': correlation_score,
                    'utility_score': utility_score
                }
            })
        
        scores.sort(key=lambda x: x['score'], reverse=True)
        
        results = []
        total = len(scores)
        
        for i, item in enumerate(scores, 1):
            percentile = (total - i + 1) / total * 100
            
            result = RankingResult(
                name=item['name'],
                category=item['category'],
                rank=i,
                total=total,
                percentile=percentile,
                score=item['score'],
                is_top_quartile=percentile >= 75,
                is_bottom_quartile=percentile <= 25,
                metrics=item['metrics']
            )
            results.append(result)
        
        return results
    
    def rank_strategies(
        self,
        evaluation_results: Dict[str, Any],
        category: Optional[str] = None
    ) -> List[RankingResult]:
        """
        策略排名
        
        Args:
            evaluation_results: 策略评估结果字典
            category: 策略类别
            
        Returns:
            List[RankingResult]: 排名结果列表
        """
        scores = []
        
        for strategy_name, result in evaluation_results.items():
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result
            
            return_score = self._normalize_score(result_dict.get('annual_return', 0), -0.1, 0.3) * 100
            risk_score = 100 - abs(result_dict.get('max_drawdown', 0)) * 300
            risk_score = max(0, min(100, risk_score))
            
            sharpe = result_dict.get('sharpe_ratio', 0)
            risk_adjusted_score = self._normalize_score(sharpe, 0, 2) * 100
            
            stability_score = result_dict.get('stability_score', 70)
            
            total_score = (
                return_score * self.strategy_weights['return'] +
                risk_score * self.strategy_weights['risk'] +
                risk_adjusted_score * self.strategy_weights['risk_adjusted'] +
                stability_score * self.strategy_weights['stability']
            )
            
            scores.append({
                'name': strategy_name,
                'category': category or result_dict.get('category', 'unknown'),
                'score': total_score,
                'metrics': {
                    'return_score': return_score,
                    'risk_score': risk_score,
                    'risk_adjusted_score': risk_adjusted_score,
                    'stability_score': stability_score
                }
            })
        
        scores.sort(key=lambda x: x['score'], reverse=True)
        
        results = []
        total = len(scores)
        
        for i, item in enumerate(scores, 1):
            percentile = (total - i + 1) / total * 100
            
            result = RankingResult(
                name=item['name'],
                category=item['category'],
                rank=i,
                total=total,
                percentile=percentile,
                score=item['score'],
                is_top_quartile=percentile >= 75,
                is_bottom_quartile=percentile <= 25,
                metrics=item['metrics']
            )
            results.append(result)
        
        return results
    
    def rank_by_metric(
        self,
        data: Dict[str, float],
        higher_is_better: bool = True
    ) -> List[RankingResult]:
        """
        按单一指标排名
        
        Args:
            data: 数据字典 {名称: 值}
            higher_is_better: 是否越高越好
            
        Returns:
            List[RankingResult]: 排名结果列表
        """
        items = [(name, value) for name, value in data.items()]
        
        if higher_is_better:
            items.sort(key=lambda x: x[1], reverse=True)
        else:
            items.sort(key=lambda x: x[1])
        
        results = []
        total = len(items)
        
        for i, (name, value) in enumerate(items, 1):
            percentile = (total - i + 1) / total * 100 if higher_is_better else i / total * 100
            
            result = RankingResult(
                name=name,
                category='single_metric',
                rank=i,
                total=total,
                percentile=percentile,
                score=value,
                is_top_quartile=percentile >= 75,
                is_bottom_quartile=percentile <= 25,
                metrics={'value': value}
            )
            results.append(result)
        
        return results
    
    def rank_by_category(
        self,
        evaluation_results: Dict[str, Any],
        categories: Dict[str, str],
        ranking_type: str = "strategy"
    ) -> Dict[str, List[RankingResult]]:
        """
        分类排名
        
        Args:
            evaluation_results: 评估结果字典
            categories: 分类字典 {名称: 类别}
            ranking_type: 排名类型 (factor/strategy)
            
        Returns:
            Dict[str, List[RankingResult]]: 各类别排名结果
        """
        categorized = {}
        
        for name, result in evaluation_results.items():
            category = categories.get(name, 'other')
            
            if category not in categorized:
                categorized[category] = {}
            
            categorized[category][name] = result
        
        results = {}
        
        for category, items in categorized.items():
            if ranking_type == "factor":
                results[category] = self.rank_factors(items, category)
            else:
                results[category] = self.rank_strategies(items, category)
        
        return results
    
    def get_top_performers(
        self,
        ranking_results: List[RankingResult],
        n: int = 10
    ) -> List[RankingResult]:
        """
        获取排名前N的对象
        
        Args:
            ranking_results: 排名结果列表
            n: 数量
            
        Returns:
            List[RankingResult]: 前N名结果
        """
        return ranking_results[:n]
    
    def get_bottom_performers(
        self,
        ranking_results: List[RankingResult],
        n: int = 10
    ) -> List[RankingResult]:
        """
        获取排名后N的对象
        
        Args:
            ranking_results: 排名结果列表
            n: 数量
            
        Returns:
            List[RankingResult]: 后N名结果
        """
        return ranking_results[-n:]
    
    def get_quartile_distribution(
        self,
        ranking_results: List[RankingResult]
    ) -> Dict[str, List[str]]:
        """
        获取四分位分布
        
        Args:
            ranking_results: 排名结果列表
            
        Returns:
            Dict[str, List[str]]: 各四分位的名称列表
        """
        total = len(ranking_results)
        
        if total == 0:
            return {
                'top_quartile': [],
                'second_quartile': [],
                'third_quartile': [],
                'bottom_quartile': []
            }
        
        q1 = max(1, total // 4)
        q2 = max(1, total // 2)
        q3 = max(1, 3 * total // 4)
        
        return {
            'top_quartile': [r.name for r in ranking_results[:q1]],
            'second_quartile': [r.name for r in ranking_results[q1:q2]],
            'third_quartile': [r.name for r in ranking_results[q2:q3]],
            'bottom_quartile': [r.name for r in ranking_results[q3:]]
        }
    
    def generate_ranking_report(
        self,
        ranking_results: List[RankingResult],
        title: str = "排名报告"
    ) -> str:
        """
        生成排名报告
        
        Args:
            ranking_results: 排名结果列表
            title: 报告标题
            
        Returns:
            str: 报告内容
        """
        report = f"""
{title}
{'=' * 60}

"""
        
        if len(ranking_results) == 0:
            return report + "无排名数据"
        
        report += f"{'排名':<6}{'名称':<20}{'得分':<12}{'百分位':<10}{'四分位':<10}\n"
        report += "-" * 60 + "\n"
        
        for result in ranking_results:
            quartile = "前25%" if result.is_top_quartile else ("后25%" if result.is_bottom_quartile else "中段")
            report += f"{result.rank:<6}{result.name:<20}{result.score:<12.2f}{result.percentile:<10.1f}{quartile:<10}\n"
        
        distribution = self.get_quartile_distribution(ranking_results)
        
        report += f"\n四分位分布:\n"
        report += f"  前25%: {', '.join(distribution['top_quartile'][:5])}{'...' if len(distribution['top_quartile']) > 5 else ''}\n"
        report += f"  后25%: {', '.join(distribution['bottom_quartile'][:5])}{'...' if len(distribution['bottom_quartile']) > 5 else ''}\n"
        
        return report
    
    def _normalize_score(
        self,
        value: float,
        min_val: float,
        max_val: float
    ) -> float:
        """归一化分数到0-100"""
        if max_val == min_val:
            return 50
        
        normalized = (value - min_val) / (max_val - min_val)
        normalized = max(0, min(1, normalized))
        
        return normalized * 100
    
    def to_dataframe(
        self,
        ranking_results: List[RankingResult]
    ) -> pd.DataFrame:
        """
        转换为DataFrame
        
        Args:
            ranking_results: 排名结果列表
            
        Returns:
            pd.DataFrame: 排名结果表
        """
        data = []
        
        for result in ranking_results:
            row = {
                'name': result.name,
                'category': result.category,
                'rank': result.rank,
                'total': result.total,
                'percentile': result.percentile,
                'score': result.score,
                'is_top_quartile': result.is_top_quartile,
                'is_bottom_quartile': result.is_bottom_quartile
            }
            row.update(result.metrics)
            data.append(row)
        
        return pd.DataFrame(data)
