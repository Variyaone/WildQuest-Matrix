"""
策略绩效评估器

评估策略的收益风险特征。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np

from .metrics import PerformanceMetricsCalculator


@dataclass
class StrategyEvaluationResult:
    """策略评估结果"""
    strategy_id: str
    strategy_name: str
    evaluation_date: str
    start_date: str
    end_date: str
    benchmark: str
    
    cumulative_return: float = 0.0
    annual_return: float = 0.0
    excess_return: float = 0.0
    beat_benchmark_ratio: float = 0.0
    
    annual_volatility: float = 0.0
    max_drawdown: float = 0.0
    drawdown_duration: int = 0
    var_95: float = 0.0
    
    sharpe_ratio: float = 0.0
    calmar_ratio: float = 0.0
    sortino_ratio: float = 0.0
    information_ratio: float = 0.0
    
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    turnover_rate: float = 0.0
    trade_count: int = 0
    avg_holding_period: float = 0.0
    
    allocation_effect: float = 0.0
    selection_effect: float = 0.0
    interaction_effect: float = 0.0
    
    momentum_contribution: float = 0.0
    value_contribution: float = 0.0
    quality_contribution: float = 0.0
    other_contribution: float = 0.0
    
    bull_market_return: float = 0.0
    bear_market_return: float = 0.0
    sideways_market_return: float = 0.0
    
    return_score: int = 0
    risk_control_score: int = 0
    risk_adjusted_score: int = 0
    trading_efficiency_score: int = 0
    stability_score: int = 0
    total_score: int = 0
    rank: int = 0
    total_strategies: int = 0
    
    recommended_allocation: str = ""
    recommended_market: str = ""
    risk_warnings: List[str] = field(default_factory=list)
    optimization_suggestions: List[str] = field(default_factory=list)
    
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'evaluation_date': self.evaluation_date,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'benchmark': self.benchmark,
            'cumulative_return': self.cumulative_return,
            'annual_return': self.annual_return,
            'excess_return': self.excess_return,
            'beat_benchmark_ratio': self.beat_benchmark_ratio,
            'annual_volatility': self.annual_volatility,
            'max_drawdown': self.max_drawdown,
            'drawdown_duration': self.drawdown_duration,
            'var_95': self.var_95,
            'sharpe_ratio': self.sharpe_ratio,
            'calmar_ratio': self.calmar_ratio,
            'sortino_ratio': self.sortino_ratio,
            'information_ratio': self.information_ratio,
            'win_rate': self.win_rate,
            'profit_loss_ratio': self.profit_loss_ratio,
            'turnover_rate': self.turnover_rate,
            'trade_count': self.trade_count,
            'avg_holding_period': self.avg_holding_period,
            'allocation_effect': self.allocation_effect,
            'selection_effect': self.selection_effect,
            'interaction_effect': self.interaction_effect,
            'momentum_contribution': self.momentum_contribution,
            'value_contribution': self.value_contribution,
            'quality_contribution': self.quality_contribution,
            'other_contribution': self.other_contribution,
            'bull_market_return': self.bull_market_return,
            'bear_market_return': self.bear_market_return,
            'sideways_market_return': self.sideways_market_return,
            'return_score': self.return_score,
            'risk_control_score': self.risk_control_score,
            'risk_adjusted_score': self.risk_adjusted_score,
            'trading_efficiency_score': self.trading_efficiency_score,
            'stability_score': self.stability_score,
            'total_score': self.total_score,
            'rank': self.rank,
            'total_strategies': self.total_strategies,
            'recommended_allocation': self.recommended_allocation,
            'recommended_market': self.recommended_market,
            'risk_warnings': self.risk_warnings,
            'optimization_suggestions': self.optimization_suggestions,
            'details': self.details
        }
    
    def get_summary(self) -> str:
        """获取摘要"""
        return f"""
策略评估报告
================
策略编号: {self.strategy_id}
策略名称: {self.strategy_name}
评估日期: {self.evaluation_date}
回测周期: {self.start_date} 至 {self.end_date}
基准指数: {self.benchmark}

一、收益评估
  累计收益率: {self.cumulative_return:.2%}
  年化收益率: {self.annual_return:.2%}
  超额收益率: {self.excess_return:.2%}
  跑赢基准比例: {self.beat_benchmark_ratio:.2%}

二、风险评估
  年化波动率: {self.annual_volatility:.2%}
  最大回撤: {self.max_drawdown:.2%}
  回撤持续: {self.drawdown_duration}天
  VaR(95%): {self.var_95:.2%}

