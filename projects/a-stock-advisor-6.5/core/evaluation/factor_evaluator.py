"""
因子绩效评估器

评估因子的预测能力和稳定性。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import pandas as pd
import numpy as np

from .metrics import PerformanceMetricsCalculator


@dataclass
class FactorEvaluationResult:
    """因子评估结果"""
    factor_id: str
    factor_name: str
    evaluation_date: str
    start_date: str
    end_date: str
    
    ic_mean: float = 0.0
    ic_std: float = 0.0
    ir: float = 0.0
    ic_trend: str = "stable"
    
    monotonicity: float = 0.0
    long_short_return: float = 0.0
    
    monthly_ic_stability: float = 0.0
    bull_market_ic: float = 0.0
    bear_market_ic: float = 0.0
    sideways_market_ic: float = 0.0
    
    correlation_with_similar: float = 0.0
    correlation_with_other: float = 0.0
    redundancy: str = "low"
    
    coverage: float = 0.0
    turnover: float = 0.0
    complexity: str = "low"
    
    prediction_score: int = 0
    stability_score: int = 0
    correlation_score: int = 0
    utility_score: int = 0
    total_score: int = 0
    rank: int = 0
    total_factors: int = 0
    
    recommended_usage: str = ""
    recommended_weight: str = ""
    warnings: List[str] = field(default_factory=list)
    paired_factors: List[str] = field(default_factory=list)
    
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'factor_id': self.factor_id,
            'factor_name': self.factor_name,
            'evaluation_date': self.evaluation_date,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'ic_mean': self.ic_mean,
            'ic_std': self.ic_std,
            'ir': self.ir,
            'ic_trend': self.ic_trend,
            'monotonicity': self.monotonicity,
            'long_short_return': self.long_short_return,
            'monthly_ic_stability': self.monthly_ic_stability,
            'bull_market_ic': self.bull_market_ic,
            'bear_market_ic': self.bear_market_ic,
            'sideways_market_ic': self.sideways_market_ic,
            'correlation_with_similar': self.correlation_with_similar,
            'correlation_with_other': self.correlation_with_other,
            'redundancy': self.redundancy,
            'coverage': self.coverage,
            'turnover': self.turnover,
            'complexity': self.complexity,
            'prediction_score': self.prediction_score,
            'stability_score': self.stability_score,
            'correlation_score': self.correlation_score,
            'utility_score': self.utility_score,
            'total_score': self.total_score,
            'rank': self.rank,
            'total_factors': self.total_factors,
            'recommended_usage': self.recommended_usage,
            'recommended_weight': self.recommended_weight,
            'warnings': self.warnings,
            'paired_factors': self.paired_factors,
            'details': self.details
        }
    
    def get_summary(self) -> str:
        """获取摘要"""
        return f"""
因子评估报告
================
因子编号: {self.factor_id}
因子名称: {self.factor_name}
评估日期: {self.evaluation_date}
评估周期: {self.start_date} 至 {self.end_date}

一、预测能力评估
  IC均值: {self.ic_mean:.4f}
  IC标准差: {self.ic_std:.4f}
  IR: {self.ir:.4f}
  IC趋势: {self.ic_trend}
  单调性: {self.monotonicity:.2f}
  多空收益: {self.long_short_return:.2%}

二、稳定性评估
  月度IC稳定性: {self.monthly_ic_stability:.2f}
  牛市IC: {self.bull_market_ic:.4f}
  熊市IC: {self.bear_market_ic:.4f}
  震荡市IC: {self.sideways_market_ic:.4f}

三、相关性评估
  同类因子相关性: {self.correlation_with_similar:.2f}
  其他因子相关性: {self.correlation_with_other:.2f}
  冗余度: {self.redundancy}

四、实用性评估
  覆盖率: {self.coverage:.2%}
  换手率: {self.turnover:.2%}
  计算复杂度: {self.complexity}