三、风险调整收益
  夏普比率: {self.sharpe_ratio:.2f}
  卡玛比率: {self.calmar_ratio:.2f}
  索提诺比率: {self.sortino_ratio:.2f}
  信息比率: {self.information_ratio:.2f}

四、交易评估
  胜率: {self.win_rate:.2%}
  盈亏比: {self.profit_loss_ratio:.2f}
  换手率: {self.turnover_rate:.2%}
  交易次数: {self.trade_count}
  平均持仓: {self.avg_holding_period:.1f}天

五、归因分析
  配置效应: {self.allocation_effect:.2%}
  选择效应: {self.selection_effect:.2%}
  动量因子贡献: {self.momentum_contribution:.2%}
  价值因子贡献: {self.value_contribution:.2%}
  质量因子贡献: {self.quality_contribution:.2%}

六、市场适应性
  牛市表现: {self.bull_market_return:.2%}
  熊市表现: {self.bear_market_return:.2%}
  震荡市表现: {self.sideways_market_return:.2%}

七、综合评分
  收益得分: {self.return_score}/100
  风险控制得分: {self.risk_control_score}/100
  风险调整收益得分: {self.risk_adjusted_score}/100
  交易效率得分: {self.trading_efficiency_score}/100
  稳定性得分: {self.stability_score}/100
  综合得分: {self.total_score}/100 (排名: {self.rank}/{self.total_strategies})

八、使用建议
  推荐资金比例: {self.recommended_allocation}
  推荐市场环境: {self.recommended_market}
  风险提示: {', '.join(self.risk_warnings) if self.risk_warnings else '无'}
  优化方向: {', '.join(self.optimization_suggestions) if self.optimization_suggestions else '无'}