五、综合评分
  预测能力: {self.prediction_score}/100
  稳定性: {self.stability_score}/100
  相关性: {self.correlation_score}/100
  实用性: {self.utility_score}/100
  综合得分: {self.total_score}/100 (排名: {self.rank}/{self.total_factors})

六、使用建议
  推荐场景: {self.recommended_usage}
  推荐权重: {self.recommended_weight}
  注意事项: {', '.join(self.warnings) if self.warnings else '无'}
  配对因子: {', '.join(self.paired_factors) if self.paired_factors else '无'}
"""


class FactorEvaluator:
    """
    因子绩效评估器
    
    评估因子的预测能力和稳定性。
    """
    
    IC_THRESHOLDS = {
        'excellent': 0.05,
        'good': 0.03,
        'fair': 0.01,
        'poor': 0.0
    }
    
    IR_THRESHOLDS = {
        'excellent': 0.5,
        'good': 0.3,
        'fair': 0.1,
        'poor': 0.0
    }
    
    def __init__(
        self,
        n_groups: int = 5,
        forward_periods: List[int] = None,
        ic_method: str = "spearman"
    ):
        """
        初始化因子评估器
        
        Args:
            n_groups: 分组数量
            forward_periods: 预测周期列表
            ic_method: IC计算方法 (pearson/spearman)
        """
        self.n_groups = n_groups
        self.forward_periods = forward_periods or [1, 5, 10, 20]
        self.ic_method = ic_method
    
    def evaluate(
        self,
        factor_data: pd.DataFrame,
        return_data: pd.DataFrame,
        factor_id: str = "",
        factor_name: str = "",
        market_states: Optional[pd.Series] = None,
        other_factors: Optional[Dict[str, pd.DataFrame]] = None
    ) -> FactorEvaluationResult:
        """
        评估因子
        
        Args:
            factor_data: 因子数据 (index: date, columns: stock_codes)
            return_data: 收益数据 (index: date, columns: stock_codes)
            factor_id: 因子ID
            factor_name: 因子名称
            market_states: 市场状态序列
            other_factors: 其他因子数据字典
            
        Returns:
            FactorEvaluationResult: 评估结果
        """
        result = FactorEvaluationResult(
            factor_id=factor_id,
            factor_name=factor_name,
            evaluation_date=datetime.now().strftime('%Y-%m-%d'),
            start_date=str(factor_data.index.min())[:10] if len(factor_data) > 0 else "",
            end_date=str(factor_data.index.max())[:10] if len(factor_data) > 0 else ""
        )
        
        ic_results = self._calculate_ic(factor_data, return_data)
        result.ic_mean = ic_results['ic_mean']
        result.ic_std = ic_results['ic_std']
        result.ir = ic_results['ir']
        result.ic_trend = ic_results['trend']
        result.details['ic_series'] = ic_results.get('ic_series', {})
        
        group_results = self._calculate_group_returns(factor_data, return_data)
        result.monotonicity = group_results['monotonicity']
        result.long_short_return = group_results['long_short_return']
        result.details['group_returns'] = group_results.get('group_returns', {})
        
        stability_results = self._evaluate_stability(
            factor_data, return_data, market_states
        )
        result.monthly_ic_stability = stability_results['monthly_stability']
        result.bull_market_ic = stability_results['bull_ic']
        result.bear_market_ic = stability_results['bear_ic']
        result.sideways_market_ic = stability_results['sideways_ic']
        
        if other_factors:
            corr_results = self._evaluate_correlation(factor_data, other_factors)
            result.correlation_with_similar = corr_results['similar_correlation']
            result.correlation_with_other = corr_results['other_correlation']
            result.redundancy = corr_results['redundancy']
        
        utility_results = self._evaluate_utility(factor_data)
        result.coverage = utility_results['coverage']
        result.turnover = utility_results['turnover']
        result.complexity = utility_results['complexity']
        
        scores = self._calculate_scores(result)
        result.prediction_score = scores['prediction']
        result.stability_score = scores['stability']
        result.correlation_score = scores['correlation']
        result.utility_score = scores['utility']
        result.total_score = scores['total']
        
        recommendations = self._generate_recommendations(result)
        result.recommended_usage = recommendations['usage']
        result.recommended_weight = recommendations['weight']
        result.warnings = recommendations['warnings']
        result.paired_factors = recommendations['paired_factors']
        
        return result
    
    def _calculate_ic(
        self,
        factor_data: pd.DataFrame,
        return_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """计算IC"""
        ics = []
        
        for date in factor_data.index:
            if date not in return_data.index:
                continue
            
            factor_vals = factor_data.loc[date].dropna()
            return_vals = return_data.loc[date].dropna()
            
            common_stocks = factor_vals.index.intersection(return_vals.index)
            
            if len(common_stocks) < 10:
                continue
            
            if self.ic_method == "spearman":
                ic = factor_vals[common_stocks].corr(return_vals[common_stocks], method='spearman')
            else:
                ic = factor_vals[common_stocks].corr(return_vals[common_stocks], method='pearson')
            
            if pd.notna(ic):
                ics.append({'date': date, 'ic': ic})
        
        if not ics:
            return {
                'ic_mean': 0.0,
                'ic_std': 0.0,
                'ir': 0.0,
                'trend': 'unknown'
            }
        
        ic_series = pd.DataFrame(ics).set_index('date')['ic']
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        ir = ic_mean / ic_std if ic_std > 0 else 0.0
        
        if len(ic_series) > 20:
            recent = ic_series.tail(20).mean()
            earlier = ic_series.head(20).mean()
            if recent > earlier * 1.1:
                trend = "improving"
            elif recent < earlier * 0.9:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            'ic_mean': ic_mean,
            'ic_std': ic_std,
            'ir': ir,
            'trend': trend,
            'ic_series': ic_series.to_dict()
        }
    
    def _calculate_group_returns(
        self,
        factor_data: pd.DataFrame,
        return_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """计算分组收益"""
        group_returns = {f'group_{i+1}': [] for i in range(self.n_groups)}
        
        for date in factor_data.index:
            if date not in return_data.index:
                continue
            
            factor_vals = factor_data.loc[date].dropna()
            return_vals = return_data.loc[date]
            
            common_stocks = factor_vals.index.intersection(return_vals.index)
            
            if len(common_stocks) < self.n_groups * 5:
                continue
            
            ranked = factor_vals[common_stocks].rank()
            group_size = len(ranked) // self.n_groups
            
            for i in range(self.n_groups):
                if i == self.n_groups - 1:
                    group_stocks = ranked[ranked >= (i + 1) * group_size].index
                else:
                    group_stocks = ranked[
                        (ranked >= i * group_size) & (ranked < (i + 1) * group_size)
                    ].index
                
                group_ret = return_vals[group_stocks].mean()
                if pd.notna(group_ret):
                    group_returns[f'group_{i+1}'].append(group_ret)
        
        avg_group_returns = {}
        for group, rets in group_returns.items():
            if rets:
                avg_group_returns[group] = np.mean(rets)
            else:
                avg_group_returns[group] = 0.0
        
        returns_values = list(avg_group_returns.values())
        if len(returns_values) >= 2:
            diffs = np.diff(returns_values)
            positive = np.sum(diffs > 0)
            negative = np.sum(diffs < 0)
            monotonicity = max(positive, negative) / len(diffs) if len(diffs) > 0 else 0
        else:
            monotonicity = 0.0
        
        long_short = avg_group_returns.get(f'group_{self.n_groups}', 0) - avg_group_returns.get('group_1', 0)
        
        return {
            'monotonicity': monotonicity,
            'long_short_return': long_short,
            'group_returns': avg_group_returns
        }
    
    def _evaluate_stability(
        self,
        factor_data: pd.DataFrame,
        return_data: pd.DataFrame,
        market_states: Optional[pd.Series] = None
    ) -> Dict[str, Any]:
        """评估稳定性"""
        ics = []
        dates = []
        
        for date in factor_data.index:
            if date not in return_data.index:
                continue
            
            factor_vals = factor_data.loc[date].dropna()
            return_vals = return_data.loc[date].dropna()
            
            common_stocks = factor_vals.index.intersection(return_vals.index)
            
            if len(common_stocks) < 10:
                continue
            
            ic = factor_vals[common_stocks].corr(return_vals[common_stocks], method='spearman')
            
            if pd.notna(ic):
                ics.append(ic)
                dates.append(date)
        
        if not ics:
            return {
                'monthly_stability': 0.0,
                'bull_ic': 0.0,
                'bear_ic': 0.0,
                'sideways_ic': 0.0
            }
        
        ic_series = pd.Series(ics, index=dates)
        
        if isinstance(ic_series.index[0], str):
            ic_series.index = pd.to_datetime(ic_series.index)
        
        monthly_ic = ic_series.resample('M').mean()
        monthly_stability = monthly_ic.std() / abs(monthly_ic.mean()) if monthly_ic.mean() != 0 else 0
        monthly_stability = 1 - min(monthly_stability, 1)
        
        bull_ic = 0.0
        bear_ic = 0.0
        sideways_ic = 0.0
        
        if market_states is not None:
            bull_ics = []
            bear_ics = []
            sideways_ics = []
            
            for date, ic in ic_series.items():
                if date in market_states.index:
                    state = market_states.loc[date]
                    if state == 'bull':
                        bull_ics.append(ic)
                    elif state == 'bear':
                        bear_ics.append(ic)
                    else:
                        sideways_ics.append(ic)
            
            bull_ic = np.mean(bull_ics) if bull_ics else 0.0
            bear_ic = np.mean(bear_ics) if bear_ics else 0.0
            sideways_ic = np.mean(sideways_ics) if sideways_ics else 0.0
        
        return {
            'monthly_stability': monthly_stability,
            'bull_ic': bull_ic,
            'bear_ic': bear_ic,
            'sideways_ic': sideways_ic
        }
    
    def _evaluate_correlation(
        self,
        factor_data: pd.DataFrame,
        other_factors: Dict[str, pd.DataFrame]
    ) -> Dict[str, Any]:
        """评估相关性"""
        correlations = []
        
        for other_name, other_data in other_factors.items():
            common_dates = factor_data.index.intersection(other_data.index)
            
            if len(common_dates) == 0:
                continue
            
            for date in common_dates:
                factor_vals = factor_data.loc[date].dropna()
                other_vals = other_data.loc[date].dropna()
                
                common_stocks = factor_vals.index.intersection(other_vals.index)
                
                if len(common_stocks) < 10:
                    continue
                
                corr = factor_vals[common_stocks].corr(other_vals[common_stocks])
                
                if pd.notna(corr):
                    correlations.append(abs(corr))
        
        avg_corr = np.mean(correlations) if correlations else 0.0
        
        if avg_corr > 0.7:
            redundancy = "high"
        elif avg_corr > 0.4:
            redundancy = "medium"
        else:
            redundancy = "low"
        
        return {
            'similar_correlation': avg_corr,
            'other_correlation': avg_corr,
            'redundancy': redundancy
        }
    
    def _evaluate_utility(self, factor_data: pd.DataFrame) -> Dict[str, Any]:
        """评估实用性"""
        total_cells = factor_data.size
        valid_cells = factor_data.notna().sum().sum()
        coverage = valid_cells / total_cells if total_cells > 0 else 0
        
        turnovers = []
        for i in range(1, len(factor_data)):
            prev_vals = factor_data.iloc[i-1].dropna()
            curr_vals = factor_data.iloc[i].dropna()
            
            common_stocks = prev_vals.index.intersection(curr_vals.index)
            
            if len(common_stocks) < 10:
                continue
            
            prev_ranks = prev_vals[common_stocks].rank()
            curr_ranks = curr_vals[common_stocks].rank()
            
            rank_changes = abs(curr_ranks - prev_ranks).mean()
            max_change = len(common_stocks)
            turnover = rank_changes / max_change if max_change > 0 else 0
            turnovers.append(turnover)
        
        avg_turnover = np.mean(turnovers) if turnovers else 0
        
        complexity = "low"
        
        return {
            'coverage': coverage,
            'turnover': avg_turnover,
            'complexity': complexity
        }
    
    def _calculate_scores(self, result: FactorEvaluationResult) -> Dict[str, int]:
        """计算评分"""
        prediction_score = 0
        if abs(result.ic_mean) >= self.IC_THRESHOLDS['excellent']:
            prediction_score = 90
        elif abs(result.ic_mean) >= self.IC_THRESHOLDS['good']:
            prediction_score = 75
        elif abs(result.ic_mean) >= self.IC_THRESHOLDS['fair']:
            prediction_score = 60
        else:
            prediction_score = 40
        
        if abs(result.ir) >= self.IR_THRESHOLDS['excellent']:
            prediction_score = min(100, prediction_score + 10)
        elif abs(result.ir) >= self.IR_THRESHOLDS['good']:
            prediction_score = min(100, prediction_score + 5)
        
        stability_score = int(result.monthly_ic_stability * 100)
        
        correlation_score = 100 - int(result.correlation_with_similar * 100)
        
        utility_score = int(result.coverage * 100)
        if result.turnover < 0.1:
            utility_score = min(100, utility_score + 10)
        
        total_score = int(
            prediction_score * 0.3 +
            stability_score * 0.25 +
            correlation_score * 0.2 +
            utility_score * 0.25
        )
        
        return {
            'prediction': prediction_score,
            'stability': stability_score,
            'correlation': correlation_score,
            'utility': utility_score,
            'total': total_score
        }
    
    def _generate_recommendations(self, result: FactorEvaluationResult) -> Dict[str, Any]:
        """生成建议"""
        warnings = []
        paired_factors = []
        
        if result.ic_mean < 0.01:
            warnings.append("IC较低，预测能力有限")
        
        if result.monthly_ic_stability < 0.5:
            warnings.append("稳定性较差，建议谨慎使用")
        
        if result.correlation_with_similar > 0.6:
            warnings.append("与同类因子相关性较高，可能存在冗余")
        
        if result.coverage < 0.8:
            warnings.append("覆盖率较低，可能影响选股范围")
        
        if result.ic_mean > 0.03 and result.monthly_ic_stability > 0.6:
            usage = "趋势行情"
            weight = "较高（10-15%）"
        elif result.ic_mean > 0.01:
            usage = "综合行情"
            weight = "中等（5-10%）"
        else:
            usage = "辅助参考"
            weight = "较低（<5%）"
        
        if result.correlation_with_similar < 0.3:
            paired_factors = ["价值类因子", "质量类因子"]
        
        return {
            'usage': usage,
            'weight': weight,
            'warnings': warnings,
            'paired_factors': paired_factors
        }
    
    def evaluate_multiple(
        self,
        factors_data: Dict[str, pd.DataFrame],
        return_data: pd.DataFrame,
        market_states: Optional[pd.Series] = None
    ) -> Dict[str, FactorEvaluationResult]:
        """
        评估多个因子
        
        Args:
            factors_data: 因子数据字典 {因子名: 因子数据}
            return_data: 收益数据
            market_states: 市场状态
            
        Returns:
            Dict[str, FactorEvaluationResult]: 评估结果字典
        """
        results = {}
        
        for factor_name, factor_data in factors_data.items():
            other_factors = {k: v for k, v in factors_data.items() if k != factor_name}
            
            result = self.evaluate(
                factor_data=factor_data,
                return_data=return_data,
                factor_id=factor_name,
                factor_name=factor_name,
                market_states=market_states,
                other_factors=other_factors
            )
            results[factor_name] = result
        
        sorted_results = sorted(
            results.items(),
            key=lambda x: x[1].total_score,
            reverse=True
        )
        
        for rank, (name, result) in enumerate(sorted_results, 1):
            result.rank = rank
            result.total_factors = len(sorted_results)
        
        return results