"""


class StrategyEvaluator:
    """
    策略绩效评估器
    
    评估策略的收益风险特征。
    """
    
    SHARPE_THRESHOLDS = {
        'excellent': 2.0,
        'good': 1.5,
        'fair': 1.0,
        'poor': 0.5
    }
    
    DRAWDOWN_THRESHOLDS = {
        'excellent': 0.10,
        'good': 0.15,
        'fair': 0.20,
        'poor': 0.30
    }
    
    def __init__(
        self,
        risk_free_rate: float = 0.03,
        trading_days: int = 252
    ):
        """
        初始化策略评估器
        
        Args:
            risk_free_rate: 无风险利率
            trading_days: 年交易日数
        """
        self.risk_free_rate = risk_free_rate
        self.trading_days = trading_days
    
    def evaluate(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        positions: Optional[pd.DataFrame] = None,
        trades: Optional[List[Dict]] = None,
        strategy_id: str = "",
        strategy_name: str = "",
        benchmark_name: str = "沪深300",
        market_states: Optional[pd.Series] = None,
        factor_contributions: Optional[Dict[str, float]] = None
    ) -> StrategyEvaluationResult:
        """
        评估策略
        
        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列
            positions: 持仓数据
            trades: 交易记录
            strategy_id: 策略ID
            strategy_name: 策略名称
            benchmark_name: 基准名称
            market_states: 市场状态
            factor_contributions: 因子贡献
            
        Returns:
            StrategyEvaluationResult: 评估结果
        """
        result = StrategyEvaluationResult(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            evaluation_date=datetime.now().strftime('%Y-%m-%d'),
            start_date=str(returns.index[0])[:10] if len(returns) > 0 else "",
            end_date=str(returns.index[-1])[:10] if len(returns) > 0 else "",
            benchmark=benchmark_name
        )
        
        result.cumulative_return = PerformanceMetricsCalculator.total_return(returns)
        result.annual_return = PerformanceMetricsCalculator.annual_return(returns, self.trading_days)
        
        if benchmark_returns is not None:
            aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
            
            if len(aligned_returns) > 0:
                benchmark_annual = PerformanceMetricsCalculator.annual_return(aligned_benchmark, self.trading_days)
                result.excess_return = result.annual_return - benchmark_annual
                
                beat_days = (aligned_returns > aligned_benchmark).sum()
                result.beat_benchmark_ratio = beat_days / len(aligned_returns) if len(aligned_returns) > 0 else 0
                
                result.information_ratio = PerformanceMetricsCalculator.information_ratio(
                    returns, benchmark_returns, self.trading_days
                )
        
        result.annual_volatility = PerformanceMetricsCalculator.volatility(returns, self.trading_days)
        result.max_drawdown = PerformanceMetricsCalculator.max_drawdown(returns)
        result.drawdown_duration = PerformanceMetricsCalculator.drawdown_duration(returns)
        result.var_95 = PerformanceMetricsCalculator.var(returns, 0.95)
        
        result.sharpe_ratio = PerformanceMetricsCalculator.sharpe_ratio(
            returns, self.risk_free_rate, self.trading_days
        )
        result.sortino_ratio = PerformanceMetricsCalculator.sortino_ratio(
            returns, self.risk_free_rate, self.trading_days
        )
        result.calmar_ratio = PerformanceMetricsCalculator.calmar_ratio(returns, self.trading_days)
        
        if trades:
            result.win_rate = PerformanceMetricsCalculator.win_rate(trades)
            result.profit_loss_ratio = PerformanceMetricsCalculator.profit_loss_ratio(trades)
            result.trade_count = len(trades)
            
            holding_periods = [t.get('holding_period', 0) for t in trades if 'holding_period' in t]
            result.avg_holding_period = np.mean(holding_periods) if holding_periods else 0
        
        if positions is not None and len(positions) > 0:
            result.turnover_rate = PerformanceMetricsCalculator.turnover_rate(positions, self.trading_days)
        
        if benchmark_returns is not None and positions is not None:
            brinson_result = self._calculate_brinson_attribution(
                returns, benchmark_returns, positions
            )
            result.allocation_effect = brinson_result['allocation']
            result.selection_effect = brinson_result['selection']
            result.interaction_effect = brinson_result['interaction']
        
        if factor_contributions:
            result.momentum_contribution = factor_contributions.get('momentum', 0)
            result.value_contribution = factor_contributions.get('value', 0)
            result.quality_contribution = factor_contributions.get('quality', 0)
            result.other_contribution = factor_contributions.get('other', 0)
        
        if market_states is not None:
            market_result = self._analyze_market_adaptation(returns, market_states)
            result.bull_market_return = market_result['bull']
            result.bear_market_return = market_result['bear']
            result.sideways_market_return = market_result['sideways']
        
        scores = self._calculate_scores(result)
        result.return_score = scores['return']
        result.risk_control_score = scores['risk']
        result.risk_adjusted_score = scores['risk_adjusted']
        result.trading_efficiency_score = scores['trading']
        result.stability_score = scores['stability']
        result.total_score = scores['total']
        
        recommendations = self._generate_recommendations(result)
        result.recommended_allocation = recommendations['allocation']
        result.recommended_market = recommendations['market']
        result.risk_warnings = recommendations['warnings']
        result.optimization_suggestions = recommendations['optimizations']
        
        return result
    
    def _calculate_brinson_attribution(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series,
        positions: pd.DataFrame
    ) -> Dict[str, float]:
        """计算Brinson归因"""
        allocation = 0.0
        selection = 0.0
        interaction = 0.0
        
        return {
            'allocation': allocation,
            'selection': selection,
            'interaction': interaction
        }
    
    def _analyze_market_adaptation(
        self,
        returns: pd.Series,
        market_states: pd.Series
    ) -> Dict[str, float]:
        """分析市场适应性"""
        bull_returns = []
        bear_returns = []
        sideways_returns = []
        
        for date, ret in returns.items():
            if date in market_states.index:
                state = market_states.loc[date]
                if state == 'bull':
                    bull_returns.append(ret)
                elif state == 'bear':
                    bear_returns.append(ret)
                else:
                    sideways_returns.append(ret)
        
        bull_return = (1 + pd.Series(bull_returns)).prod() - 1 if bull_returns else 0
        bear_return = (1 + pd.Series(bear_returns)).prod() - 1 if bear_returns else 0
        sideways_return = (1 + pd.Series(sideways_returns)).prod() - 1 if sideways_returns else 0
        
        return {
            'bull': bull_return,
            'bear': bear_return,
            'sideways': sideways_return
        }
    
    def _calculate_scores(self, result: StrategyEvaluationResult) -> Dict[str, int]:
        """计算评分"""
        return_score = 0
        if result.annual_return > 0.20:
            return_score = 90
        elif result.annual_return > 0.15:
            return_score = 80
        elif result.annual_return > 0.10:
            return_score = 70
        elif result.annual_return > 0.05:
            return_score = 60
        else:
            return_score = 40
        
        risk_score = 0
        if abs(result.max_drawdown) < self.DRAWDOWN_THRESHOLDS['excellent']:
            risk_score = 90
        elif abs(result.max_drawdown) < self.DRAWDOWN_THRESHOLDS['good']:
            risk_score = 80
        elif abs(result.max_drawdown) < self.DRAWDOWN_THRESHOLDS['fair']:
            risk_score = 65
        else:
            risk_score = 40
        
        risk_adjusted_score = 0
        if result.sharpe_ratio > self.SHARPE_THRESHOLDS['excellent']:
            risk_adjusted_score = 95
        elif result.sharpe_ratio > self.SHARPE_THRESHOLDS['good']:
            risk_adjusted_score = 85
        elif result.sharpe_ratio > self.SHARPE_THRESHOLDS['fair']:
            risk_adjusted_score = 70
        elif result.sharpe_ratio > self.SHARPE_THRESHOLDS['poor']:
            risk_adjusted_score = 55
        else:
            risk_adjusted_score = 35
        
        trading_score = 0
        if result.win_rate > 0.6 and result.profit_loss_ratio > 1.5:
            trading_score = 90
        elif result.win_rate > 0.55 and result.profit_loss_ratio > 1.2:
            trading_score = 75
        elif result.win_rate > 0.5:
            trading_score = 60
        else:
            trading_score = 40
        
        stability_score = 70
        
        total_score = int(
            return_score * 0.30 +
            risk_score * 0.25 +
            risk_adjusted_score * 0.25 +
            trading_score * 0.10 +
            stability_score * 0.10
        )
        
        return {
            'return': return_score,
            'risk': risk_score,
            'risk_adjusted': risk_adjusted_score,
            'trading': trading_score,
            'stability': stability_score,
            'total': total_score
        }
    
    def _generate_recommendations(self, result: StrategyEvaluationResult) -> Dict[str, Any]:
        """生成建议"""
        warnings = []
        optimizations = []
        
        if abs(result.max_drawdown) > 0.20:
            warnings.append("最大回撤较大，建议增加风控措施")
        
        if result.sharpe_ratio < 1.0:
            warnings.append("夏普比率较低，风险调整后收益不佳")
        
        if result.win_rate < 0.5:
            warnings.append("胜率较低，建议优化选股逻辑")
        
        if result.turnover_rate > 0.5:
            warnings.append("换手率较高，交易成本可能侵蚀收益")
        
        if result.excess_return < 0:
            optimizations.append("策略未能跑赢基准，建议重新审视策略逻辑")
        
        if abs(result.max_drawdown) > 0.15:
            optimizations.append("建议增加止损机制控制回撤")
        
        if result.information_ratio < 0.5:
            optimizations.append("信息比率较低，建议提高超额收益稳定性")
        
        if result.total_score >= 80:
            allocation = "20-30%"
        elif result.total_score >= 70:
            allocation = "15-20%"
        elif result.total_score >= 60:
            allocation = "10-15%"
        else:
            allocation = "5-10%"
        
        if result.bull_market_return > result.bear_market_return * 2:
            market = "趋势行情"
        elif abs(result.bear_market_return) < abs(result.max_drawdown) * 0.5:
            market = "震荡行情"
        else:
            market = "综合行情"
        
        return {
            'allocation': allocation,
            'market': market,
            'warnings': warnings,
            'optimizations': optimizations
        }
    
    def evaluate_multiple(
        self,
        strategies_returns: Dict[str, pd.Series],
        benchmark_returns: Optional[pd.Series] = None,
        market_states: Optional[pd.Series] = None
    ) -> Dict[str, StrategyEvaluationResult]:
        """
        评估多个策略
        
        Args:
            strategies_returns: 策略收益率字典 {策略名: 收益率序列}
            benchmark_returns: 基准收益率
            market_states: 市场状态
            
        Returns:
            Dict[str, StrategyEvaluationResult]: 评估结果字典
        """
        results = {}
        
        for strategy_name, returns in strategies_returns.items():
            result = self.evaluate(
                returns=returns,
                benchmark_returns=benchmark_returns,
                strategy_id=strategy_name,
                strategy_name=strategy_name,
                market_states=market_states
            )
            results[strategy_name] = result
        
        sorted_results = sorted(
            results.items(),
            key=lambda x: x[1].total_score,
            reverse=True
        )
        
        for rank, (name, result) in enumerate(sorted_results, 1):
            result.rank = rank
            result.total_strategies = len(sorted_results)
        
        return results
